from fastapi import APIRouter, HTTPException
from ..models import LoyaltyProfile, LoyaltyTransaction
from ..services.supabase import db
import uuid

router = APIRouter(prefix="/loyalty", tags=["loyalty"])


@router.get("/profile/{customer_id}")
async def get_loyalty_profile(customer_id: str):
    try:
        result = db.select("loyalty_profiles", "customer_id", customer_id)
        if not result.data:
            return {"customer_id": customer_id, "points": 0, "tier": "bronze"}
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/earn")
async def earn_points(payload: LoyaltyTransaction):
    try:
        tx = payload.dict()
        tx["id"] = str(uuid.uuid4())
        tx["transaction_type"] = "earn"
        db.insert("loyalty_transactions", tx)

        profile = db.select("loyalty_profiles", "customer_id", payload.customer_id)
        if profile.data:
            current = profile.data[0]
            new_points = current.get("points", 0) + payload.points
            db.update("loyalty_profiles", {"points": new_points}, "customer_id", payload.customer_id)
        else:
            db.insert("loyalty_profiles", {
                "customer_id": payload.customer_id,
                "points": payload.points,
                "tier": "bronze",
            })
        return {"message": "Points earned", "points": payload.points}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
