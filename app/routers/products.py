import uuid
import json
import logging
from fastapi import APIRouter, HTTPException
from ..models import BrandProductSubmission
from ..services.supabase import db
from ..services.scoring import calculate_ai_readiness, calculate_rack_readiness, missing_items_ai, missing_items_rack

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/products", tags=["products"])


@router.post("")
async def create_product(payload: BrandProductSubmission):
    try:
        data = payload.dict(exclude={"variants", "images", "measurements"}, exclude_none=True)
        data["id"] = str(uuid.uuid4())
        data["ai_readiness_score"] = calculate_ai_readiness(data)
        data["rack_readiness_score"] = calculate_rack_readiness(data)
        result = db.insert("brand_product_submissions", data)
        row = result.data[0] if result.data else data
        submission_id = row["id"]

        if payload.variants:
            for v in payload.variants:
                v["id"] = str(uuid.uuid4())
                v["product_submission_id"] = submission_id
                db.insert("product_variants", v)
        if payload.images:
            for i, img in enumerate(payload.images):
                img["id"] = str(uuid.uuid4())
                img["product_submission_id"] = submission_id
                img["sort_order"] = i
                db.insert("product_images", img)
        if payload.measurements:
            for m in payload.measurements:
                m["id"] = str(uuid.uuid4())
                m["product_submission_id"] = submission_id
                db.insert("garment_measurements", m)

        db.insert("brand_activity_logs", {
            "id": str(uuid.uuid4()),
            "brand_id": payload.brand_id,
            "action": "product_created",
            "metadata": {"product_title": payload.title, "status": "draft"},
        })
        return {"id": submission_id, "status": "draft", "ai_readiness_score": data["ai_readiness_score"], "rack_readiness_score": data["rack_readiness_score"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{submission_id}")
async def get_product(submission_id: str):
    try:
        result = db.select_by_id("brand_product_submissions", submission_id)
        if not result.data:
            raise HTTPException(status_code=404, detail="Product not found")
        row = result.data[0]
        extras = _get_product_extras(submission_id)
        row.update(extras)
        row["missing_ai_items"] = missing_items_ai(row)
        row["missing_rack_items"] = missing_items_rack(row)
        return row
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{submission_id}")
async def update_product(submission_id: str, payload: BrandProductSubmission):
    try:
        existing = db.select_by_id("brand_product_submissions", submission_id)
        if not existing.data:
            raise HTTPException(status_code=404, detail="Product not found")
        data = payload.dict(exclude={"variants", "images", "measurements", "id"}, exclude_none=True)
        data["ai_readiness_score"] = calculate_ai_readiness(data)
        data["rack_readiness_score"] = calculate_rack_readiness(data)
        data["updated_at"] = "now()"
        db.update("brand_product_submissions", data, "id", submission_id)

        if payload.variants is not None:
            existing_variants = db.select("product_variants", "product_submission_id", submission_id)
            if existing_variants.data:
                for v in existing_variants.data:
                    db.delete("product_variants", "id", v["id"])
            for v in payload.variants:
                v["id"] = str(uuid.uuid4())
                v["product_submission_id"] = submission_id
                db.insert("product_variants", v)
        if payload.images is not None:
            existing_images = db.select("product_images", "product_submission_id", submission_id)
            if existing_images.data:
                for img in existing_images.data:
                    db.delete("product_images", "id", img["id"])
            for i, img in enumerate(payload.images):
                img["id"] = str(uuid.uuid4())
                img["product_submission_id"] = submission_id
                img["sort_order"] = i
                db.insert("product_images", img)
        if payload.measurements is not None:
            existing_meas = db.select("garment_measurements", "product_submission_id", submission_id)
            if existing_meas.data:
                for m in existing_meas.data:
                    db.delete("garment_measurements", "id", m["id"])
            for m in payload.measurements:
                m["id"] = str(uuid.uuid4())
                m["product_submission_id"] = submission_id
                db.insert("garment_measurements", m)

        return {"message": "Product updated", "ai_readiness_score": data["ai_readiness_score"], "rack_readiness_score": data["rack_readiness_score"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/brand/{brand_id}")
async def list_brand_products(brand_id: str, status: str = None):
    try:
        result = db.select("brand_product_submissions", "brand_id", brand_id)
        rows = result.data or []
        if status:
            rows = [r for r in rows if r.get("status") == status]
        for row in rows:
            extras = _get_product_extras(row["id"])
            row.update(extras)
            row["missing_ai_items"] = missing_items_ai(row)
            row["missing_rack_items"] = missing_items_rack(row)
        return {"products": rows}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{submission_id}/submit")
async def submit_product_for_review(submission_id: str):
    try:
        existing = db.select_by_id("brand_product_submissions", submission_id)
        if not existing.data:
            raise HTTPException(status_code=404, detail="Product not found")
        row = existing.data[0]
        missing = missing_items_ai(row)
        if missing:
            raise HTTPException(status_code=400, detail=f"Product is incomplete. Missing: {'; '.join(missing)}")
        db.update("brand_product_submissions", {"status": "submitted", "updated_at": "now()"}, "id", submission_id)
        db.insert("brand_activity_logs", {
            "id": str(uuid.uuid4()),
            "brand_id": row["brand_id"],
            "action": "product_submitted_for_review",
            "metadata": {"product_title": row.get("title"), "submission_id": submission_id},
        })
        return {"message": "Product submitted for review", "status": "submitted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{submission_id}")
async def delete_product(submission_id: str):
    try:
        db.delete("brand_product_submissions", "id", submission_id)
        return {"message": "Product deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _get_product_extras(submission_id: str) -> dict:
    extras = {}
    variants = db.select("product_variants", "product_submission_id", submission_id)
    extras["variants"] = variants.data or []
    images = db.select("product_images", "product_submission_id", submission_id)
    extras["images"] = images.data or []
    measurements = db.select("garment_measurements", "product_submission_id", submission_id)
    extras["measurements"] = measurements.data or []
    return extras
