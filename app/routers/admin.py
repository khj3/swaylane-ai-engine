import uuid
import logging
from fastapi import APIRouter, HTTPException
from ..services.supabase import db
from ..services.shopify_admin import create_product, publish_product
from ..services.scoring import calculate_ai_readiness, calculate_rack_readiness

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/brands")
async def list_brands(status: str = None):
    try:
        result = db.select("brands")
        rows = result.data or []
        if status:
            rows = [r for r in rows if r.get("status") == status]
        return {"brands": rows}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/brands/{brand_id}/approve")
async def approve_brand(brand_id: str):
    try:
        existing = db.select_by_id("brands", brand_id)
        if not existing.data:
            raise HTTPException(status_code=404, detail="Brand not found")
        db.update("brands", {"status": "approved", "updated_at": "now()"}, "id", brand_id)
        db.insert("brand_activity_logs", {
            "id": str(uuid.uuid4()),
            "brand_id": brand_id,
            "action": "brand_approved_by_admin",
            "metadata": {},
        })
        return {"message": "Brand approved", "status": "approved"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/brands/{brand_id}/reject")
async def reject_brand(brand_id: str, notes: str = ""):
    try:
        existing = db.select_by_id("brands", brand_id)
        if not existing.data:
            raise HTTPException(status_code=404, detail="Brand not found")
        db.update("brands", {"status": "rejected", "admin_notes": notes, "updated_at": "now()"}, "id", brand_id)
        db.insert("brand_activity_logs", {
            "id": str(uuid.uuid4()),
            "brand_id": brand_id,
            "action": "brand_rejected_by_admin",
            "metadata": {"notes": notes},
        })
        return {"message": "Brand rejected", "status": "rejected"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/brands/{brand_id}/suspend")
async def suspend_brand(brand_id: str, reason: str = ""):
    try:
        db.update("brands", {"status": "suspended", "admin_notes": reason, "updated_at": "now()"}, "id", brand_id)
        return {"message": "Brand suspended", "status": "suspended"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/products")
async def list_submissions(status: str = None):
    try:
        result = db.select("brand_product_submissions")
        rows = result.data or []
        if status:
            rows = [r for r in rows if r.get("status") == status]
        brand_cache = {}
        for row in rows:
            row["ai_readiness_score"] = calculate_ai_readiness(row)
            row["rack_readiness_score"] = calculate_rack_readiness(row)
            bid = row.get("brand_id", "")
            if bid and bid not in brand_cache:
                b = db.select_by_id("brands", bid)
                brand_cache[bid] = b.data[0].get("brand_name", "") if b.data else ""
            row["brand_name"] = brand_cache.get(bid, "")
        return {"products": rows}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/products/{submission_id}/approve")
async def approve_product(submission_id: str, publish_to_shopify: bool = True):
    try:
        existing = db.select_by_id("brand_product_submissions", submission_id)
        if not existing.data:
            raise HTTPException(status_code=404, detail="Product not found")
        row = existing.data[0]

        brand = db.select_by_id("brands", row["brand_id"])
        brand_name = brand.data[0].get("brand_name", "Unknown Brand") if brand.data else "Unknown Brand"

        shopify_id = row.get("shopify_product_id")
        if not shopify_id:
            variants = db.select("product_variants", "product_submission_id", submission_id)
            images = db.select("product_images", "product_submission_id", submission_id)
            row["variants"] = [v.data for v in variants.data] if variants.data else []
            row["images"] = [i.data for i in images.data] if images.data else []
            result = await create_product(row, brand_name)
            if result:
                shopify_id = result

        if publish_to_shopify and shopify_id:
            await publish_product(shopify_id)

        updates = {
            "status": "approved" if not publish_to_shopify else "published",
            "shopify_product_id": shopify_id,
            "admin_notes": "",
            "updated_at": "now()",
        }
        db.update("brand_product_submissions", updates, "id", submission_id)
        db.insert("brand_activity_logs", {
            "id": str(uuid.uuid4()),
            "brand_id": row["brand_id"],
            "action": "product_approved_by_admin",
            "metadata": {"product_title": row.get("title"), "shopify_product_id": shopify_id},
        })
        return {"message": "Product approved", "shopify_product_id": shopify_id, "status": updates["status"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/products/{submission_id}/reject")
async def reject_product(submission_id: str, notes: str = ""):
    try:
        existing = db.select_by_id("brand_product_submissions", submission_id)
        if not existing.data:
            raise HTTPException(status_code=404, detail="Product not found")
        db.update("brand_product_submissions", {
            "status": "rejected", "admin_notes": notes, "updated_at": "now()"
        }, "id", submission_id)
        row = existing.data[0]
        db.insert("brand_activity_logs", {
            "id": str(uuid.uuid4()),
            "brand_id": row["brand_id"],
            "action": "product_rejected_by_admin",
            "metadata": {"product_title": row.get("title"), "notes": notes},
        })
        return {"message": "Product rejected", "status": "rejected"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
