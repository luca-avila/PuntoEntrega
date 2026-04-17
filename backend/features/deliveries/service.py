import uuid

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from features.deliveries.models import Delivery, DeliveryItem
from features.deliveries.schemas import DeliveryCreate, DeliveryListFilters
from features.notifications.outbox import (
    EVENT_DELIVERY_SUMMARY_EMAIL_REQUESTED,
    enqueue_notification_event,
)
from features.organizations.service import (
    ensure_location_belongs_to_organization,
    ensure_products_belong_to_organization,
)

EMAIL_SEND_MAX_ATTEMPTS = 3


def _delivery_load_options():
    return (
        selectinload(Delivery.location),
        selectinload(Delivery.items).selectinload(DeliveryItem.product),
    )


async def list_deliveries_for_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
    filters: DeliveryListFilters,
    scoped_location_id: uuid.UUID | None = None,
) -> list[Delivery]:
    query: Select[tuple[Delivery]] = (
        select(Delivery)
        .where(Delivery.organization_id == organization_id)
        .options(*_delivery_load_options())
        .order_by(Delivery.delivered_at.desc(), Delivery.created_at.desc())
    )

    if scoped_location_id is not None:
        if filters.location_id is not None and filters.location_id != scoped_location_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El miembro no puede consultar entregas de otra ubicación.",
            )
        query = query.where(Delivery.location_id == scoped_location_id)
    elif filters.location_id is not None:
        query = query.where(Delivery.location_id == filters.location_id)
    if filters.delivered_from is not None:
        query = query.where(Delivery.delivered_at >= filters.delivered_from)
    if filters.delivered_to is not None:
        query = query.where(Delivery.delivered_at <= filters.delivered_to)

    result = await session.execute(query)
    deliveries = list(result.scalars().all())
    for delivery in deliveries:
        setattr(delivery, "location_name", delivery.location.name if delivery.location else None)
        setattr(delivery, "location_address", delivery.location.address if delivery.location else None)
    return deliveries


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

    await ensure_products_belong_to_organization(
        session=session,
        organization_id=organization_id,
        product_ids=(item.product_id for item in payload.items),
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

    await enqueue_notification_event(
        session,
        event_type=EVENT_DELIVERY_SUMMARY_EMAIL_REQUESTED,
        aggregate_type="delivery",
        aggregate_id=delivery.id,
        organization_id=organization_id,
        payload={
            "delivery_id": str(delivery.id),
            "summary_recipient_email": payload.summary_recipient_email,
        },
        deduplication_key=f"delivery:{delivery.id}:summary_email",
        max_attempts=EMAIL_SEND_MAX_ATTEMPTS,
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
    scoped_location_id: uuid.UUID | None = None,
) -> Delivery:
    query = (
        select(Delivery)
        .where(
            Delivery.id == delivery_id,
            Delivery.organization_id == organization_id,
        )
        .options(*_delivery_load_options())
    )
    if scoped_location_id is not None:
        query = query.where(Delivery.location_id == scoped_location_id)

    result = await session.execute(query)
    delivery = result.scalar_one_or_none()
    if delivery is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrega no encontrada.",
        )
    setattr(delivery, "location_name", delivery.location.name if delivery.location else None)
    setattr(delivery, "location_address", delivery.location.address if delivery.location else None)
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
