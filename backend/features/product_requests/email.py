from datetime import datetime, timedelta, timezone
from html import escape

from features.auth.email import _send_email

ARGENTINA_TIMEZONE = timezone(timedelta(hours=-3), name="ART")


def _format_requested_at_for_argentina(requested_at: datetime) -> str:
    if requested_at.tzinfo is None:
        requested_at = requested_at.replace(tzinfo=timezone.utc)

    requested_at_argentina = requested_at.astimezone(ARGENTINA_TIMEZONE)
    return requested_at_argentina.strftime("%d/%m/%Y %H:%M hs (Argentina, UTC-03:00)")


def _build_product_request_email_html(
    organization_name: str,
    requester_email: str,
    request_subject: str,
    request_message: str,
    requested_at: datetime,
) -> str:
    safe_organization_name = escape(organization_name)
    safe_requester_email = escape(requester_email)
    safe_subject = escape(request_subject)
    safe_message = escape(request_message).replace("\n", "<br/>")
    requested_at_label = _format_requested_at_for_argentina(requested_at)

    return (
        "<h2>Nueva solicitud de producto</h2>"
        "<p>Se registró una nueva solicitud en PuntoEntrega.</p>"
        f"<p><strong>Organización:</strong> {safe_organization_name}</p>"
        f"<p><strong>Solicitado por:</strong> {safe_requester_email}</p>"
        f"<p><strong>Fecha:</strong> {requested_at_label}</p>"
        f"<p><strong>Asunto:</strong> {safe_subject}</p>"
        f"<p><strong>Mensaje:</strong><br/>{safe_message}</p>"
    )


async def send_product_request_email(
    to_email: str,
    organization_name: str,
    requester_email: str,
    request_subject: str,
    request_message: str,
    requested_at: datetime,
) -> None:
    await _send_email(
        to_email=to_email,
        subject=f"Nueva solicitud de producto - {organization_name}",
        html=_build_product_request_email_html(
            organization_name=organization_name,
            requester_email=requester_email,
            request_subject=request_subject,
            request_message=request_message,
            requested_at=requested_at,
        ),
    )
