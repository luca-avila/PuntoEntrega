from sqlalchemy.ext.asyncio import AsyncSession

from features.invitations import emails as invitation_emails
from features.notifications.models import NotificationOutboxEvent
from features.notifications.payloads import require_payload_str


async def handle_organization_invitation_requested(
    session: AsyncSession,
    event: NotificationOutboxEvent,
) -> None:
    del session
    await invitation_emails.send_organization_invitation_email(
        to_email=require_payload_str(event.payload, "to_email"),
        organization_name=require_payload_str(event.payload, "organization_name"),
        token=require_payload_str(event.payload, "token"),
    )
