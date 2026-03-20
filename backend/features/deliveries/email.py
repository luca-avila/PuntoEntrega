import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib import request
from urllib.error import HTTPError, URLError

from core.config import settings
from core.errors import EmailSendError
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


def _extract_resend_error_detail(raw_body: str) -> str:
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


def _payment_method_label_es(payment_method: str) -> str:
    return PAYMENT_METHOD_LABELS_ES.get(payment_method, payment_method)


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
    summary_recipient_email: str,
) -> None:
    recipient = summary_recipient_email.strip()
    if not recipient:
        raise ValueError("summary_recipient_email is required.")

    if not settings.RESEND_API_KEY:
        raise EmailSendError("RESEND_API_KEY is not set.")

    if not settings.EMAIL_FROM:
        raise EmailSendError("EMAIL_FROM is not set.")

    payload = json.dumps(
        {
            "from": settings.EMAIL_FROM,
            "to": [recipient],
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
        logger.info("Delivery summary email sent: delivery_id=%s recipient=%s", delivery.id, recipient)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        request_id = exc.headers.get("x-request-id", "") if exc.headers else ""
        detail = _extract_resend_error_detail(body)
        raise EmailSendError(
            "Resend HTTP error: "
            f"status={exc.code} reason={exc.reason} request_id={request_id} "
            f"detail={detail} from={settings.EMAIL_FROM} to={recipient} "
            f"subject=Resumen de entrega {delivery.id}"
        ) from exc
    except URLError as exc:
        raise EmailSendError(
            "Resend network error: "
            f"reason={exc.reason} from={settings.EMAIL_FROM} to={recipient} "
            f"subject=Resumen de entrega {delivery.id}"
        ) from exc
