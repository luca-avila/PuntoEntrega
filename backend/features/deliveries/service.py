import uuid
import logging

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from features.deliveries.email import send_delivery_summary_email
from features.deliveries.models import Delivery, DeliveryItem, EmailStatus
from features.deliveries.schemas import DeliveryCreate, DeliveryListFilters
from features.organizations.service import (
    ensure_location_belongs_to_organization,
    ensure_product_belongs_to_organization,
)

logger = logging.getLogger(__name__)


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

    stored_delivery = await get_delivery_for_organization(
        session=session,
        organization_id=organization_id,
        delivery_id=delivery.id,
    )

    try:
        await send_delivery_summary_email(stored_delivery)
        await _update_email_status(session, stored_delivery, EmailStatus.SENT)
    except Exception as exc:
        logger.exception(
            "Failed to send delivery summary email: delivery_id=%s error=%s",
            stored_delivery.id,
            exc,
        )
        await _update_email_status(session, stored_delivery, EmailStatus.FAILED)

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
