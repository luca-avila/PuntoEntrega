from sqlalchemy.ext.asyncio import AsyncSession

from features.auth import emails as auth_emails
from features.notifications.models import NotificationOutboxEvent
from features.notifications.payloads import require_payload_str


async def handle_verify_email_requested(
    session: AsyncSession,
    event: NotificationOutboxEvent,
) -> None:
    del session
    await auth_emails.send_verify_email(
        require_payload_str(event.payload, "email"),
        require_payload_str(event.payload, "token"),
    )


async def handle_password_reset_requested(
    session: AsyncSession,
    event: NotificationOutboxEvent,
) -> None:
    del session
    await auth_emails.send_reset_password_email(
        require_payload_str(event.payload, "email"),
        require_payload_str(event.payload, "token"),
    )
