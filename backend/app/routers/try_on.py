import os
import uuid
import json
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from ..models import TryOnRequest, TryOnResponse
from ..services.replicate_client import run_replicate
from ..services.supabase import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/try-on", tags=["try-on"])

FLUX_MODEL = "black-forest-labs/flux-schnell"


def build_prompt(product_data: dict, mode: str) -> str:
    title = product_data.get("title", "a fashion item")
    brand = product_data.get("brand", "")
    material = product_data.get("material", "")
    fit_type = product_data.get("fit_type", "")
    parts = [f"A fashion model wearing {title}"]
    if brand:
        parts.append(f"by {brand}")
    if material:
        parts.append(f"made of {material}")
    if fit_type:
        parts.append(f"with {fit_type} fit")
    if mode == "style_preview":
        parts.append("style preview, soft lighting")
    else:
        parts.append("studio lighting, white background, fashion photography")
    parts.append("--no watermark, no text")
    return ", ".join(parts)


@router.post("", response_model=TryOnResponse)
async def create_try_on(
    customer_id: str = Form("guest"),
    product_id: str = Form(""),
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

    prompt = build_prompt(product_data_dict, selected_mode)

    flux_input = {
        "prompt": prompt,
        "num_outputs": 1,
        "aspect_ratio": "3:4",
        "output_format": "png",
    }

    status = "failed"
    result_url = None
    confidence_label = "low"

    try:
        output = run_replicate(FLUX_MODEL, flux_input)
        if output and isinstance(output, list) and len(output) > 0:
            result_url = str(output[0])
            status = "completed"
            confidence_label = "medium" if selected_mode == "style_preview" else "high"
        elif output and isinstance(output, str):
            result_url = output
            status = "completed"
            confidence_label = "medium"
    except Exception as e:
        logger.error(f"Replicate generation failed: {e}")
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
        "AI-generated style preview. This is a visual estimate based on the product description — "
        "not an actual photo of you wearing the item. Colors, textures, and fit may differ. "
        "Add measurements and use size recommendations for better fit confidence."
    )

    return TryOnResponse(
        id=record["id"],
        status=status,
        result_url=result_url,
        selected_mode=selected_mode,
        confidence_label=confidence_label,
        disclaimer=disclaimer,
    )
