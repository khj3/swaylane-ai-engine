import os
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException
from ..services.supabase import db
from ..services.shopify_admin import SHOPIFY_CLIENT_SECRET

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def verify_webhook(request: Request) -> bytes:
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")
    secret = SHOPIFY_CLIENT_SECRET or os.getenv("SHOPIFY_CLIENT_SECRET", "")
    if secret:
        digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
        computed = "sha256=" + hashlib.sha256(digest).hexdigest()
        if computed != hmac_header:
            logger.warning("Shopify webhook HMAC mismatch")
            raise HTTPException(status_code=401, detail="Invalid HMAC")
    else:
        logger.warning("No SHOPIFY_CLIENT_SECRET set, skipping webhook verification")
    return body


def _get_brand_for_product(shopify_product_id: str, shopify_variant_id: str = None) -> tuple:
    try:
        result = db.select("brand_product_connections", "shopify_product_id", shopify_product_id)
        if result.data and len(result.data) > 0:
            row = result.data[0]
            return row["brand_id"], float(row.get("platform_fee_percent", 20))
    except Exception:
        pass
    if shopify_variant_id:
        try:
            result = db.select("brand_product_connections", "shopify_variant_id", shopify_variant_id)
            if result.data and len(result.data) > 0:
                row = result.data[0]
                brand = db.select_by_id("brands", row["brand_id"])
                fee = float(brand.data[0].get("platform_fee_percent", 20)) if brand.data else 20
                return row["brand_id"], fee
        except Exception:
            pass
    return None, 20


def _get_brand_fee(brand_id: str) -> float:
    try:
        brand = db.select_by_id("brands", brand_id)
        if brand.data:
            return float(brand.data[0].get("platform_fee_percent", 20))
    except Exception:
        pass
    return 20


def _process_line_item(item: dict, order_id: str, currency: str, order_created_at: str):
    product_id = str(item.get("product_id", ""))
    variant_id = str(item.get("variant_id", ""))
    line_item_id = str(item.get("id", ""))
    quantity = int(item.get("quantity", 0))

    price = float(item.get("price", 0))
    total_discount = float(item.get("total_discount", 0))
    gross = price * quantity

    brand_id, fee_pct = _get_brand_for_product(product_id, variant_id)
    if not brand_id:
        logger.info("No brand found for product %s variant %s, skipping", product_id, variant_id)
        return

    fee_pct = _get_brand_fee(brand_id)
    net = gross - total_discount
    fee = round(net * fee_pct / 100, 2)
    earnings = round(net - fee, 2)

    existing = db.select("sales_ledger", "shopify_line_item_id", line_item_id)
    if existing.data and len(existing.data) > 0:
        logger.info("Line item %s already processed, skipping", line_item_id)
        return

    entry = {
        "id": str(uuid.uuid4()),
        "shopify_order_id": order_id,
        "shopify_line_item_id": line_item_id,
        "shopify_product_id": product_id,
        "shopify_variant_id": variant_id,
        "brand_id": brand_id,
        "quantity": quantity,
        "gross_sales": round(gross, 2),
        "discounts": round(total_discount, 2),
        "refunds": 0,
        "net_sales": round(net, 2),
        "platform_fee": fee,
        "platform_fee_percent": fee_pct,
        "brand_earnings": earnings,
        "currency": currency,
        "status": "earned",
        "order_created_at": order_created_at,
    }
    db.insert("sales_ledger", entry)
    logger.info("Ledger entry created: order=%s line_item=%s brand=%s earnings=%s",
                order_id, line_item_id, brand_id, earnings)


@router.post("/shopify/orders-paid")
async def handle_order_paid(request: Request):
    await verify_webhook(request)
    body = await request.json()
    order_id = str(body.get("id", ""))
    currency = body.get("currency", "USD")
    created_at = body.get("created_at", "")

    line_items = body.get("line_items", [])
    processed = 0
    errors = 0
    for item in line_items:
        try:
            _process_line_item(item, order_id, currency, created_at)
            processed += 1
        except Exception as e:
            logger.error("Error processing line item %s: %s", item.get("id"), e)
            errors += 1
    return {"message": "Order processed", "line_items_processed": processed, "errors": errors}


@router.post("/shopify/orders-cancelled")
async def handle_order_cancelled(request: Request):
    await verify_webhook(request)
    body = await request.json()
    order_id = str(body.get("id", ""))

    entries = db.select("sales_ledger", "shopify_order_id", order_id)
    if not entries.data:
        return {"message": "No ledger entries found for this order", "updated": 0}

    updated = 0
    for entry in entries.data:
        refund_amt = float(entry.get("brand_earnings", 0))
        db.update("sales_ledger", {
            "refunds": float(entry.get("gross_sales", 0)),
            "net_sales": 0,
            "platform_fee": 0,
            "brand_earnings": 0,
            "status": "cancelled",
            "updated_at": "now()",
        }, "id", entry["id"])
        db.insert("brand_activity_logs", {
            "id": str(uuid.uuid4()),
            "brand_id": entry["brand_id"],
            "action": "order_cancelled",
            "metadata": {"shopify_order_id": order_id, "refund_amount": refund_amt},
        })
        updated += 1
    return {"message": "Order cancelled", "ledger_entries_updated": updated}


@router.post("/shopify/refunds-create")
async def handle_refund(request: Request):
    await verify_webhook(request)
    body = await request.json()
    order_id = str(body.get("order_id", ""))
    transactions = body.get("transactions", [])
    refund_line_items = body.get("refund_line_items", [])

    updated = 0
    for rli in refund_line_items:
        line_item = rli.get("line_item", {})
        line_item_id = str(line_item.get("id", ""))
        refund_qty = int(rli.get("quantity", 0))
        refund_amt = abs(float(rli.get("subtotal", 0)))

        entries = db.select("sales_ledger", "shopify_line_item_id", line_item_id)
        if not entries.data:
            continue
        entry = entries.data[0]
        existing_refunds = float(entry.get("refunds", 0))
        new_refunds = existing_refunds + refund_amt
        gross = float(entry.get("gross_sales", 0))
        discounts = float(entry.get("discounts", 0))
        net = max(0, gross - discounts - new_refunds)
        fee_pct = float(entry.get("platform_fee_percent", 20))
        fee = round(net * fee_pct / 100, 2) if net > 0 else 0
        earnings = round(net - fee, 2) if net > 0 else 0

        status = "refunded" if new_refunds >= gross else "partially_refunded"
        db.update("sales_ledger", {
            "refunds": round(new_refunds, 2),
            "net_sales": round(net, 2),
            "platform_fee": fee,
            "brand_earnings": earnings,
            "status": status,
            "updated_at": "now()",
        }, "id", entry["id"])
        db.insert("brand_activity_logs", {
            "id": str(uuid.uuid4()),
            "brand_id": entry["brand_id"],
            "action": "line_item_refunded",
            "metadata": {
                "shopify_order_id": order_id,
                "shopify_line_item_id": line_item_id,
                "refund_amount": refund_amt,
            },
        })
        updated += 1
    return {"message": "Refund processed", "line_items_updated": updated}
