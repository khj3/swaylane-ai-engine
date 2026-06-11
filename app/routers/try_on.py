import os
import uuid
import json
import logging
import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from ..models import TryOnRequest, TryOnResponse
from ..services.replicate_client import run_replicate
from ..services.supabase import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/try-on", tags=["try-on"])

FLUX_MODEL = "black-forest-labs/flux-schnell"
VTON_MODEL = "yisol/IDM-VTON"


def build_prompt(product_data: dict) -> str:
    title = product_data.get("title", "a fashion item")
    brand = product_data.get("brand", "")
    material = product_data.get("material", "")
    fit_type = product_data.get("fit_type", "")
    parts = [f"A photorealistic model wearing {title}"]
    if brand:
        parts.append(f"by {brand}")
    if material:
        parts.append(f"made of {material}")
    if fit_type:
        parts.append(f"with {fit_type} fit")
    parts.append("studio lighting, white background, fashion photography --no watermark")
    return ", ".join(parts)


def guess_category(product_data: dict) -> str:
    garment_type = (product_data.get("garment_type") or "").lower()
    title = (product_data.get("title") or "").lower()
    combined = garment_type + " " + title
    if any(w in combined for w in ["dress", "gown", "jumpsuit", "romper"]):
        return "dresses"
    if any(w in combined for w in ["pant", "short", "jean", "trouser", "skirt", "legging"]):
        return "lower_body"
    return "upper_body"


def image_to_data_uri(image_bytes: bytes) -> str:
    """Convert image bytes to a data URI for Replicate input."""
    import base64
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64}"


@router.post("", response_model=TryOnResponse)
async def create_try_on(
    customer_id: str = Form(...),
    product_id: str = Form(...),
    product_data: str = Form("{}"),
    selected_mode: str = Form("style_preview"),
    fit_profile_id: str = Form(None),
    measurement_profile_id: str = Form(None),
    image: UploadFile = File(None),
    product_image: UploadFile = File(None),
):
    try:
        product_data_dict = json.loads(product_data)
    except (json.JSONDecodeError, TypeError):
        product_data_dict = {"product_id": product_id}

    status = "failed"
    result_url = None
    confidence_label = "low"

    if selected_mode == "full_ai_try_on" and image is not None:
        # IDM-VTON: virtual try-on with person image + garment image
        try:
            human_bytes = await image.read()

            if product_image is not None:
                garment_bytes = await product_image.read()
                garment_data = image_to_data_uri(garment_bytes)
            else:
                # Try to fetch product image from URL in product_data
                product_img_url = product_data_dict.get("product_image_url") or product_data_dict.get("image_url") or ""
                if product_img_url:
                    async with httpx.AsyncClient(timeout=30) as client:
                        resp = await client.get(product_img_url)
                        resp.raise_for_status()
                        garment_bytes = resp.content
                        garment_data = image_to_data_uri(garment_bytes)
                else:
                    raise HTTPException(status_code=400, detail="No garment image provided. Upload a product image or include product_image_url in product_data.")

            human_data = image_to_data_uri(human_bytes)

            category = guess_category(product_data_dict)

            vton_input = {
                "human_image": human_data,
                "garment_image": garment_data,
                "garment_description": product_data_dict.get("title", "a garment"),
                "category": category,
            }

            output = run_replicate(VTON_MODEL, vton_input, timeout=180)
            if output:
                if isinstance(output, list) and len(output) > 0:
                    result_url = str(output[0])
                elif isinstance(output, str):
                    result_url = output
                status = "completed"
                confidence_label = "high"
        except Exception as e:
            logger.error(f"IDM-VTON failed: {e}. Falling back to flux-schnell.")
            selected_mode = "style_preview"
            confidence_label = "low"

    if status != "completed":
        # Fallback: flux-schnell text-to-image (style preview)
        prompt = build_prompt(product_data_dict)
        flux_input = {
            "prompt": prompt,
            "num_outputs": 1,
            "aspect_ratio": "3:4",
            "output_format": "png",
        }
        try:
            output = run_replicate(FLUX_MODEL, flux_input)
            if output and isinstance(output, list) and len(output) > 0:
                result_url = str(output[0])
                status = "completed"
                confidence_label = "medium"
            elif output and isinstance(output, str):
                result_url = output
                status = "completed"
                confidence_label = "medium"
        except Exception as e:
            logger.error(f"Flux fallback also failed: {e}")
            status = "failed"

    record = {
        "id": str(uuid.uuid4()),
        "customer_id": customer_id,
        "product_id": product_id,
        "product_data": product_data_dict,
        "status": status,
        "result_url": result_url,
        "selected_mode": selected_mode,
        "confidence_label": confidence_label,
    }
    try:
        db.insert("ai_tryon_results", record)
    except Exception:
        pass

    disclaimer = (
        "AI-generated style preview. This is a visual estimate — not an actual photo of you. "
        "Colors, textures, and fit may differ. Add measurements for better size confidence."
    )

    return TryOnResponse(
        id=record["id"],
        status=status,
        result_url=result_url,
        selected_mode=selected_mode,
        confidence_label=confidence_label,
        disclaimer=disclaimer,
    )
