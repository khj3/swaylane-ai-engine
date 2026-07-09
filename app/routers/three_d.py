import uuid
import json
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from ..services.supabase import db
from ..services.three_d import three_d_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/3d", tags=["3d"])


@router.get("/assets/{submission_id}")
async def list_product_3d_assets(submission_id: str):
    """List all 3D assets generated for a product submission."""
    try:
        result = db.select("product_3d_assets", "product_submission_id", submission_id)
        rows = result.data or []
        rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return {"assets": rows}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/generate")
async def generate_3d_asset(
    product_submission_id: str,
    tool: str = "hunyuan",
    asset_type: str = "model",
    input_image_url: str = None,
    input_prompt: str = None,
):
    """Trigger 3D asset generation for a product using specified tool."""
    try:
        existing = db.select_by_id("brand_product_submissions", product_submission_id)
        if not existing.data:
            raise HTTPException(status_code=404, detail="Product not found")

        asset_id = str(uuid.uuid4())
        asset_record = {
            "id": asset_id,
            "product_submission_id": product_submission_id,
            "tool_name": tool,
            "asset_type": asset_type,
            "input_image_url": input_image_url or "",
            "input_prompt": input_prompt or existing.data[0].get("title", ""),
            "status": "queued",
            "metadata": json.dumps({"source": "brand_portal"}),
        }

        task_id = None
        status = "queued"
        result_data = {}

        if tool == "hunyuan":
            task_id, status, result_data = await three_d_service.generate_hunyuan_3d(
                image_url=input_image_url,
                prompt=input_prompt or existing.data[0].get("title", ""),
                asset_type=asset_type,
            )
        elif tool == "modddif":
            if not input_image_url:
                images = db.select("product_images", "product_submission_id", product_submission_id)
                if images.data and len(images.data) > 0:
                    input_image_url = images.data[0].get("image_url", "")
            if input_image_url:
                task_id, status, result_data = await three_d_service.enhance_texture_modddif(
                    image_url=input_image_url,
                    enhancement_type=asset_type if asset_type != "model" else "texture",
                )
            else:
                return {"error": "No image available for Modddif enhancement. Provide input_image_url."}
        elif tool == "top3d":
            return {
                "message": "Top3D AI Arena is a comparison/benchmark tool. Use it manually at:",
                "url": three_d_service.top3d_benchmark_url(),
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool}")

        if status == "not_configured":
            asset_record["status"] = "pending"
            asset_record["error_message"] = f"{tool} API key not configured. Set it and regenerate."
        elif status == "failed":
            err_msg = result_data.get("error", "Generation failed")
            asset_record["status"] = "failed"
            asset_record["error_message"] = err_msg
        else:
            asset_record["status"] = status
            if task_id:
                asset_record["metadata"] = json.dumps({"task_id": task_id, **result_data})

        db.insert("product_3d_assets", asset_record)
        return {
            "asset_id": asset_id,
            "tool": tool,
            "status": asset_record["status"],
            "task_id": task_id,
            "message": "3D generation queued" if status == "processing" else asset_record.get("error_message", ""),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status/{asset_id}")
async def check_asset_status(asset_id: str):
    """Check the status of a 3D asset generation task."""
    try:
        result = db.select_by_id("product_3d_assets", asset_id)
        if not result.data:
            raise HTTPException(status_code=404, detail="Asset not found")
        asset = result.data[0]
        meta = {}
        try:
            meta = json.loads(asset.get("metadata", "{}"))
        except (json.JSONDecodeError, TypeError):
            pass

        task_id = meta.get("task_id")
        tool = asset.get("tool_name", "")
        remote_status = None

        if task_id and tool == "hunyuan":
            remote_data = await three_d_service.check_hunyuan_status(task_id)
            if remote_data:
                remote_status = remote_data.get("status")
                if remote_status == "completed":
                    output_url = remote_data.get("output_url") or remote_data.get("result_url", "")
                    if output_url:
                        db.update("product_3d_assets", {
                            "status": "completed",
                            "output_url": output_url,
                            "updated_at": "now()",
                        }, "id", asset_id)
                        return {"asset": asset, "status": "completed", "output_url": output_url}
                elif remote_status == "failed":
                    db.update("product_3d_assets", {
                        "status": "failed",
                        "error_message": remote_data.get("error", "Remote generation failed"),
                        "updated_at": "now()",
                    }, "id", asset_id)

        if tool == "modddif" and task_id:
            remote_data = await three_d_service.check_modddif_status(task_id)
            if remote_data:
                remote_status = remote_data.get("status")
                if remote_status == "completed":
                    output_url = remote_data.get("output_url") or remote_data.get("result_url", "")
                    if output_url:
                        db.update("product_3d_assets", {
                            "status": "completed",
                            "output_url": output_url,
                            "updated_at": "now()",
                        }, "id", asset_id)

        # Refresh from DB
        updated = db.select_by_id("product_3d_assets", asset_id)
        return {"asset": updated.data[0] if updated.data else asset}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/set-best")
async def set_best_3d_asset(product_submission_id: str, asset_id: str):
    """Mark a 3D asset as the best/primary for a product."""
    try:
        asset = db.select_by_id("product_3d_assets", asset_id)
        if not asset.data:
            raise HTTPException(status_code=404, detail="Asset not found")
        a = asset.data[0]
        if a.get("product_submission_id") != product_submission_id:
            raise HTTPException(status_code=400, detail="Asset does not belong to this product")
        thumbnail = a.get("thumbnail_url") or a.get("output_url", "")
        db.update("brand_product_submissions", {
            "has_3d_asset": True,
            "best_3d_thumbnail": thumbnail,
            "updated_at": "now()",
        }, "id", product_submission_id)
        return {"message": "Best 3D asset set", "thumbnail": thumbnail}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Admin endpoints ──────────────────────────────

@router.get("/admin/assets")
async def admin_list_3d_assets(status: str = None, limit: int = 50, offset: int = 0):
    try:
        result = db.select("product_3d_assets")
        rows = result.data or []
        if status:
            rows = [r for r in rows if r.get("status") == status]
        rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        total = len(rows)
        page = rows[offset:offset + limit]
        return {"assets": page, "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
