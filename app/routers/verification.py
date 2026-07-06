import uuid
import secrets
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Query
from ..models import VerifyTokenRequest, ResendVerificationRequest, VerifyResponse
from ..services.supabase import db
from ..services.email import send_verification_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/brands", tags=["verification"])

RESEND_COOLDOWN_SECONDS = 60
TOKEN_EXPIRE_HOURS = 24


@router.post("/verify", response_model=VerifyResponse)
async def verify_email(token: str = Query(...)):
    try:
        result = db.select("brands", "verification_token", token)
        rows = result.data or []

        if not rows:
            return VerifyResponse(
                verified=False,
                message="This verification link is invalid. Please request a new verification email.",
            )

        row = rows[0]

        if row.get("email_verified"):
            return VerifyResponse(
                verified=True,
                message="Your email is already verified.",
                brand_id=row.get("id"),
            )

        expires_at = row.get("verification_token_expires_at")
        if expires_at:
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                return VerifyResponse(
                    verified=False,
                    message="This verification link has expired. Please request a new verification email.",
                )

        brand_id = row["id"]
        now_iso = datetime.now(timezone.utc).isoformat()
        db.update("brands", {
            "email_verified": True,
            "verified_at": now_iso,
            "verification_token": None,
            "verification_token_expires_at": None,
        }, "id", brand_id)

        logger.info(f"Email verified for brand {brand_id}")
        return VerifyResponse(
            verified=True,
            message="Your email has been verified. You can now continue your brand application.",
            brand_id=brand_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verification error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/resend-verification", response_model=VerifyResponse)
async def resend_verification(payload: ResendVerificationRequest):
    try:
        result = db.select("brands", "contact_email", payload.email)
        rows = result.data or []

        if not rows:
            return VerifyResponse(
                verified=False,
                message="No account found with this email.",
            )

        row = rows[0]

        if row.get("email_verified"):
            return VerifyResponse(
                verified=True,
                message="Your email is already verified.",
                brand_id=row.get("id"),
            )

        brand_id = row["id"]
        brand_name = row.get("name", "Brand")

        sent_at = row.get("verification_email_sent_at")
        if sent_at:
            if isinstance(sent_at, str):
                sent_at = datetime.fromisoformat(sent_at.replace("Z", "+00:00"))
            if sent_at.tzinfo is None:
                sent_at = sent_at.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - sent_at).total_seconds()
            if elapsed < RESEND_COOLDOWN_SECONDS:
                wait = int(RESEND_COOLDOWN_SECONDS - elapsed)
                return VerifyResponse(
                    verified=False,
                    message=f"Please wait {wait}s before requesting another verification email.",
                )

        new_token = secrets.token_urlsafe(48)
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)).isoformat()
        now_iso = datetime.now(timezone.utc).isoformat()

        db.update("brands", {
            "verification_token": new_token,
            "verification_token_expires_at": expires_at,
            "verification_email_sent_at": now_iso,
        }, "id", brand_id)

        email_sent = await send_verification_email(payload.email, new_token, brand_name)
        if not email_sent and not os.getenv("RESEND_API_KEY"):
            logger.warning(f"Verification email not sent (no API key). Token for {payload.email}: {new_token}")

        return VerifyResponse(
            verified=False,
            message="A new verification email has been sent.",
            brand_id=brand_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
