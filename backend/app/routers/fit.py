import uuid
import io
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from ..models import (
    PhotoQualityResult,
    FitProfile,
    FitProfileCreate,
    FitProfileUpdate,
    SizeRecommendationRequest,
    SizeRecommendationResult,
)
from ..services.supabase import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fit", tags=["fit"])


# ---------------------------------------------------------------------------
# POST /api/fit/analyze-photo
# ---------------------------------------------------------------------------

@router.post("/analyze-photo", response_model=PhotoQualityResult)
async def analyze_photo(
    image: UploadFile = File(...),
    customer_id: str = Form(None),
):
    issues = []

    try:
        image_bytes = await image.read()
        pil_image = _open_image(image_bytes)
    except Exception as exc:
        logger.warning("analyze-photo: failed to open image — %s", exc)
        return _fallback_result(["Could not read image file"], "Upload a clear photo of yourself.")

    if pil_image is None:
        return _fallback_result(["Could not decode image"], "Upload a supported image format (JPEG, PNG, WebP).")

    # --- Dimension check ---
    width, height = pil_image.size
    min_dim = 200
    dim_issues = []
    if width < min_dim or height < min_dim:
        dim_issues.append(f"Image too small ({width}x{height}). Minimum 200x200 px.")
    if width > 10000 or height > 10000:
        dim_issues.append(f"Image unusually large ({width}x{height}). May affect processing.")
    issues.extend(dim_issues)

    # --- Brightness / contrast ---
    brightness, contrast = _analyze_luminance(pil_image)
    lum_issues = []
    if brightness < 30:
        lum_issues.append("Image is too dark")
    elif brightness > 230:
        lum_issues.append("Image is overexposed")
    if contrast < 15:
        lum_issues.append("Low contrast — image may be flat or poorly lit")
    issues.extend(lum_issues)

    # --- Person detection heuristic ---
    person_found, detection_detail = _detect_person_heuristic(pil_image)
    if not person_found:
        issues.append("No person detected in image")

    # --- Determine photo type ---
    detected_type, quality_score = _classify_photo_type(
        pil_image, person_found, brightness, contrast, detection_detail
    )

    # --- Confidence & mode ---
    if detected_type == "no_person":
        confidence = "low"
        recommended_mode = "style_preview"
        if not issues:
            issues.append("No person detected")
    elif detected_type == "poor_quality":
        confidence = "low"
        recommended_mode = "style_preview"
    elif quality_score >= 70 and person_found:
        confidence = "high"
        recommended_mode = _mode_for_type(detected_type)
    elif quality_score >= 40 and person_found:
        confidence = "medium"
        recommended_mode = _mode_for_type(detected_type)
    else:
        confidence = "low"
        recommended_mode = _mode_for_type(detected_type)

    if dim_issues and person_found and confidence != "low":
        confidence = "medium"
    if not person_found:
        recommended_mode = "style_preview"
        confidence = "low"

    quality_score = max(0, min(100, quality_score))

    message = _build_message(detected_type, confidence, issues)

    # --- Persist ---
    _save_quality_check(customer_id, quality_score, detected_type, confidence, recommended_mode, issues)

    return PhotoQualityResult(
        photo_quality_score=quality_score,
        detected_photo_type=detected_type,
        fit_confidence_level=confidence,
        recommended_mode=recommended_mode,
        issues=issues,
        message=message,
    )


# ---------------------------------------------------------------------------
# POST /api/fit/recommend-size
# ---------------------------------------------------------------------------

@router.post("/recommend-size", response_model=SizeRecommendationResult)
async def recommend_size(payload: SizeRecommendationRequest):
    profile = payload.customer_fit_profile
    product = payload.product_measurements
    brand_chart = payload.brand_size_chart or {}
    preference = payload.fit_preference or "regular"

    # --- Extract numeric measurements ---
    customer_measurements = _extract_measurements(profile)
    product_measurements = _extract_measurements(product)

    if not customer_measurements:
        raise HTTPException(status_code=400, detail="Customer fit profile must contain at least one measurement")

    # --- Determine size fit ---
    recommended_size, alternate_size, fit_reason, confidence_score = _compute_size_recommendation(
        customer_measurements, product_measurements, brand_chart, preference
    )

    fit_warning = None
    diff = _measurement_diff(customer_measurements, product_measurements)
    if abs(diff) > 15:
        fit_warning = "Significant measurement difference — consider trying on in-store."

    confidence_label = "high" if confidence_score >= 80 else "medium" if confidence_score >= 50 else "low"

    # --- Persist ---
    _save_size_rec(
        profile.get("customer_id"),
        product.get("product_id"),
        recommended_size,
        alternate_size,
        confidence_score,
        confidence_label,
        fit_reason,
        fit_warning,
    )

    return SizeRecommendationResult(
        recommended_size=recommended_size,
        alternate_size=alternate_size,
        fit_reason=fit_reason,
        confidence_score=confidence_score,
        confidence_label=confidence_label,
        fit_warning=fit_warning,
    )


# ---------------------------------------------------------------------------
# CRUD /api/fit/profile/
# ---------------------------------------------------------------------------

@router.get("/profile/{customer_id}", response_model=FitProfile)
async def get_fit_profile(customer_id: str):
    try:
        result = db.select("fit_profiles", "customer_id", customer_id)
        if not result.data:
            raise HTTPException(status_code=404, detail="Fit profile not found")
        row = result.data[0]
        row.pop("id", None)
        return FitProfile(**row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/profile", response_model=FitProfile)
async def create_fit_profile(payload: FitProfileCreate):
    try:
        existing = db.select("fit_profiles", "customer_id", payload.customer_id)
        data = payload.dict()
        if existing.data:
            db.update("fit_profiles", data, "customer_id", payload.customer_id)
        else:
            data["id"] = str(uuid.uuid4())
            db.insert("fit_profiles", data)
        result = db.select("fit_profiles", "customer_id", payload.customer_id)
        row = result.data[0] if result.data else data
        row.pop("id", None)
        return FitProfile(**row)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/profile/{customer_id}", response_model=FitProfile)
async def update_fit_profile(customer_id: str, payload: FitProfileUpdate):
    try:
        existing = db.select("fit_profiles", "customer_id", customer_id)
        if not existing.data:
            raise HTTPException(status_code=404, detail="Fit profile not found")
        data = {k: v for k, v in payload.dict().items() if v is not None}
        if data:
            db.update("fit_profiles", data, "customer_id", customer_id)
        result = db.select("fit_profiles", "customer_id", customer_id)
        row = result.data[0]
        row.pop("id", None)
        return FitProfile(**row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/profile/{customer_id}")
async def delete_fit_profile(customer_id: str):
    try:
        existing = db.select("fit_profiles", "customer_id", customer_id)
        if not existing.data:
            raise HTTPException(status_code=404, detail="Fit profile not found")
        db.delete("fit_profiles", "customer_id", customer_id)
        return {"message": "Fit profile deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _open_image(data: bytes):
    try:
        from PIL import Image
        return Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        return None


def _analyze_luminance(pil_image):
    greyscale = pil_image.convert("L")
    pixels = list(greyscale.getdata())
    n = len(pixels)
    if n == 0:
        return 128, 50
    avg = sum(pixels) / n
    variance = sum((p - avg) ** 2 for p in pixels) / n
    contrast = variance ** 0.5
    return avg, contrast


def _detect_person_heuristic(pil_image):
    """
    Basic heuristic: look for skin-colored pixel clusters (face detection
    would require a model). Also checks aspect ratio for body proportions.
    """
    width, height = pil_image.size
    rgb = pil_image.convert("RGB")
    pixels = list(rgb.getdata())

    skin_count = 0
    total = len(pixels)
    sample = pixels[::max(1, total // 20000)]

    for r, g, b in sample:
        if _is_skin_tone(r, g, b):
            skin_count += 1

    skin_ratio = skin_count / max(1, len(sample))

    aspect = width / height if height else 1
    portrait = 0.3 <= aspect <= 1.0

    person_found = skin_ratio > 0.02 and portrait
    detail = {"skin_ratio": round(skin_ratio, 4), "portrait": portrait}

    # If very high skin ratio, definitely a person
    if skin_ratio > 0.15:
        person_found = True
    # Broad landscape with no skin — unlikely person
    if aspect > 1.4 and skin_ratio < 0.01:
        person_found = False

    return person_found, detail


def _is_skin_tone(r, g, b):
    """Simple skin-color range heuristic."""
    if r <= 20 or g <= 10 or b <= 10:
        return False
    if r < 60 and g < 40 and b < 30:
        return False
    if r > 250 and g > 240 and b > 230:
        return False
    return (r > g > b) and (r - g > 5) and (r - g < 80) and (r - b > 10)


def _classify_photo_type(pil_image, person_found, brightness, contrast, detail):
    width, height = pil_image.size
    aspect = width / height if height else 1
    skin_ratio = detail.get("skin_ratio", 0)
    quality_score = 70

    if not person_found:
        return "no_person", 20

    # Score based on brightness and contrast
    quality_score = 50
    if 60 <= brightness <= 200:
        quality_score += 20
    if contrast >= 30:
        quality_score += 15
    elif contrast >= 20:
        quality_score += 8
    if width >= 800 and height >= 800:
        quality_score += 10
    elif width >= 400 and height >= 400:
        quality_score += 5

    # Classify by aspect ratio and skin ratio
    if aspect < 0.5:
        if skin_ratio > 0.08:
            return "headshot", quality_score
        return "poor_quality", max(20, quality_score - 30)
    elif aspect < 0.75:
        if skin_ratio > 0.12:
            return "headshot", quality_score
        elif skin_ratio > 0.04:
            return "waist_up", quality_score
        return "waist_up", max(40, quality_score - 10)
    elif aspect <= 1.0:
        if skin_ratio > 0.06:
            return "full_body", quality_score
        return "waist_up", quality_score
    else:
        if skin_ratio > 0.05:
            return "full_body", quality_score
        return "poor_quality", max(20, quality_score - 20)


def _mode_for_type(detected_type):
    mapping = {
        "full_body": "full_ai_try_on",
        "waist_up": "full_ai_try_on",
        "headshot": "fit_avatar",
        "poor_quality": "style_preview",
        "no_person": "style_preview",
    }
    return mapping.get(detected_type, "style_preview")


def _build_message(detected_type, confidence, issues):
    if detected_type == "no_person":
        return "No person detected. Style preview mode will be used."
    if detected_type == "poor_quality" and confidence == "low":
        return "Photo quality is too low for reliable fit analysis. Style preview recommended."
    if confidence == "high":
        return f"Great photo! Detected {detected_type.replace('_', ' ')}. Ready for AI try-on."
    if detected_type == "headshot":
        return "Headshot detected. Fit avatar mode recommended."
    return f"Detected {detected_type.replace('_', ' ')} with {confidence} confidence."


def _fallback_result(issues, message):
    return PhotoQualityResult(
        photo_quality_score=10,
        detected_photo_type="poor_quality",
        fit_confidence_level="low",
        recommended_mode="style_preview",
        issues=issues,
        message=message,
    )


def _save_quality_check(customer_id, score, detected_type, confidence, mode, issues):
    try:
        db.insert("photo_quality_checks", {
            "id": str(uuid.uuid4()),
            "customer_id": customer_id,
            "image_id": str(uuid.uuid4()),
            "photo_quality_score": score,
            "detected_photo_type": detected_type,
            "fit_confidence_level": confidence,
            "recommended_mode": mode,
            "issues": issues,
        })
    except Exception as exc:
        logger.warning("Failed to save photo_quality_checks: %s", exc)


# ---------------------------------------------------------------------------
# Size recommendation helpers
# ---------------------------------------------------------------------------

_SIZE_MAP = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "3XL", "4XL", "5XL"]


def _extract_measurements(data: dict) -> dict:
    """Pull out numeric measurement values from a dict with string or numeric values."""
    keys = ["chest", "waist", "hips", "inseam", "shoulders", "thigh", "arm_length", "torso_length"]
    result = {}
    for key in keys:
        val = data.get(key)
        if val is not None:
            try:
                result[key] = float(val)
            except (ValueError, TypeError):
                pass
    return result


def _compute_size_recommendation(customer, product, brand_chart, preference):
    """
    Compare customer measurements to product measurements and pick best size.
    """
    if not product:
        return "M", "L", "Standard size recommended (no product measurements)", 50

    # Determine brand fit offset
    brand_offset = 0
    brand_fit = brand_chart.get("fit", "true_to_size") if brand_chart else "true_to_size"
    if brand_fit == "runs_small":
        brand_offset = 1
    elif brand_fit == "runs_large":
        brand_offset = -1

    # Preference offset
    pref_offset = 0
    if preference == "slim":
        pref_offset = -1
    elif preference == "oversized":
        pref_offset = 1

    # Compare key measurements
    primary_keys = ["chest", "waist"]
    differences = []
    for key in primary_keys:
        c_val = customer.get(key)
        p_val = product.get(key)
        if c_val and p_val and p_val > 0:
            diff = c_val - p_val
            differences.append(diff)

    avg_diff = sum(differences) / len(differences) if differences else 0

    # Map diff to size index offset
    if avg_diff < -10:
        size_offset = -2
    elif avg_diff < -5:
        size_offset = -1
    elif avg_diff <= 5:
        size_offset = 0
    elif avg_diff <= 10:
        size_offset = 1
    else:
        size_offset = 2

    total_offset = size_offset + brand_offset + pref_offset
    base_index = _SIZE_MAP.index("M")  # 3
    recommended_index = max(0, min(len(_SIZE_MAP) - 1, base_index - total_offset))
    recommended_size = _SIZE_MAP[recommended_index]

    # Alternate: one step away
    alt_index = max(0, min(len(_SIZE_MAP) - 1, recommended_index + (1 if total_offset >= 0 else -1)))
    alternate_size = _SIZE_MAP[alt_index]
    if alternate_size == recommended_size:
        if recommended_index > 0:
            alternate_size = _SIZE_MAP[recommended_index - 1]
        else:
            alternate_size = _SIZE_MAP[recommended_index + 1]

    # Confidence
    abs_diff = abs(avg_diff)
    if abs_diff <= 3:
        confidence = 90
    elif abs_diff <= 8:
        confidence = 75
    elif abs_diff <= 15:
        confidence = 55
    else:
        confidence = 35

    # Reason
    direction = "smaller" if total_offset > 0 else "larger"
    if total_offset == 0:
        fit_reason = f"Customer measurements align with {recommended_size}."
    else:
        fit_reason = (
            f"Based on measurements and {preference} fit preference, "
            f"a {direction} size ({recommended_size}) is recommended."
        )

    return recommended_size, alternate_size, fit_reason, confidence


def _measurement_diff(customer, product):
    diffs = []
    for key in ["chest", "waist", "hips"]:
        c = customer.get(key)
        p = product.get(key)
        if c and p:
            diffs.append(abs(c - p))
    return sum(diffs) / len(diffs) if diffs else 0


def _save_size_rec(customer_id, product_id, rec_size, alt_size, confidence_score, confidence_label, fit_reason, fit_warning):
    try:
        db.insert("size_recommendations", {
            "id": str(uuid.uuid4()),
            "customer_id": customer_id,
            "product_id": product_id,
            "recommended_size": rec_size,
            "alternate_size": alt_size,
            "confidence_score": confidence_score,
            "confidence_label": confidence_label,
            "fit_reason": fit_reason,
            "fit_warning": fit_warning,
        })
    except Exception as exc:
        logger.warning("Failed to save size_recommendations: %s", exc)
