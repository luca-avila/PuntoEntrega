import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from features.notifications.models import (
    NotificationOutboxEvent,
    NotificationOutboxStatus,
)

EVENT_AUTH_VERIFY_EMAIL_REQUESTED = "auth.verify_email_requested"
EVENT_AUTH_PASSWORD_RESET_REQUESTED = "auth.password_reset_requested"
EVENT_INVITATION_EMAIL_REQUESTED = "invitations.organization_invitation_requested"
EVENT_DELIVERY_SUMMARY_EMAIL_REQUESTED = "deliveries.summary_email_requested"
EVENT_PRODUCT_REQUEST_OWNER_NOTIFICATION_REQUESTED = (
    "product_requests.owner_notification_requested"
)


async def enqueue_notification_event(
    session: AsyncSession,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: uuid.UUID,
    payload: dict[str, Any],
    deduplication_key: str,
    organization_id: uuid.UUID | None = None,
    max_attempts: int | None = None,
    available_at: datetime | None = None,
) -> NotificationOutboxEvent:
    existing_event = await session.scalar(
        select(NotificationOutboxEvent).where(
            NotificationOutboxEvent.deduplication_key == deduplication_key
        )
    )
    if existing_event is not None:
        return existing_event

    event = NotificationOutboxEvent(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        organization_id=organization_id,
        payload=payload,
        deduplication_key=deduplication_key,
        max_attempts=max_attempts or settings.NOTIFICATION_OUTBOX_MAX_ATTEMPTS,
        available_at=available_at or datetime.now(UTC),
        status=NotificationOutboxStatus.PENDING,
    )
    session.add(event)
    return event
