import uuid
import logging
from fastapi import APIRouter, HTTPException
from ..models import BrandCreate, BrandResponse, BrandProfile, BrandDashboardMetrics, BrandProductSubmission
from ..services.supabase import db
from ..services.scoring import calculate_ai_readiness, calculate_rack_readiness

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/brands", tags=["brands"])


@router.post("", response_model=BrandResponse)
async def create_brand(payload: BrandCreate):
    try:
        data = payload.dict()
        data["id"] = str(uuid.uuid4())
        data["status"] = "pending"
        data["brand_slug"] = data["name"].lower().replace(" ", "-").replace("/", "-")
        result = db.insert("brands", data)
        row = result.data[0] if result.data else data
        return BrandResponse(id=row.get("id"), name=row.get("brand_name", data["name"]), status=row.get("status"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{brand_id}", response_model=BrandProfile)
async def get_brand(brand_id: str):
    try:
        result = db.select_by_id("brands", brand_id)
        if not result.data:
            raise HTTPException(status_code=404, detail="Brand not found")
        return BrandProfile(**result.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{brand_id}")
async def update_brand(brand_id: str, payload: BrandProfile):
    try:
        existing = db.select_by_id("brands", brand_id)
        if not existing.data:
            raise HTTPException(status_code=404, detail="Brand not found")
        data = payload.dict(exclude_unset=True)
        data["updated_at"] = "now()"
        db.update("brands", data, "id", brand_id)
        return {"message": "Brand updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/user/{user_id}")
async def get_brands_by_user(user_id: str):
    try:
        result = db.select("brand_users", "user_id", user_id)
        if not result.data:
            return {"brands": []}
        brand_ids = [row["brand_id"] for row in result.data]
        brands = []
        for bid in brand_ids:
            b = db.select_by_id("brands", bid)
            if b.data:
                brands.append(b.data[0])
        return {"brands": brands}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{brand_id}/dashboard", response_model=BrandDashboardMetrics)
async def brand_dashboard(brand_id: str):
    try:
        products = db.select("brand_product_submissions", "brand_id", brand_id)
        rows = products.data or []
        metrics = BrandDashboardMetrics(
            total_products=len(rows),
            draft_products=sum(1 for r in rows if r.get("status") == "draft"),
            submitted_products=sum(1 for r in rows if r.get("status") == "submitted"),
            approved_products=sum(1 for r in rows if r.get("status") == "approved"),
            rejected_products=sum(1 for r in rows if r.get("status") == "rejected"),
            ai_ready_count=sum(1 for r in rows if r.get("ai_readiness_score", 0) >= 70),
            rack_ready_count=sum(1 for r in rows if r.get("rack_readiness_score", 0) >= 70),
            published_count=sum(1 for r in rows if r.get("shopify_product_id") and r.get("status") == "published"),
            missing_ai_data=sum(1 for r in rows if (r.get("ai_readiness_score", 0) or 0) < 40),
            missing_measurements=sum(1 for r in rows if not _has_measurements(r)),
            missing_rack_data=sum(1 for r in rows if (r.get("rack_readiness_score", 0) or 0) < 40),
        )
        return metrics
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{brand_id}/onboarding")
async def update_onboarding_step(brand_id: str, step: int, payload: dict):
    try:
        existing = db.select_by_id("brands", brand_id)
        if not existing.data:
            raise HTTPException(status_code=404, detail="Brand not found")
        data = payload.get("data", {})
        data["updated_at"] = "now()"
        db.update("brands", data, "id", brand_id)
        return {"message": f"Onboarding step {step} saved", "brand_id": brand_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{brand_id}/submit")
async def submit_brand_for_review(brand_id: str):
    try:
        db.update("brands", {"status": "submitted", "updated_at": "now()"}, "id", brand_id)
        db.insert("brand_activity_logs", {
            "id": str(uuid.uuid4()),
            "brand_id": brand_id,
            "action": "brand_submitted_for_review",
            "metadata": {},
        })
        return {"message": "Brand submitted for review", "status": "submitted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _has_measurements(row: dict) -> bool:
    for key in ("chest_width", "waist", "hips"):
        if row.get(key):
            return True
    return False
