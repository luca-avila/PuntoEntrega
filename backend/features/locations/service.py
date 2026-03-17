import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from features.locations.models import Location
from features.locations.schemas import LocationCreate, LocationUpdate


async def list_locations_for_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
) -> list[Location]:
    result = await session.execute(
        select(Location)
        .where(Location.organization_id == organization_id)
        .order_by(Location.created_at.desc())
    )
    return list(result.scalars().all())


async def create_location_for_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
    payload: LocationCreate,
) -> Location:
    location = Location(
        organization_id=organization_id,
        name=payload.name,
        address=payload.address,
        contact_name=payload.contact_name,
        contact_phone=payload.contact_phone,
        contact_email=payload.contact_email,
        latitude=payload.latitude,
        longitude=payload.longitude,
        notes=payload.notes,
    )
    session.add(location)
    await session.commit()
    await session.refresh(location)
    return location


async def get_location_for_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
    location_id: uuid.UUID,
) -> Location:
    result = await session.execute(
        select(Location).where(
            Location.id == location_id,
            Location.organization_id == organization_id,
        )
    )
    location = result.scalar_one_or_none()
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ubicación no encontrada.",
        )
    return location


async def update_location_for_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
    location_id: uuid.UUID,
    payload: LocationUpdate,
) -> Location:
    location = await get_location_for_organization(
        session=session,
        organization_id=organization_id,
        location_id=location_id,
    )
    for field_name, field_value in payload.model_dump(exclude_unset=True).items():
        setattr(location, field_name, field_value)

    await session.commit()
    await session.refresh(location)
    return location

