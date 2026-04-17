import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from features.deliveries.models import Delivery
from features.notifications.email_provider import send_email

logger = logging.getLogger(__name__)

ARGENTINA_TIMEZONE = timezone(timedelta(hours=-3), name="ART")

PAYMENT_METHOD_LABELS_ES = {
    "cash": "Efectivo",
    "transfer": "Transferencia",
    "current_account": "Cuenta corriente",
    "other": "Otro",
}


def _payment_method_label_es(payment_method: str) -> str:
    return PAYMENT_METHOD_LABELS_ES.get(payment_method, payment_method)


def _format_quantity(value: Decimal) -> str:
    return f"{value.normalize():f}" if value != value.to_integral() else str(value.to_integral())


def _format_delivered_at_for_argentina(delivered_at: datetime) -> str:
    if delivered_at.tzinfo is None:
        delivered_at = delivered_at.replace(tzinfo=timezone.utc)

    delivered_at_argentina = delivered_at.astimezone(ARGENTINA_TIMEZONE)
    return delivered_at_argentina.strftime("%d/%m/%Y %H:%M hs (Argentina, UTC-03:00)")


def _format_delivered_at_for_argentina_compact(delivered_at: datetime) -> str:
    if delivered_at.tzinfo is None:
        delivered_at = delivered_at.replace(tzinfo=timezone.utc)

    delivered_at_argentina = delivered_at.astimezone(ARGENTINA_TIMEZONE)
    return delivered_at_argentina.strftime("%d/%m/%Y %H:%M hs")


def _normalize_location_name(value: str | None) -> str:
    if not value:
        return "Sin ubicación"

    normalized = " ".join(value.split()).strip()
    if not normalized:
        return "Sin ubicación"

    return normalized


def _truncate_text(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 1].rstrip()}…"


def _build_delivery_reference(delivery_id: uuid.UUID | str) -> str:
    return str(delivery_id).split("-", maxsplit=1)[0].upper()


def _build_delivery_summary_subject(delivery: Delivery) -> str:
    location_name = _normalize_location_name(delivery.location.name if delivery.location else None)
    location_for_subject = _truncate_text(location_name, 45)
    delivered_at_label = _format_delivered_at_for_argentina_compact(delivery.delivered_at)
    reference = _build_delivery_reference(delivery.id)
    return (
        "PuntoEntrega · "
        f"Entrega en {location_for_subject} · "
        f"{delivered_at_label} · "
        f"Ref {reference}"
    )


def _build_delivery_summary_html(delivery: Delivery) -> str:
    location_name = _normalize_location_name(delivery.location.name if delivery.location else None)
    delivery_reference = _build_delivery_reference(delivery.id)
    items_html = "".join(
        f"<li>{item.product.name if item.product else item.product_id}: cantidad { _format_quantity(item.quantity) }</li>"
        for item in delivery.items
    )

    return (
        "<h2>Resumen de entrega</h2>"
        "<p>Registramos una nueva entrega en tu organización.</p>"
        f"<p><strong>Referencia:</strong> {delivery_reference}</p>"
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

    subject = _build_delivery_summary_subject(delivery)

    await send_email(
        to_email=recipient,
        subject=subject,
        html=_build_delivery_summary_html(delivery),
    )
    logger.info("Delivery summary email sent: delivery_id=%s recipient=%s", delivery.id, recipient)
