from fastapi import APIRouter, HTTPException
from ..models import BrandCreate, BrandResponse
from ..services.supabase import db

router = APIRouter(prefix="/brands", tags=["brands"])


@router.post("", response_model=BrandResponse)
async def create_brand(payload: BrandCreate):
    try:
        result = db.insert("brands", payload.dict())
        data = result.data[0] if result.data else {}
        return BrandResponse(id=data.get("id"), name=data.get("name"), status=data.get("status"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{brand_id}", response_model=BrandResponse)
async def get_brand(brand_id: str):
    try:
        result = db.select_by_id("brands", brand_id)
        if not result.data:
            raise HTTPException(status_code=404, detail="Brand not found")
        data = result.data[0]
        return BrandResponse(id=data.get("id"), name=data.get("name"), status=data.get("status"))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
