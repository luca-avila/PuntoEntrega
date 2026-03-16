import asyncio
import json
import logging
from urllib import request
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit

from core.config import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def _extract_resend_error_detail(raw_body: str) -> str:
    if not raw_body:
        return ""
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return raw_body

    # Resend-style error payloads usually include message/name fields.
    if isinstance(payload, dict):
        message = payload.get("message")
        name = payload.get("name")
        if isinstance(message, str) and isinstance(name, str):
            return f"{name}: {message}"
        if isinstance(message, str):
            return message
        if isinstance(name, str):
            return name
    return raw_body


def _normalize_frontend_base_url(raw_url: str) -> str:
    """Return a validated base frontend URL without query/fragment."""
    value = raw_url.strip()

    # Common misconfiguration: protocol accidentally repeated.
    for scheme in ("https://", "http://"):
        duplicated = f"{scheme}{scheme}"
        if value.startswith(duplicated):
            value = value[len(scheme) :]

    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError(
            "FRONTEND_URL must be an absolute http/https URL "
            f"(got: {raw_url!r})"
        )

    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def _build_action_url(path: str, token: str) -> str:
    base = _normalize_frontend_base_url(settings.FRONTEND_URL)
    route = path if path.startswith("/") else f"/{path}"
    return f"{base}{route}?{urlencode({'token': token})}"


async def _send_email(*, to_email: str, subject: str, html: str) -> None:
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY is not set. Skipping email send.")
        return

    if not settings.EMAIL_FROM:
        logger.warning("EMAIL_FROM is not set. Skipping email send.")
        return

    payload = json.dumps(
        {
            "from": settings.EMAIL_FROM,
            "to": [to_email],
            "subject": subject,
            "html": html,
        }
    ).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "auth-module/1.0 (+https://luca-dev.online)",
    }

    req = request.Request(RESEND_API_URL, data=payload, headers=headers, method="POST")

    try:
        await asyncio.to_thread(request.urlopen, req, timeout=10)
        logger.info("Email sent to %s via Resend.", to_email)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        request_id = exc.headers.get("x-request-id", "") if exc.headers else ""
        detail = _extract_resend_error_detail(body)
        logger.error(
            "Failed sending email via Resend: status=%s reason=%s request_id=%s detail=%s from=%s to=%s subject=%s",
            exc.code,
            exc.reason,
            request_id,
            detail,
            settings.EMAIL_FROM,
            to_email,
            subject,
        )
    except URLError as exc:
        logger.error(
            "Failed sending email via Resend: network_error=%s from=%s to=%s subject=%s",
            exc.reason,
            settings.EMAIL_FROM,
            to_email,
            subject,
        )


async def send_verify_email(to_email: str, token: str) -> None:
    try:
        verify_url = _build_action_url(settings.VERIFY_PATH, token)
    except ValueError as exc:
        logger.error("Invalid verification URL config: %s", exc)
        return

    await _send_email(
        to_email=to_email,
        subject="Verify your email",
        html=(
            "<p>Welcome!</p>"
            f"<p>Verify your email by clicking <a href=\"{verify_url}\">this link</a>.</p>"
        ),
    )


async def send_reset_password_email(to_email: str, token: str) -> None:
    try:
        reset_url = _build_action_url(settings.RESET_PASSWORD_PATH, token)
    except ValueError as exc:
        logger.error("Invalid reset-password URL config: %s", exc)
        return

    await _send_email(
        to_email=to_email,
        subject="Reset your password",
        html=(
            "<p>We received a password reset request.</p>"
            f"<p>Reset your password by clicking <a href=\"{reset_url}\">this link</a>.</p>"
            "<p>If you did not request this, you can ignore this email.</p>"
        ),
    )
