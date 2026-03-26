import re
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy import asc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.db import get_async_session
from features.auth.models import User
from features.auth.service import current_active_user
from features.deliveries.models import Delivery
from features.locations.models import Location
from features.organizations.models import MembershipRole, Organization, OrganizationMembership
from features.products.models import Product

ORGANIZATION_SLUG_MAX_LENGTH = 120


@dataclass(frozen=True)
class OrganizationUserContext:
    user: User
    membership: OrganizationMembership
    organization: Organization


def is_organization_owner(context: OrganizationUserContext) -> bool:
    return context.membership.role == MembershipRole.OWNER


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


async def _get_active_memberships_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[OrganizationMembership]:
    result = await session.execute(
        select(OrganizationMembership)
        .join(
            Organization,
            Organization.id == OrganizationMembership.organization_id,
        )
        .where(
            OrganizationMembership.user_id == user_id,
            Organization.is_active.is_(True),
        )
        .options(selectinload(OrganizationMembership.organization))
        .order_by(OrganizationMembership.created_at.asc())
    )
    return list(result.scalars().all())


async def get_current_user_with_optional_organization(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> OrganizationUserContext | None:
    memberships = await _get_active_memberships_for_user(session, user.id)
    if not memberships:
        return None

    if len(memberships) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "El usuario pertenece a múltiples organizaciones activas. "
                "La selección de organización no está soportada todavía."
            ),
        )

    membership = memberships[0]
    organization = membership.organization
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La organización está inactiva o no existe.",
        )

    return OrganizationUserContext(user=user, membership=membership, organization=organization)


async def get_current_user_with_organization(
    context: OrganizationUserContext | None = Depends(get_current_user_with_optional_organization),
) -> OrganizationUserContext:
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no está asignado a una organización.",
        )
    return context


async def require_organization_owner(
    context: OrganizationUserContext = Depends(get_current_user_with_organization),
) -> OrganizationUserContext:
    if not is_organization_owner(context):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el owner de la organización puede realizar esta acción.",
        )
    return context


async def require_organization_member(
    context: OrganizationUserContext = Depends(get_current_user_with_organization),
) -> OrganizationUserContext:
    if is_organization_owner(context):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta acción solo está permitida para miembros de la organización.",
        )
    return context


async def require_organization_user(
    context: OrganizationUserContext = Depends(get_current_user_with_organization),
) -> OrganizationUserContext:
    return context


async def get_current_organization_id(
    context: OrganizationUserContext = Depends(require_organization_user),
) -> uuid.UUID:
    return context.organization.id


async def get_current_organization(
    context: OrganizationUserContext = Depends(require_organization_user),
) -> Organization:
    return context.organization


async def get_member_assigned_location_id(
    session: AsyncSession,
    context: OrganizationUserContext,
) -> uuid.UUID | None:
    if is_organization_owner(context):
        return None

    location_id = context.membership.location_id
    if location_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El miembro no tiene una ubicación asignada.",
        )

    belongs_to_organization = await _resource_belongs_to_organization(
        session,
        Location,
        location_id,
        context.organization.id,
    )
    if not belongs_to_organization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La ubicación asignada no pertenece a la organización del miembro.",
        )

    return location_id


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

    existing_membership_result = await session.execute(
        select(OrganizationMembership.id)
        .where(OrganizationMembership.user_id == user.id)
        .limit(1)
    )
    if existing_membership_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario ya está asignado a una organización.",
        )

    organization_slug = await _build_unique_organization_slug(session, organization_name)
    organization = Organization(
        name=organization_name,
        slug=organization_slug,
    )

    membership = OrganizationMembership(
        user_id=user.id,
        organization=organization,
        role=MembershipRole.OWNER,
        location_id=None,
    )

    try:
        session.add(organization)
        session.add(membership)
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
    memberships = await _get_active_memberships_for_user(session, user_id)
    if not memberships:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no está asignado a una organización.",
        )

    if len(memberships) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "El usuario pertenece a múltiples organizaciones activas. "
                "La selección de organización no está soportada todavía."
            ),
        )

    organization = memberships[0].organization
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La organización está inactiva o no existe.",
        )
    return organization


async def get_current_membership_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> OrganizationMembership:
    memberships = await _get_active_memberships_for_user(session, user_id)
    if not memberships:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no está asignado a una organización.",
        )

    if len(memberships) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "El usuario pertenece a múltiples organizaciones activas. "
                "La selección de organización no está soportada todavía."
            ),
        )

    return memberships[0]


async def list_members_for_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
) -> list[OrganizationMembership]:
    result = await session.execute(
        select(OrganizationMembership)
        .join(User, User.id == OrganizationMembership.user_id)
        .where(OrganizationMembership.organization_id == organization_id)
        .options(selectinload(OrganizationMembership.user))
        .order_by(asc(User.email))
    )
    return list(result.scalars().all())


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
