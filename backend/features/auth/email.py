import asyncio
import json
import logging
from urllib import request
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit

from core.config import settings
from core.errors import EmailSendError

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
VERIFY_EMAIL_PATH = "/verify-email"
RESET_PASSWORD_PATH = "/reset-password"


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


def _build_verify_email_html(verify_url: str) -> str:
    return (
        "<p>Hola,</p>"
        "<p>Gracias por registrarte en PuntoEntrega.</p>"
        "<p>Para activar tu cuenta, hac&eacute; click en el siguiente enlace:</p>"
        f"<p><a href=\"{verify_url}\">{verify_url}</a></p>"
        "<p>Si no creaste esta cuenta, pod&eacute;s ignorar este mensaje.</p>"
        "<p>&mdash; Equipo PuntoEntrega</p>"
    )


def _build_reset_password_email_html(reset_url: str) -> str:
    return (
        "<p>Hola,</p>"
        "<p>Recibimos una solicitud para restablecer tu contrase&ntilde;a en PuntoEntrega.</p>"
        "<p>Para crear una nueva contrase&ntilde;a, hac&eacute; click en el siguiente enlace:</p>"
        f"<p><a href=\"{reset_url}\">{reset_url}</a></p>"
        "<p>Si no solicitaste este cambio, pod&eacute;s ignorar este mensaje.</p>"
        "<p>&mdash; Equipo PuntoEntrega</p>"
    )


async def _send_email(*, to_email: str, subject: str, html: str) -> None:
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


async def send_verify_email(to_email: str, token: str) -> None:
    try:
        verify_url = _build_action_url(VERIFY_EMAIL_PATH, token)
    except ValueError as exc:
        raise EmailSendError(f"Invalid verification URL config: {exc}") from exc

    await _send_email(
        to_email=to_email,
        subject="Activa tu cuenta de PuntoEntrega",
        html=_build_verify_email_html(verify_url),
    )


async def send_reset_password_email(to_email: str, token: str) -> None:
    try:
        reset_url = _build_action_url(RESET_PASSWORD_PATH, token)
    except ValueError as exc:
        raise EmailSendError(f"Invalid reset-password URL config: {exc}") from exc

    await _send_email(
        to_email=to_email,
        subject="Restablece tu clave de PuntoEntrega",
        html=_build_reset_password_email_html(reset_url),
    )
