import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_async_session
from features.locations.schemas import LocationCreate, LocationRead, LocationUpdate
from features.locations.service import (
    create_location_for_organization,
    get_location_for_organization,
    list_locations_for_organization,
    update_location_for_organization,
)
from features.organizations.service import get_current_organization_id

router = APIRouter()


@router.get("", response_model=list[LocationRead])
async def list_locations(
    organization_id: uuid.UUID = Depends(get_current_organization_id),
    session: AsyncSession = Depends(get_async_session),
):
    return await list_locations_for_organization(
        session=session,
        organization_id=organization_id,
    )


@router.post("", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
async def create_location(
    payload: LocationCreate,
    organization_id: uuid.UUID = Depends(get_current_organization_id),
    session: AsyncSession = Depends(get_async_session),
):
    return await create_location_for_organization(
        session=session,
        organization_id=organization_id,
        payload=payload,
    )


@router.get("/{location_id}", response_model=LocationRead)
async def get_location(
    location_id: uuid.UUID,
    organization_id: uuid.UUID = Depends(get_current_organization_id),
    session: AsyncSession = Depends(get_async_session),
):
    return await get_location_for_organization(
        session=session,
        organization_id=organization_id,
        location_id=location_id,
    )


@router.patch("/{location_id}", response_model=LocationRead)
async def patch_location(
    location_id: uuid.UUID,
    payload: LocationUpdate,
    organization_id: uuid.UUID = Depends(get_current_organization_id),
    session: AsyncSession = Depends(get_async_session),
):
    return await update_location_for_organization(
        session=session,
        organization_id=organization_id,
        location_id=location_id,
        payload=payload,
    )

