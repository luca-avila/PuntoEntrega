from sqlalchemy.ext.asyncio import AsyncSession

from features.deliveries import emails as delivery_emails
from features.deliveries import service as delivery_service
from features.notifications.errors import NonRetryableNotificationError
from features.notifications.models import NotificationOutboxEvent
from features.notifications.payloads import require_payload_str, require_payload_uuid


async def handle_summary_email_requested(
    session: AsyncSession,
    event: NotificationOutboxEvent,
) -> None:
    delivery_id = require_payload_uuid(event.payload, "delivery_id")
    recipient_email = require_payload_str(event.payload, "summary_recipient_email")
    delivery = await delivery_service._get_delivery_or_none(session, delivery_id)
    if delivery is None:
        raise NonRetryableNotificationError(f"Delivery not found: {delivery_id}")

    await delivery_emails.send_delivery_summary_email(
        delivery,
        summary_recipient_email=recipient_email,
    )
