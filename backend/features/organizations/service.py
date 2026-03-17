import uuid
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_async_session
from features.auth.models import User
from features.auth.service import current_active_user
from features.deliveries.models import Delivery
from features.locations.models import Location
from features.organizations.models import Organization
from features.products.models import Product


async def get_current_organization_id(
    user: User = Depends(current_active_user),
) -> uuid.UUID:
    if user.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no está asignado a una organización.",
        )
    return user.organization_id


async def get_current_organization(
    organization_id: uuid.UUID = Depends(get_current_organization_id),
    session: AsyncSession = Depends(get_async_session),
) -> Organization:
    result = await session.execute(
        select(Organization).where(
            Organization.id == organization_id,
            Organization.is_active.is_(True),
        )
    )
    organization = result.scalar_one_or_none()
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La organización está inactiva o no existe.",
        )
    return organization


async def _resource_belongs_to_organization(
    session: AsyncSession,
    model: Any,
    resource_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> bool:
    result = await session.execute(
        select(model.id).where(
            model.id == resource_id,
            model.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def ensure_location_belongs_to_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
    location_id: uuid.UUID,
) -> None:
    belongs_to_organization = await _resource_belongs_to_organization(
        session,
        Location,
        location_id,
        organization_id,
    )
    if not belongs_to_organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ubicación no encontrada.")


async def ensure_product_belongs_to_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
    product_id: uuid.UUID,
) -> None:
    belongs_to_organization = await _resource_belongs_to_organization(
        session,
        Product,
        product_id,
        organization_id,
    )
    if not belongs_to_organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado.")


async def ensure_delivery_belongs_to_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
    delivery_id: uuid.UUID,
) -> None:
    belongs_to_organization = await _resource_belongs_to_organization(
        session,
        Delivery,
        delivery_id,
        organization_id,
    )
    if not belongs_to_organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrega no encontrada.")

