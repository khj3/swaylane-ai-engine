from fastapi import APIRouter, HTTPException
from ..models import SavedLookCreate, SavedLookResponse
from ..services.supabase import db

router = APIRouter(prefix="/vault", tags=["vault"])


@router.post("", response_model=SavedLookResponse)
async def save_look(payload: SavedLookCreate):
    try:
        result = db.insert("saved_looks", payload.dict())
        data = result.data[0] if result.data else {}
        return SavedLookResponse(id=data.get("id"), message="Look saved")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{customer_id}")
async def get_saved_looks(customer_id: str):
    try:
        result = db.select("saved_looks", "customer_id", customer_id)
        return {"looks": result.data or []}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{look_id}")
async def delete_saved_look(look_id: str):
    try:
        db.delete("saved_looks", "id", look_id)
        return {"message": "Look deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
