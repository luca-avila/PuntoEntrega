import uuid
import logging
import asyncio

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.db import async_session_maker
from features.deliveries.email import send_delivery_summary_email
from features.deliveries.models import Delivery, DeliveryItem, EmailStatus
from features.deliveries.schemas import DeliveryCreate, DeliveryListFilters
from features.organizations.service import (
    ensure_location_belongs_to_organization,
    ensure_product_belongs_to_organization,
)

logger = logging.getLogger(__name__)


EMAIL_SEND_MAX_ATTEMPTS = 3
EMAIL_SEND_RETRY_DELAY_SECONDS = 2.0


def _delivery_load_options():
    return (
        selectinload(Delivery.location),
        selectinload(Delivery.items).selectinload(DeliveryItem.product),
    )


async def list_deliveries_for_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
    filters: DeliveryListFilters,
) -> list[Delivery]:
    query: Select[tuple[Delivery]] = (
        select(Delivery)
        .where(Delivery.organization_id == organization_id)
        .options(*_delivery_load_options())
        .order_by(Delivery.delivered_at.desc(), Delivery.created_at.desc())
    )

    if filters.location_id is not None:
        query = query.where(Delivery.location_id == filters.location_id)
    if filters.delivered_from is not None:
        query = query.where(Delivery.delivered_at >= filters.delivered_from)
    if filters.delivered_to is not None:
        query = query.where(Delivery.delivered_at <= filters.delivered_to)

    result = await session.execute(query)
    return list(result.scalars().all())


async def _update_email_status(
    session: AsyncSession,
    delivery: Delivery,
    email_status: EmailStatus,
) -> None:
    delivery.email_status = email_status
    await session.commit()


async def create_delivery_for_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
    payload: DeliveryCreate,
) -> Delivery:
    await ensure_location_belongs_to_organization(
        session=session,
        organization_id=organization_id,
        location_id=payload.location_id,
    )

    for item in payload.items:
        await ensure_product_belongs_to_organization(
            session=session,
            organization_id=organization_id,
            product_id=item.product_id,
        )

    delivery = Delivery(
        organization_id=organization_id,
        location_id=payload.location_id,
        delivered_at=payload.delivered_at,
        payment_method=payload.payment_method,
        payment_notes=payload.payment_notes,
        observations=payload.observations,
    )

    session.add(delivery)
    await session.flush()

    for item in payload.items:
        session.add(
            DeliveryItem(
                delivery_id=delivery.id,
                product_id=item.product_id,
                quantity=item.quantity,
            )
        )

    await session.commit()

    return await get_delivery_for_organization(
        session=session,
        organization_id=organization_id,
        delivery_id=delivery.id,
    )


async def get_delivery_for_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
    delivery_id: uuid.UUID,
) -> Delivery:
    result = await session.execute(
        select(Delivery)
        .where(
            Delivery.id == delivery_id,
            Delivery.organization_id == organization_id,
        )
        .options(*_delivery_load_options())
    )
    delivery = result.scalar_one_or_none()
    if delivery is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrega no encontrada.",
        )
    return delivery


async def _get_delivery_or_none(
    session: AsyncSession,
    delivery_id: uuid.UUID,
) -> Delivery | None:
    result = await session.execute(
        select(Delivery)
        .where(
            Delivery.id == delivery_id,
        )
        .options(*_delivery_load_options())
    )
    return result.scalar_one_or_none()


async def send_delivery_summary_email_in_background(
    delivery_id: uuid.UUID,
    summary_recipient_email: str | None = None,
) -> None:
    for attempt in range(1, EMAIL_SEND_MAX_ATTEMPTS + 1):
        async with async_session_maker() as session:
            delivery = await _get_delivery_or_none(session, delivery_id)
            if delivery is None:
                logger.warning(
                    "Delivery not found during async email dispatch: delivery_id=%s",
                    delivery_id,
                )
                return

            # Idempotency guard: if another attempt already succeeded, do nothing.
            if delivery.email_status == EmailStatus.SENT:
                return

            try:
                await send_delivery_summary_email(
                    delivery,
                    summary_recipient_email=summary_recipient_email,
                )
                await _update_email_status(session, delivery, EmailStatus.SENT)
                return
            except Exception as exc:
                await session.rollback()
                logger.exception(
                    "Delivery summary email attempt failed: delivery_id=%s attempt=%s error=%s",
                    delivery_id,
                    attempt,
                    exc,
                )

                if attempt >= EMAIL_SEND_MAX_ATTEMPTS:
                    try:
                        latest_delivery = await _get_delivery_or_none(session, delivery_id)
                        if (
                            latest_delivery is not None
                            and latest_delivery.email_status != EmailStatus.SENT
                        ):
                            await _update_email_status(
                                session, latest_delivery, EmailStatus.FAILED
                            )
                    except Exception as status_exc:
                        await session.rollback()
                        logger.exception(
                            "Failed to persist final failed email status: delivery_id=%s error=%s",
                            delivery_id,
                            status_exc,
                        )
                    return

        await asyncio.sleep(EMAIL_SEND_RETRY_DELAY_SECONDS)
