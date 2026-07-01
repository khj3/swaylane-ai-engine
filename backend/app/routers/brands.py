import uuid
import hashlib
import logging
from fastapi import APIRouter, HTTPException
from ..models import BrandCreate, BrandLogin, BrandResponse, BrandProfile, BrandDashboardMetrics, BrandProductSubmission
from ..services.supabase import db
from ..services.scoring import calculate_ai_readiness, calculate_rack_readiness

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/brands", tags=["brands"])


@router.post("", response_model=BrandResponse)
async def create_brand(payload: BrandCreate):
    try:
        data = payload.dict(exclude_unset=True)
        password = data.pop("password", None)
        owner_name = data.pop("owner_name", None)

        brand_id = str(uuid.uuid4())
        data["id"] = brand_id
        data["status"] = "pending"
        if password:
            data["password_hash"] = hashlib.sha256(password.encode()).hexdigest()

        result = db.insert("brands", data)
        row = result.data[0] if result.data else data

        user_id = str(uuid.uuid4())
        db.insert("brand_users", {
            "id": str(uuid.uuid4()),
            "brand_id": brand_id,
            "user_id": user_id,
            "role": "owner",
            "status": "active",
        })

        db.insert("brand_activity_logs", {
            "id": str(uuid.uuid4()),
            "brand_id": brand_id,
            "user_id": user_id,
            "action": "brand_created",
            "metadata": {"owner_name": owner_name},
        })

        return BrandResponse(
            id=row.get("id"),
            name=row.get("name") or row.get("brand_name") or data.get("name", ""),
            status=row.get("status"),
            user_id=user_id,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=BrandResponse)
async def login_brand(payload: BrandLogin):
    try:
        result = db.select("brands", "contact_email", payload.contact_email)
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        row = result.data[0]
        stored_hash = row.get("password_hash", "")
        input_hash = hashlib.sha256(payload.password.encode()).hexdigest()
        if stored_hash != input_hash:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        user_result = db.select("brand_users", "brand_id", row["id"])
        user_id = user_result.data[0]["user_id"] if user_result.data else ""
        return BrandResponse(
            id=row.get("id"),
            name=row.get("name") or row.get("brand_name"),
            status=row.get("status"),
            user_id=user_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{brand_id}", response_model=BrandProfile)
async def get_brand(brand_id: str):
    try:
        result = db.select_by_id("brands", brand_id)
        if not result.data:
            raise HTTPException(status_code=404, detail="Brand not found")
        row = result.data[0]
        if "brand_name" in row and "name" not in row:
            row["name"] = row.pop("brand_name")
        return BrandProfile(**row)
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
