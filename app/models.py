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
    brand_name: str
    name: Optional[str] = None
    owner_name: str
    contact_email: str
    phone: str
    password: str
    country: str
    state: str
    logo_url: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    brand_category: Optional[str] = None
    legal_business_name: Optional[str] = None
    business_address: Optional[str] = None
    city: Optional[str] = None
    zip: Optional[str] = None
    brand_style: Optional[str] = None
    target_customer: Optional[str] = None
    price_range: Optional[str] = None
    fit_identity: Optional[str] = None
    brand_story: Optional[str] = None
    shipping_policy: Optional[str] = None
    return_policy: Optional[str] = None
    processing_time: Optional[str] = None
    customer_support_email: Optional[str] = None
    instagram: Optional[str] = None
    tiktok: Optional[str] = None
    contact_phone: Optional[str] = None


class BrandLogin(BaseModel):
    contact_email: str
    password: str


class BrandResponse(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None
    user_id: Optional[str] = None
    email_verified: Optional[bool] = None


class VerifyTokenRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: str


class VerifyResponse(BaseModel):
    verified: bool
    message: str
    brand_id: Optional[str] = None


class BrandProfile(BaseModel):
    name: Optional[str] = None
    brand_slug: Optional[str] = None
    status: Optional[str] = None
    email_verified: Optional[bool] = None
    contact_email: Optional[str] = None
    logo_url: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    instagram: Optional[str] = None
    tiktok: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    legal_business_name: Optional[str] = None
    business_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = None
    brand_category: Optional[str] = None
    brand_style: Optional[str] = None
    target_customer: Optional[str] = None
    price_range: Optional[str] = None
    fit_identity: Optional[str] = None
    shipping_policy: Optional[str] = None
    return_policy: Optional[str] = None
    processing_time: Optional[str] = None
    customer_support_email: Optional[str] = None
    rights_confirmation: Optional[bool] = None
    rules_agreement: Optional[bool] = None
    example_photo_urls: Optional[str] = None


class BrandProductSubmission(BaseModel):
    id: Optional[str] = None
    brand_id: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    product_type: Optional[str] = None
    price: Optional[float] = None
    compare_at_price: Optional[float] = None
    sku: Optional[str] = None
    inventory_quantity: int = 0
    shipping_weight: Optional[float] = None
    tags: Optional[str] = None
    material_composition: Optional[str] = None
    fabric_weight: Optional[str] = None
    stretch_level: Optional[str] = None
    thickness: Optional[str] = None
    care_instructions: Optional[str] = None
    season: Optional[str] = None
    fit_type: Optional[str] = None
    fit_notes: Optional[str] = None
    model_height: Optional[str] = None
    model_weight: Optional[str] = None
    model_wearing_size: Optional[str] = None
    runs_small: bool = False
    true_to_size: bool = True
    runs_large: bool = False
    garment_type: Optional[str] = None
    ai_ready: bool = False
    prompt_guidance: Optional[str] = None
    tryon_image_url: Optional[str] = None
    fabric_behavior: Optional[str] = None
    ai_limitations: Optional[str] = None
    supports_full_body_tryon: bool = True
    supports_style_preview: bool = True
    rack_ready: bool = False
    layer_category: Optional[str] = None
    can_layer: bool = True
    recommended_pairings: Optional[str] = None
    conflicting_categories: Optional[str] = None
    styling_notes: Optional[str] = None
    outfit_prompt_guidance: Optional[str] = None
    status: str = "draft"
    variants: Optional[List[dict]] = None
    images: Optional[List[dict]] = None
    measurements: Optional[List[dict]] = None


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


class BrandDashboardMetrics(BaseModel):
    total_products: int = 0
    draft_products: int = 0
    submitted_products: int = 0
    approved_products: int = 0
    rejected_products: int = 0
    ai_ready_count: int = 0
    rack_ready_count: int = 0
    published_count: int = 0
    missing_ai_data: int = 0
    missing_measurements: int = 0
    missing_rack_data: int = 0


class BrandProductConnection(BaseModel):
    id: Optional[str] = None
    shopify_product_id: str
    shopify_variant_id: Optional[str] = None
    brand_id: str
    product_title: Optional[str] = None
    vendor_name: Optional[str] = None
    status: str = "active"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SalesLedgerEntry(BaseModel):
    id: Optional[str] = None
    shopify_order_id: str
    shopify_line_item_id: str
    shopify_product_id: Optional[str] = None
    shopify_variant_id: Optional[str] = None
    brand_id: str
    quantity: int = 0
    gross_sales: float = 0
    discounts: float = 0
    refunds: float = 0
    net_sales: float = 0
    platform_fee: float = 0
    platform_fee_percent: float = 20.0
    brand_earnings: float = 0
    currency: str = "USD"
    status: str = "earned"
    order_created_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PayoutRecord(BaseModel):
    id: Optional[str] = None
    brand_id: str
    payout_period_start: Optional[str] = None
    payout_period_end: Optional[str] = None
    gross_sales: float = 0
    total_discounts: float = 0
    total_refunds: float = 0
    total_platform_fees: float = 0
    total_brand_earnings: float = 0
    amount_paid: float = 0
    payout_status: str = "pending"
    paid_at: Optional[str] = None
    payment_reference: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class BrandEarningsSummary(BaseModel):
    brand_id: str
    brand_name: str
    total_gross_sales: float = 0
    total_discounts: float = 0
    total_refunds: float = 0
    total_net_sales: float = 0
    total_platform_fees: float = 0
    total_brand_earnings: float = 0
    unpaid_earnings: float = 0
    total_paid: float = 0
    order_count: int = 0
    currency: str = "USD"
