import uuid
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from ..services.supabase import db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sales"])


def _calc_brand_summary(brand_id: str):
    entries = db.select("sales_ledger", "brand_id", brand_id)
    rows = entries.data or []
    summary = {
        "total_gross_sales": 0.0,
        "total_discounts": 0.0,
        "total_refunds": 0.0,
        "total_net_sales": 0.0,
        "total_platform_fees": 0.0,
        "total_brand_earnings": 0.0,
        "order_count": 0,
        "currency": "USD",
    }
    seen_orders = set()
    for r in rows:
        summary["total_gross_sales"] += float(r.get("gross_sales", 0))
        summary["total_discounts"] += float(r.get("discounts", 0))
        summary["total_refunds"] += float(r.get("refunds", 0))
        summary["total_net_sales"] += float(r.get("net_sales", 0))
        summary["total_platform_fees"] += float(r.get("platform_fee", 0))
        summary["total_brand_earnings"] += float(r.get("brand_earnings", 0))
        seen_orders.add(r.get("shopify_order_id", ""))
        if r.get("currency"):
            summary["currency"] = r["currency"]
    summary["order_count"] = len(seen_orders)

    payouts = db.select("payouts", "brand_id", brand_id)
    total_paid = sum(float(p.get("amount_paid", 0)) for p in (payouts.data or []) if p.get("payout_status") == "paid")
    summary["total_paid"] = round(total_paid, 2)
    summary["unpaid_earnings"] = round(summary["total_brand_earnings"] - total_paid, 2)

    for k in summary:
        if isinstance(summary[k], float):
            summary[k] = round(summary[k], 2)
    return summary


# ─── Brand-facing endpoints ───────────────────────

@router.get("/brands/{brand_id}/earnings")
async def brand_earnings(brand_id: str):
    try:
        summary = _calc_brand_summary(brand_id)
        brand = db.select_by_id("brands", brand_id)
        name = brand.data[0].get("brand_name", "") if brand.data else ""
        summary["brand_id"] = brand_id
        summary["brand_name"] = name
        return summary
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/brands/{brand_id}/orders")
async def brand_orders(brand_id: str, limit: int = 50, offset: int = 0):
    try:
        entries = db.select("sales_ledger", "brand_id", brand_id)
        rows = entries.data or []
        rows.sort(key=lambda r: r.get("order_created_at", r.get("created_at", "")), reverse=True)
        total = len(rows)
        page = rows[offset:offset + limit]
        return {"orders": page, "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/brands/{brand_id}/payouts")
async def brand_payouts(brand_id: str):
    try:
        result = db.select("payouts", "brand_id", brand_id)
        rows = result.data or []
        rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return {"payouts": rows}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Admin-facing endpoints ───────────────────────

@router.get("/admin/sales")
async def admin_sales_overview():
    try:
        entries = db.select("sales_ledger")
        rows = entries.data or []
        brands_result = db.select("brands")
        all_brands = {b["id"]: b.get("brand_name", "Unknown") for b in (brands_result.data or [])}

        totals = {
            "total_gross_sales": 0.0,
            "total_discounts": 0.0,
            "total_refunds": 0.0,
            "total_net_sales": 0.0,
            "total_platform_fees": 0.0,
            "total_brand_earnings": 0.0,
            "order_count": 0,
            "brand_count": 0,
        }
        brand_totals = {}
        seen_orders = set()
        for r in rows:
            totals["total_gross_sales"] += float(r.get("gross_sales", 0))
            totals["total_discounts"] += float(r.get("discounts", 0))
            totals["total_refunds"] += float(r.get("refunds", 0))
            totals["total_net_sales"] += float(r.get("net_sales", 0))
            totals["total_platform_fees"] += float(r.get("platform_fee", 0))
            totals["total_brand_earnings"] += float(r.get("brand_earnings", 0))
            seen_orders.add(r.get("shopify_order_id", ""))
            bid = r.get("brand_id", "")
            if bid not in brand_totals:
                brand_totals[bid] = {"brand_id": bid, "brand_name": all_brands.get(bid, "Unknown"), "gross_sales": 0.0, "earnings": 0.0}
            brand_totals[bid]["gross_sales"] += float(r.get("gross_sales", 0))
            brand_totals[bid]["earnings"] += float(r.get("brand_earnings", 0))

        totals["order_count"] = len(seen_orders)
        totals["brand_count"] = len(brand_totals)
        for k in totals:
            if isinstance(totals[k], float):
                totals[k] = round(totals[k], 2)
        for b in brand_totals.values():
            b["gross_sales"] = round(b["gross_sales"], 2)
            b["earnings"] = round(b["earnings"], 2)

        return {"summary": totals, "by_brand": list(brand_totals.values())}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/admin/sales/brand/{brand_id}")
async def admin_brand_sales(brand_id: str):
    try:
        summary = _calc_brand_summary(brand_id)
        brand = db.select_by_id("brands", brand_id)
        name = brand.data[0].get("brand_name", "") if brand.data else ""
        summary["brand_id"] = brand_id
        summary["brand_name"] = name
        return summary
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/admin/sales/orders")
async def admin_order_list(limit: int = 50, offset: int = 0):
    try:
        entries = db.select("sales_ledger")
        rows = entries.data or []
        rows.sort(key=lambda r: r.get("order_created_at", r.get("created_at", "")), reverse=True)
        total = len(rows)
        page = rows[offset:offset + limit]
        return {"orders": page, "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/admin/payouts")
async def admin_payout_list(status: str = None):
    try:
        result = db.select("payouts")
        rows = result.data or []
        if status:
            rows = [r for r in rows if r.get("payout_status") == status]
        rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return {"payouts": rows}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/admin/payouts")
async def admin_create_payout(brand_id: str, notes: str = ""):
    try:
        brand = db.select_by_id("brands", brand_id)
        if not brand.data:
            raise HTTPException(status_code=404, detail="Brand not found")
        summary = _calc_brand_summary(brand_id)
        unpaid = summary["unpaid_earnings"]
        if unpaid <= 0:
            raise HTTPException(status_code=400, detail="No unpaid earnings for this brand")

        now = datetime.utcnow()
        period_start = (now - timedelta(days=90)).isoformat()
        period_end = now.isoformat()

        payout = {
            "id": str(uuid.uuid4()),
            "brand_id": brand_id,
            "payout_period_start": period_start,
            "payout_period_end": period_end,
            "gross_sales": summary["total_gross_sales"],
            "total_discounts": summary["total_discounts"],
            "total_refunds": summary["total_refunds"],
            "total_platform_fees": summary["total_platform_fees"],
            "total_brand_earnings": unpaid,
            "amount_paid": unpaid,
            "payout_status": "pending",
            "notes": notes,
        }
        db.insert("payouts", payout)
        return payout
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/admin/payouts/{payout_id}/process")
async def admin_process_payout(payout_id: str, payment_reference: str = ""):
    try:
        existing = db.select_by_id("payouts", payout_id)
        if not existing.data:
            raise HTTPException(status_code=404, detail="Payout not found")
        db.update("payouts", {
            "payout_status": "paid",
            "paid_at": "now()",
            "payment_reference": payment_reference,
            "updated_at": "now()",
        }, "id", payout_id)
        return {"message": "Payout processed", "status": "paid"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
