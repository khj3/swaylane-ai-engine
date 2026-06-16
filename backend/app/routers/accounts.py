from fastapi import APIRouter, HTTPException
from ..models import AccountCreate, AccountResponse
from ..services.supabase import db

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.post("", response_model=AccountResponse)
async def create_account(payload: AccountCreate):
    try:
        result = db.insert("accounts", payload.dict())
        data = result.data[0] if result.data else {}
        return AccountResponse(id=data.get("id"), email=data.get("email"), message="Account created")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{customer_id}", response_model=AccountResponse)
async def get_account(customer_id: str):
    try:
        result = db.select("accounts", "customer_id", customer_id)
        if not result.data:
            raise HTTPException(status_code=404, detail="Account not found")
        data = result.data[0]
        return AccountResponse(id=data.get("id"), email=data.get("email"))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
