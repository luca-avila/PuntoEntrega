import logging
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from features.auth import notifications as auth_notifications
from features.deliveries import notifications as delivery_notifications
from features.invitations import notifications as invitation_notifications
from features.notifications.errors import NonRetryableNotificationError
from features.notifications.models import NotificationOutboxEvent
from features.notifications.outbox import (
    EVENT_AUTH_PASSWORD_RESET_REQUESTED,
    EVENT_AUTH_VERIFY_EMAIL_REQUESTED,
    EVENT_DELIVERY_SUMMARY_EMAIL_REQUESTED,
    EVENT_INVITATION_EMAIL_REQUESTED,
    EVENT_PRODUCT_REQUEST_OWNER_NOTIFICATION_REQUESTED,
)
from features.product_requests import notifications as product_request_notifications

logger = logging.getLogger(__name__)

NotificationHandler = Callable[[AsyncSession, NotificationOutboxEvent], Awaitable[None]]
NotificationFailureHandler = Callable[
    [AsyncSession, NotificationOutboxEvent, str],
    Awaitable[None],
]


async def mark_event_notification_failed(
    session: AsyncSession,
    event: NotificationOutboxEvent,
    error_message: str,
) -> None:
    failure_handler = FAILURE_HANDLERS.get(event.event_type)
    if failure_handler is None:
        return

    await failure_handler(session, event, error_message)


HANDLERS: dict[str, NotificationHandler] = {
    EVENT_AUTH_VERIFY_EMAIL_REQUESTED: auth_notifications.handle_verify_email_requested,
    EVENT_AUTH_PASSWORD_RESET_REQUESTED: (
        auth_notifications.handle_password_reset_requested
    ),
    EVENT_INVITATION_EMAIL_REQUESTED: (
        invitation_notifications.handle_organization_invitation_requested
    ),
    EVENT_DELIVERY_SUMMARY_EMAIL_REQUESTED: (
        delivery_notifications.handle_summary_email_requested
    ),
    EVENT_PRODUCT_REQUEST_OWNER_NOTIFICATION_REQUESTED: (
        product_request_notifications.handle_owner_notification_requested
    ),
}

FAILURE_HANDLERS: dict[str, NotificationFailureHandler] = {
    # Intentionally empty: notification delivery state is tracked in outbox.
}


async def handle_notification_event(
    session: AsyncSession,
    event: NotificationOutboxEvent,
) -> None:
    handler = HANDLERS.get(event.event_type)
    if handler is None:
        raise NonRetryableNotificationError(
            f"No notification handler registered for event_type={event.event_type}"
        )

    logger.info(
        "Processing notification event: event_id=%s event_type=%s aggregate_type=%s aggregate_id=%s attempt=%s",
        event.id,
        event.event_type,
        event.aggregate_type,
        event.aggregate_id,
        event.attempts,
    )
    await handler(session, event)
