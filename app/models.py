import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class TryOnRequest(BaseModel):
    customer_id: str
    product_id: str
    product_data: dict = {}
    selected_mode: str = "full_ai_try_on"
    fit_profile_id: Optional[str] = None
    measurement_profile_id: Optional[str] = None


class TryOnResponse(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str
    result_url: Optional[str] = None
    selected_mode: str = "full_ai_try_on"
    confidence_label: str = "high"
    disclaimer: str = ""


class AccountCreate(BaseModel):
    customer_id: str
    email: str


class AccountResponse(BaseModel):
    id: Optional[str] = None
    email: Optional[str] = None
    message: Optional[str] = None


class BrandCreate(BaseModel):
    name: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    contact_email: Optional[str] = None


class BrandResponse(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None


class AnalyticsEvent(BaseModel):
    event_type: str
    customer_id: Optional[str] = None
    session_id: Optional[str] = None
    product_id: Optional[str] = None
    transformation_id: Optional[str] = None
    metadata: Optional[dict] = None


class LoyaltyProfile(BaseModel):
    customer_id: str
    points: int = 0
    tier: str = "bronze"


class LoyaltyTransaction(BaseModel):
    customer_id: str
    points: int
    reason: Optional[str] = None
    reference_id: Optional[str] = None


class SavedLookCreate(BaseModel):
    customer_id: str
    transformation_id: str
    notes: Optional[str] = None


class SavedLookResponse(BaseModel):
    id: Optional[str] = None
    message: Optional[str] = None


class PhotoQualityResult(BaseModel):
    photo_quality_score: int
    detected_photo_type: str
    fit_confidence_level: str
    recommended_mode: str
    issues: List[str] = []
    message: str = ""


class FitProfile(BaseModel):
    customer_id: str
    email: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    chest: Optional[str] = None
    waist: Optional[str] = None
    hips: Optional[str] = None
    inseam: Optional[str] = None
    shoulders: Optional[str] = None
    thigh: Optional[str] = None
    arm_length: Optional[str] = None
    torso_length: Optional[str] = None
    usual_shirt_size: Optional[str] = None
    usual_hoodie_size: Optional[str] = None
    usual_pants_size: Optional[str] = None
    usual_jeans_size: Optional[str] = None
    shoe_size: Optional[str] = None
    body_type: Optional[str] = None
    preferred_fit: Optional[str] = None
    style_preference: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class FitProfileCreate(BaseModel):
    customer_id: str
    email: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    chest: Optional[str] = None
    waist: Optional[str] = None
    hips: Optional[str] = None
    inseam: Optional[str] = None
    shoulders: Optional[str] = None
    thigh: Optional[str] = None
    arm_length: Optional[str] = None
    torso_length: Optional[str] = None
    usual_shirt_size: Optional[str] = None
    usual_hoodie_size: Optional[str] = None
    usual_pants_size: Optional[str] = None
    usual_jeans_size: Optional[str] = None
    shoe_size: Optional[str] = None
    body_type: Optional[str] = None
    preferred_fit: Optional[str] = None
    style_preference: Optional[str] = None


class FitProfileUpdate(BaseModel):
    email: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    chest: Optional[str] = None
    waist: Optional[str] = None
    hips: Optional[str] = None
    inseam: Optional[str] = None
    shoulders: Optional[str] = None
    thigh: Optional[str] = None
    arm_length: Optional[str] = None
    torso_length: Optional[str] = None
    usual_shirt_size: Optional[str] = None
    usual_hoodie_size: Optional[str] = None
    usual_pants_size: Optional[str] = None
    usual_jeans_size: Optional[str] = None
    shoe_size: Optional[str] = None
    body_type: Optional[str] = None
    preferred_fit: Optional[str] = None
    style_preference: Optional[str] = None


class SizeRecommendationRequest(BaseModel):
    customer_fit_profile: dict
    product_measurements: dict
    brand_size_chart: Optional[dict] = None
    fit_preference: str = "regular"


class SizeRecommendationResult(BaseModel):
    recommended_size: str
    alternate_size: str
    fit_reason: str
    confidence_score: int
    confidence_label: str
    fit_warning: Optional[str] = None
