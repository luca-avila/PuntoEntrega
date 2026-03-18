import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_async_session
from features.deliveries.schemas import DeliveryCreate, DeliveryListFilters, DeliveryRead
from features.deliveries.service import (
    create_delivery_for_organization,
    get_delivery_for_organization,
    list_deliveries_for_organization,
    send_delivery_summary_email_in_background,
)
from features.organizations.service import get_current_organization_id

router = APIRouter()


@router.get("", response_model=list[DeliveryRead])
async def list_deliveries(
    location_id: uuid.UUID | None = None,
    delivered_from: datetime | None = None,
    delivered_to: datetime | None = None,
    organization_id: uuid.UUID = Depends(get_current_organization_id),
    session: AsyncSession = Depends(get_async_session),
):
    filters = DeliveryListFilters(
        location_id=location_id,
        delivered_from=delivered_from,
        delivered_to=delivered_to,
    )
    return await list_deliveries_for_organization(
        session=session,
        organization_id=organization_id,
        filters=filters,
    )


@router.post("", response_model=DeliveryRead, status_code=status.HTTP_201_CREATED)
async def create_delivery(
    payload: DeliveryCreate,
    background_tasks: BackgroundTasks,
    organization_id: uuid.UUID = Depends(get_current_organization_id),
    session: AsyncSession = Depends(get_async_session),
):
    delivery = await create_delivery_for_organization(
        session=session,
        organization_id=organization_id,
        payload=payload,
    )
    background_tasks.add_task(
        send_delivery_summary_email_in_background,
        delivery.id,
        payload.summary_recipient_email,
    )
    return delivery


@router.get("/{delivery_id}", response_model=DeliveryRead)
async def get_delivery(
    delivery_id: uuid.UUID,
    organization_id: uuid.UUID = Depends(get_current_organization_id),
    session: AsyncSession = Depends(get_async_session),
):
    return await get_delivery_for_organization(
        session=session,
        organization_id=organization_id,
        delivery_id=delivery_id,
    )
