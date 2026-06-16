import uuid
import logging
from fastapi import APIRouter, HTTPException
from ..services.supabase import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rack", tags=["rack"])


@router.post("/items")
async def add_to_rack(payload: dict):
    try:
        item = {
            "id": str(uuid.uuid4()),
            "customer_id": payload.get("customer_id", "guest"),
            "product_id": payload.get("product_id", ""),
            "shopify_product_id": payload.get("shopify_product_id", ""),
            "variant_id": payload.get("variant_id", ""),
            "brand_id": payload.get("brand_id", ""),
            "brand_name": payload.get("brand_name", ""),
            "product_title": payload.get("product_title", ""),
            "product_image_url": payload.get("product_image_url", ""),
            "category": payload.get("category", ""),
            "selected_size": payload.get("selected_size", ""),
            "selected_color": payload.get("selected_color", ""),
        }
        db.insert("rack_items", item)
        return {"message": "Added to Rack", "item": item}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/items/{customer_id}")
async def get_rack_items(customer_id: str):
    try:
        result = db.select("rack_items", "customer_id", customer_id)
        return {"items": result.data or []}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/items/{item_id}")
async def remove_rack_item(item_id: str):
    try:
        db.delete("rack_items", "id", item_id)
        return {"message": "Item removed from Rack"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/items/customer/{customer_id}")
async def clear_rack(customer_id: str):
    try:
        items = db.select("rack_items", "customer_id", customer_id)
        if items.data:
            for item in items.data:
                db.delete("rack_items", "id", item["id"])
        return {"message": "Rack cleared"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/outfits")
async def save_outfit(payload: dict):
    try:
        outfit = {
            "id": str(uuid.uuid4()),
            "customer_id": payload.get("customer_id", "guest"),
            "outfit_name": payload.get("outfit_name", "My Outfit"),
            "outfit_slug": payload.get("outfit_name", "my-outfit").lower().replace(" ", "-"),
            "result_image_url": payload.get("result_image_url", ""),
            "fit_confidence_label": payload.get("fit_confidence_label", "medium"),
            "style_notes": payload.get("style_notes", ""),
        }
        db.insert("outfits", outfit)
        items = payload.get("items", [])
        for i, item in enumerate(items):
            item["id"] = str(uuid.uuid4())
            item["outfit_id"] = outfit["id"]
            item["layer_order"] = i
            db.insert("outfit_items", item)
        return {"message": "Outfit saved", "outfit_id": outfit["id"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/outfits/{customer_id}")
async def get_outfits(customer_id: str):
    try:
        result = db.select("outfits", "customer_id", customer_id)
        outfits = result.data or []
        for outfit in outfits:
            items = db.select("outfit_items", "outfit_id", outfit["id"])
            outfit["items"] = items.data or []
        return {"outfits": outfits}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/outfits/{outfit_id}")
async def delete_outfit(outfit_id: str):
    try:
        db.delete("outfits", "id", outfit_id)
        return {"message": "Outfit deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
