import uuid
import re
from collections.abc import Iterable
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

ORGANIZATION_SLUG_MAX_LENGTH = 120


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        slug = "organization"
    return slug[:ORGANIZATION_SLUG_MAX_LENGTH]


async def _organization_slug_exists(session: AsyncSession, slug: str) -> bool:
    result = await session.execute(
        select(Organization.id).where(Organization.slug == slug).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _build_unique_organization_slug(session: AsyncSession, organization_name: str) -> str:
    base_slug = _slugify(organization_name)
    candidate = base_slug
    suffix = 2

    while await _organization_slug_exists(session, candidate):
        suffix_token = f"-{suffix}"
        max_base_length = ORGANIZATION_SLUG_MAX_LENGTH - len(suffix_token)
        truncated_base = base_slug[:max_base_length].rstrip("-")
        candidate = f"{truncated_base}{suffix_token}"
        suffix += 1

    return candidate


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


async def create_organization_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    organization_name: str,
) -> Organization:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )

    if user.organization_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario ya está asignado a una organización.",
        )

    organization_slug = await _build_unique_organization_slug(session, organization_name)
    organization = Organization(
        name=organization_name,
        slug=organization_slug,
        owner_user_id=user.id,
    )

    user.organization = organization

    try:
        session.add(organization)
        session.add(user)
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    await session.refresh(organization)
    return organization


async def get_current_organization_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> Organization:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )

    if user.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no está asignado a una organización.",
        )

    result = await session.execute(
        select(Organization).where(
            Organization.id == user.organization_id,
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
    await ensure_products_belong_to_organization(
        session=session,
        organization_id=organization_id,
        product_ids=[product_id],
    )


async def ensure_products_belong_to_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
    product_ids: Iterable[uuid.UUID],
) -> None:
    unique_product_ids = tuple(dict.fromkeys(product_ids))
    if not unique_product_ids:
        return

    result = await session.execute(
        select(Product.id).where(
            Product.organization_id == organization_id,
            Product.id.in_(unique_product_ids),
        )
    )
    found_product_ids = set(result.scalars().all())
    if len(found_product_ids) != len(unique_product_ids):
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
