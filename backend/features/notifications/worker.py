import asyncio
import logging
import socket
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db import async_session_maker
from features.notifications.errors import NonRetryableNotificationError
from features.notifications.handlers import (
    handle_notification_event,
    mark_event_notification_failed,
)
from features.notifications.models import (
    NotificationOutboxEvent,
    NotificationOutboxStatus,
)

logger = logging.getLogger(__name__)
LAST_ERROR_MAX_LENGTH = 2000


def build_worker_id() -> str:
    return f"{socket.gethostname()}-{uuid.uuid4()}"


def truncate_error_message(error_message: str) -> str:
    normalized = error_message.strip()
    if not normalized:
        return "Unknown notification error."
    if len(normalized) <= LAST_ERROR_MAX_LENGTH:
        return normalized
    return normalized[:LAST_ERROR_MAX_LENGTH]


def next_retry_at(attempts: int) -> datetime:
    delay_seconds = settings.NOTIFICATION_OUTBOX_RETRY_BASE_DELAY_SECONDS
    if delay_seconds <= 0:
        return datetime.now(UTC)
    backoff_multiplier = 2 ** max(attempts - 1, 0)
    return datetime.now(UTC) + timedelta(
        seconds=min(delay_seconds * backoff_multiplier, 3600)
    )


async def recover_stale_processing_events(session: AsyncSession) -> int:
    stale_before = datetime.now(UTC) - timedelta(
        seconds=settings.NOTIFICATION_OUTBOX_PROCESSING_TIMEOUT_SECONDS
    )
    result = await session.execute(
        select(NotificationOutboxEvent).where(
            NotificationOutboxEvent.status == NotificationOutboxStatus.PROCESSING,
            NotificationOutboxEvent.locked_at < stale_before,
        )
    )
    stale_events = list(result.scalars().all())
    for event in stale_events:
        event.status = NotificationOutboxStatus.PENDING
        event.locked_at = None
        event.locked_by = None
        event.available_at = datetime.now(UTC)
    return len(stale_events)


async def claim_pending_events(
    session: AsyncSession,
    *,
    worker_id: str,
    batch_size: int,
) -> list[uuid.UUID]:
    await recover_stale_processing_events(session)

    query = (
        select(NotificationOutboxEvent)
        .where(
            NotificationOutboxEvent.status == NotificationOutboxStatus.PENDING,
            NotificationOutboxEvent.available_at <= datetime.now(UTC),
        )
        .order_by(NotificationOutboxEvent.created_at.asc())
        .limit(batch_size)
    )
    if session.get_bind().dialect.name == "postgresql":
        query = query.with_for_update(skip_locked=True)

    result = await session.execute(query)
    events = list(result.scalars().all())
    now = datetime.now(UTC)
    for event in events:
        event.status = NotificationOutboxStatus.PROCESSING
        event.locked_by = worker_id
        event.locked_at = now
        event.attempts += 1
        event.last_error = None

    await session.commit()
    return [event.id for event in events]


def mark_event_processed(event: NotificationOutboxEvent) -> None:
    event.status = NotificationOutboxStatus.PROCESSED
    event.processed_at = datetime.now(UTC)
    event.locked_at = None
    event.locked_by = None
    event.last_error = None


async def mark_event_failed(
    session: AsyncSession,
    event: NotificationOutboxEvent,
    *,
    error_message: str,
    retryable: bool,
) -> None:
    normalized_error = truncate_error_message(error_message)
    event.last_error = normalized_error
    event.locked_at = None
    event.locked_by = None

    if retryable and event.attempts < event.max_attempts:
        event.status = NotificationOutboxStatus.PENDING
        event.available_at = next_retry_at(event.attempts)
        return

    await mark_event_notification_failed(session, event, normalized_error)
    event.status = NotificationOutboxStatus.FAILED


async def process_event(event_id: uuid.UUID) -> None:
    async with async_session_maker() as session:
        event = await session.get(NotificationOutboxEvent, event_id)
        if event is None:
            logger.warning("Claimed notification event disappeared: event_id=%s", event_id)
            return
        if event.status != NotificationOutboxStatus.PROCESSING:
            logger.info(
                "Skipping notification event with unexpected status: event_id=%s status=%s",
                event.id,
                event.status,
            )
            return

        try:
            await handle_notification_event(session, event)
            mark_event_processed(event)
            await session.commit()
            logger.info(
                "Notification event processed: event_id=%s event_type=%s aggregate_type=%s aggregate_id=%s attempt=%s",
                event.id,
                event.event_type,
                event.aggregate_type,
                event.aggregate_id,
                event.attempts,
            )
        except NonRetryableNotificationError as exc:
            await session.rollback()
            event = await session.get(NotificationOutboxEvent, event_id)
            if event is None:
                return
            await mark_event_failed(
                session,
                event,
                error_message=str(exc),
                retryable=False,
            )
            await session.commit()
            logger.warning(
                "Notification event failed permanently: event_id=%s event_type=%s aggregate_type=%s aggregate_id=%s attempt=%s error=%s",
                event.id,
                event.event_type,
                event.aggregate_type,
                event.aggregate_id,
                event.attempts,
                exc,
            )
        except Exception as exc:
            await session.rollback()
            event = await session.get(NotificationOutboxEvent, event_id)
            if event is None:
                return
            await mark_event_failed(
                session,
                event,
                error_message=str(exc),
                retryable=True,
            )
            await session.commit()
            logger.exception(
                "Notification event attempt failed: event_id=%s event_type=%s aggregate_type=%s aggregate_id=%s attempt=%s max_attempts=%s",
                event.id,
                event.event_type,
                event.aggregate_type,
                event.aggregate_id,
                event.attempts,
                event.max_attempts,
            )


async def process_pending_events(
    *,
    worker_id: str | None = None,
    batch_size: int | None = None,
) -> int:
    effective_worker_id = worker_id or build_worker_id()
    async with async_session_maker() as session:
        event_ids = await claim_pending_events(
            session,
            worker_id=effective_worker_id,
            batch_size=batch_size or settings.NOTIFICATION_WORKER_BATCH_SIZE,
        )

    for event_id in event_ids:
        await process_event(event_id)

    return len(event_ids)


async def run_worker_forever() -> None:
    worker_id = build_worker_id()
    logger.info("Notification worker started: worker_id=%s", worker_id)
    while True:
        processed_count = await process_pending_events(worker_id=worker_id)
        if processed_count == 0:
            await asyncio.sleep(settings.NOTIFICATION_WORKER_POLL_INTERVAL_SECONDS)
