import os
import logging

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
BRAND_PORTAL_URL = os.getenv("BRAND_PORTAL_URL", "https://swaylanestudio.com/pages/brand-portal")
EMAIL_FROM = os.getenv("EMAIL_FROM", "Sway Lane <noreply@swaylanestudio.com>")

async def send_verification_email(to_email: str, token: str, brand_name: str):
    verify_url = f"{BRAND_PORTAL_URL}?verify={token}"

    if not RESEND_API_KEY:
        logger.warning(f"RESEND_API_KEY not set. Verification URL: {verify_url}")
        return False

    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                "from": EMAIL_FROM,
                "to": [to_email],
                "subject": "Verify your Sway Lane Brand Account",
                "html": f"""<!DOCTYPE html>
<html>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f5f5;margin:0;padding:0">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:40px 20px">
<tr><td align="center">
<table width="480" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08)">
<tr><td style="padding:32px 32px 0;text-align:center">
<img src="https://swaylanestudio.com/cdn/shop/files/sway-lane-logo.png" alt="Sway Lane" style="height:36px;margin-bottom:24px">
<h1 style="font-size:22px;font-weight:700;color:#1a1a1a;margin:0 0 8px">Verify your email</h1>
<p style="font-size:15px;color:#666;line-height:1.5;margin:0 0 24px">Welcome to Sway Lane, <strong>{brand_name}</strong>.<br>Click the button below to verify your email and continue your brand application.</p>
<a href="{verify_url}" style="display:inline-block;background:#1a1a1a;color:#fff;font-size:15px;font-weight:600;padding:14px 36px;border-radius:8px;text-decoration:none">Verify Email</a>
<p style="font-size:13px;color:#999;margin:24px 0 0;line-height:1.4">This link expires in 24 hours. If you did not create a Sway Lane brand account, you can safely ignore this email.</p>
</td></tr>
<tr><td style="padding:24px 32px;text-align:center;border-top:1px solid #eee">
<p style="font-size:12px;color:#aaa;margin:0">&copy; 2026 Sway Lane Studio. All rights reserved.</p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>""",
            },
        )
        logger.info(f"Verification email sent to {to_email}: {resp.status_code}")
        try:
            body_text = resp.text
            if body_text:
                logger.info(f"Resend response body: {body_text[:500]}")
        except Exception:
            pass
        return resp.is_success
    except Exception as e:
        logger.error(f"Failed to send verification email: {e}")
        return False
