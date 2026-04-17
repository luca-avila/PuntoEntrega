import asyncio
import json
import logging
from urllib import request
from urllib.error import HTTPError, URLError

from core.config import settings
from features.notifications.errors import EmailSendError

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def extract_resend_error_detail(raw_body: str) -> str:
    if not raw_body:
        return ""
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return raw_body

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


async def send_email(*, to_email: str, subject: str, html: str) -> None:
    if not settings.RESEND_API_KEY:
        raise EmailSendError("RESEND_API_KEY is not set.")

    if not settings.EMAIL_FROM:
        raise EmailSendError("EMAIL_FROM is not set.")

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
        "User-Agent": "punto-entrega/1.0",
    }

    req = request.Request(RESEND_API_URL, data=payload, headers=headers, method="POST")

    try:
        await asyncio.to_thread(request.urlopen, req, timeout=10)
        logger.info("Email sent to %s via Resend.", to_email)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        request_id = exc.headers.get("x-request-id", "") if exc.headers else ""
        detail = extract_resend_error_detail(body)
        raise EmailSendError(
            "Resend HTTP error: "
            f"status={exc.code} reason={exc.reason} request_id={request_id} "
            f"detail={detail} from={settings.EMAIL_FROM} to={to_email} subject={subject}"
        ) from exc
    except URLError as exc:
        raise EmailSendError(
            "Resend network error: "
            f"reason={exc.reason} from={settings.EMAIL_FROM} to={to_email} "
            f"subject={subject}"
        ) from exc
