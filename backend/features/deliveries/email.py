import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib import request
from urllib.error import HTTPError, URLError

from core.config import settings
from features.deliveries.models import Delivery

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
ARGENTINA_TIMEZONE = timezone(timedelta(hours=-3), name="ART")

PAYMENT_METHOD_LABELS_ES = {
    "cash": "Efectivo",
    "transfer": "Transferencia",
    "current_account": "Cuenta corriente",
    "other": "Otro",
}


def _payment_method_label_es(payment_method: str) -> str:
    return PAYMENT_METHOD_LABELS_ES.get(payment_method, payment_method)


def _parse_recipients(raw_recipients: str) -> list[str]:
    return [recipient.strip() for recipient in raw_recipients.split(",") if recipient.strip()]


def _resolve_recipients(default_recipients_raw: str, summary_recipient_email: str | None) -> list[str]:
    if summary_recipient_email is not None:
        normalized_summary_recipient_email = summary_recipient_email.strip()
        if normalized_summary_recipient_email:
            return [normalized_summary_recipient_email]

    return _parse_recipients(default_recipients_raw)


def _format_quantity(value: Decimal) -> str:
    return f"{value.normalize():f}" if value != value.to_integral() else str(value.to_integral())


def _format_delivered_at_for_argentina(delivered_at: datetime) -> str:
    if delivered_at.tzinfo is None:
        delivered_at = delivered_at.replace(tzinfo=timezone.utc)

    delivered_at_argentina = delivered_at.astimezone(ARGENTINA_TIMEZONE)
    return delivered_at_argentina.strftime("%d/%m/%Y %H:%M hs (Argentina, UTC-03:00)")


def _build_delivery_summary_html(delivery: Delivery) -> str:
    location_name = delivery.location.name if delivery.location else "Sin ubicación"
    items_html = "".join(
        f"<li>{item.product.name if item.product else item.product_id}: cantidad { _format_quantity(item.quantity) }</li>"
        for item in delivery.items
    )

    return (
        "<h2>Resumen de entrega</h2>"
        f"<p><strong>Entrega:</strong> {delivery.id}</p>"
        f"<p><strong>Ubicación:</strong> {location_name}</p>"
        "<p><strong>Fecha de entrega:</strong> "
        f"{_format_delivered_at_for_argentina(delivery.delivered_at)}</p>"
        f"<p><strong>Método de pago:</strong> {_payment_method_label_es(delivery.payment_method.value)}</p>"
        f"<p><strong>Notas de pago:</strong> {delivery.payment_notes or '-'}</p>"
        f"<p><strong>Observaciones:</strong> {delivery.observations or '-'}</p>"
        "<p><strong>Items:</strong></p>"
        f"<ul>{items_html}</ul>"
    )


async def send_delivery_summary_email(
    delivery: Delivery,
    summary_recipient_email: str | None = None,
) -> None:
    recipients = _resolve_recipients(
        default_recipients_raw=settings.DELIVERY_SUMMARY_RECIPIENTS,
        summary_recipient_email=summary_recipient_email,
    )
    if not recipients:
        raise ValueError("No delivery summary recipients configured.")

    if not settings.RESEND_API_KEY:
        raise ValueError("RESEND_API_KEY is not set.")

    if not settings.EMAIL_FROM:
        raise ValueError("EMAIL_FROM is not set.")

    payload = json.dumps(
        {
            "from": settings.EMAIL_FROM,
            "to": recipients,
            "subject": f"Resumen de entrega {delivery.id}",
            "html": _build_delivery_summary_html(delivery),
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
        logger.info("Delivery summary email sent: delivery_id=%s recipients=%s", delivery.id, recipients)
    except HTTPError as exc:
        raise RuntimeError(f"Resend HTTP error: {exc.code} {exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"Resend network error: {exc.reason}") from exc
