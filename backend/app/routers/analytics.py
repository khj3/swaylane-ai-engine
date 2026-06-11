from fastapi import APIRouter, HTTPException
from ..models import AnalyticsEvent
from ..services.supabase import db

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.post("/events")
async def track_event(payload: AnalyticsEvent):
    try:
        db.insert("analytics_events", payload.dict())
        return {"message": "Event tracked"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/events/{customer_id}")
async def get_events(customer_id: str, limit: int = 50):
    try:
        result = db.select("analytics_events", "customer_id", customer_id)
        data = result.data or []
        return {"events": data[:limit]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
