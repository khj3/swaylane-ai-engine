import os
import json
import uuid
import time
import logging
import httpx

logger = logging.getLogger(__name__)

from .supabase import db

SHOPIFY_SHOP = os.getenv("SHOPIFY_SHOP", "")
SHOPIFY_ADMIN_TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN", "")
SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID", "")
SHOPIFY_CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET", "")
SHOPIFY_API_VERSION = "2024-04"

BASE_URL = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}"
TOKEN_URL = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/oauth/access_token"

_token_cache = {"token": "", "expires_at": 0}


def is_configured():
    return bool(SHOPIFY_SHOP and (SHOPIFY_ADMIN_TOKEN or (SHOPIFY_CLIENT_ID and SHOPIFY_CLIENT_SECRET)))


async def _get_token():
    if SHOPIFY_ADMIN_TOKEN:
        return SHOPIFY_ADMIN_TOKEN
    if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(TOKEN_URL, json={
                "client_id": SHOPIFY_CLIENT_ID,
                "client_secret": SHOPIFY_CLIENT_SECRET,
                "grant_type": "client_credentials",
            }, timeout=15)
            if resp.status_code >= 400:
                logger.error("Shopify OAuth error %s: %s", resp.status_code, resp.text)
                return ""
            body = resp.json()
            _token_cache["token"] = body.get("access_token", "")
            _token_cache["expires_at"] = time.time() + body.get("expires_in", 3000) - 60
            return _token_cache["token"]
    except Exception as e:
        logger.error("Shopify OAuth failed: %s", e)
        return ""


async def _api(method: str, path: str, data: dict = None):
    if not is_configured():
        logger.warning("Shopify Admin API not configured")
        return None
    token = await _get_token()
    if not token:
        logger.warning("No Shopify access token available")
        return None
    url = f"{BASE_URL}{path}"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": token,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.request(method, url, json=data, headers=headers, timeout=30)
        if resp.status_code >= 400:
            logger.error("Shopify API error %s: %s", resp.status_code, resp.text)
            return None
        return resp.json()


async def create_product(submission: dict, brand_name: str):
    product_data = {
        "product": {
            "title": submission.get("title", ""),
            "body_html": submission.get("description", ""),
            "vendor": brand_name,
            "product_type": submission.get("product_type", ""),
            "status": "draft",
            "tags": _build_tags(submission, brand_name),
        }
    }
    result = await _api("POST", "/products.json", product_data)
    if result and result.get("product"):
        shopify_id = str(result["product"]["id"])
        await _add_metafields(shopify_id, submission, brand_name)
        if submission.get("variants"):
            await _add_variants(shopify_id, submission["variants"])
        if submission.get("images"):
            await _add_images(shopify_id, submission["images"])
        brand_id = submission.get("brand_id", "")
        if brand_id:
            try:
                db.insert("brand_product_connections", {
                    "id": str(uuid.uuid4()),
                    "shopify_product_id": shopify_id,
                    "brand_id": brand_id,
                    "product_title": submission.get("title", ""),
                    "vendor_name": brand_name,
                    "status": "active",
                })
            except Exception as e:
                logger.error("Failed to store brand connection: %s", e)
        return shopify_id
    return None


async def _add_metafields(shopify_id: str, submission: dict, brand_name: str):
    metafields = [
        _mf("custom", "brand_id", submission.get("brand_id", "")),
        _mf("swaylane.brand", "brand_id", submission.get("brand_id", "")),
        _mf("swaylane.brand", "brand_name", brand_name),
        _mf("swaylane.fit", "fit_type", submission.get("fit_type", "")),
        _mf("swaylane.fit", "fit_notes", submission.get("fit_notes", "")),
        _mf("swaylane.fit", "model_height", submission.get("model_height", "")),
        _mf("swaylane.fit", "model_weight", submission.get("model_weight", "")),
        _mf("swaylane.fit", "model_wearing_size", submission.get("model_wearing_size", "")),
        _mf("swaylane.fit", "runs_small", str(submission.get("runs_small", False))),
        _mf("swaylane.fit", "true_to_size", str(submission.get("true_to_size", True))),
        _mf("swaylane.fit", "runs_large", str(submission.get("runs_large", False))),
        _mf("swaylane.ai", "ai_ready", str(submission.get("ai_ready", False))),
        _mf("swaylane.ai", "garment_type", submission.get("garment_type", "")),
        _mf("swaylane.ai", "prompt_guidance", submission.get("prompt_guidance", "")),
        _mf("swaylane.ai", "stretch_level", submission.get("stretch_level_ai", "")),
        _mf("swaylane.ai", "supports_full_body_tryon", str(submission.get("supports_full_body_tryon", True))),
        _mf("swaylane.ai", "supports_style_preview", str(submission.get("supports_style_preview", True))),
        _mf("swaylane.material", "material_composition", submission.get("material_composition", "")),
        _mf("swaylane.material", "fabric_weight", submission.get("fabric_weight", "")),
        _mf("swaylane.material", "thickness", submission.get("thickness", "")),
        _mf("swaylane.material", "care_instructions", submission.get("care_instructions", "")),
        _mf("swaylane.marketplace", "approval_status", "approved"),
        _mf("swaylane.marketplace", "submitted_by_brand", brand_name),
        _mf("swaylane.rack", "rack_ready", str(submission.get("rack_ready", False))),
        _mf("swaylane.rack", "layer_category", submission.get("layer_category", "")),
        _mf("swaylane.rack", "can_layer", str(submission.get("can_layer", True))),
        _mf("swaylane.rack", "styling_notes", submission.get("styling_notes", "")),
    ]
    for mf in metafields:
        await _api("POST", f"/products/{shopify_id}/metafields.json", {"metafield": mf})


def _mf(namespace: str, key: str, value: str):
    return {
        "namespace": namespace,
        "key": key,
        "value": value,
        "type": "single_line_text_field",
    }


def _build_tags(submission: dict, brand_name: str) -> str:
    tags = [brand_name]
    if submission.get("ai_ready"):
        tags.append("AI Ready")
    if submission.get("category"):
        tags.append(submission["category"])
    if submission.get("fit_type"):
        tags.append(submission["fit_type"])
    if submission.get("material_composition"):
        tags.append(submission["material_composition"])
    if submission.get("rack_ready"):
        tags.append("Rack Ready")
    if submission.get("layer_category"):
        tags.append(submission["layer_category"])
    return ", ".join(tags)


async def _add_variants(shopify_id: str, variants: list):
    for v in variants:
        v_data = {
            "variant": {
                "product_id": shopify_id,
                "option1": v.get("size", ""),
                "option2": v.get("color", ""),
                "sku": v.get("sku", ""),
                "price": str(v.get("price", 0)),
                "inventory_quantity": v.get("inventory_quantity", 0),
            }
        }
        await _api("POST", f"/products/{shopify_id}/variants.json", v_data)


async def _add_images(shopify_id: str, images: list):
    for img in images:
        img_data = {
            "image": {
                "product_id": shopify_id,
                "src": img.get("image_url", ""),
                "alt": img.get("alt_text", ""),
                "position": img.get("sort_order", 1),
            }
        }
        await _api("POST", f"/products/{shopify_id}/images.json", img_data)


async def publish_product(shopify_id: str):
    return await _api("PUT", f"/products/{shopify_id}.json", {
        "product": {"id": int(shopify_id), "status": "active"}
    })


async def unpublish_product(shopify_id: str):
    return await _api("PUT", f"/products/{shopify_id}.json", {
        "product": {"id": int(shopify_id), "status": "draft"}
    })
