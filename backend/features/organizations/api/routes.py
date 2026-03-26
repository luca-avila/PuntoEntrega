from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_async_session
from features.auth.models import User
from features.auth.service import current_active_user
from features.organizations.schemas import (
    OrganizationCreate,
    OrganizationMembershipCurrentRead,
    OrganizationMemberRead,
    OrganizationRead,
)
from features.organizations.service import (
    OrganizationUserContext,
    create_organization_for_user,
    get_current_membership_for_user,
    get_current_organization_for_user,
    list_members_for_organization,
    require_organization_owner,
)

router = APIRouter()


@router.post("/organizations", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await create_organization_for_user(
        session=session,
        user_id=current_user.id,
        organization_name=payload.name,
    )


@router.get("/organizations/current", response_model=OrganizationRead)
async def get_current_organization(
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await get_current_organization_for_user(
        session=session,
        user_id=current_user.id,
    )


@router.get(
    "/organization-memberships/current",
    response_model=OrganizationMembershipCurrentRead,
)
async def get_current_membership(
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    membership = await get_current_membership_for_user(
        session=session,
        user_id=current_user.id,
    )
    organization = membership.organization
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La organización está inactiva o no existe.",
        )

    return OrganizationMembershipCurrentRead(
        organization_id=membership.organization_id,
        organization_name=organization.name,
        role=membership.role,
        location_id=membership.location_id,
    )


@router.get("/organization-members", response_model=list[OrganizationMemberRead])
async def list_organization_members(
    context: OrganizationUserContext = Depends(require_organization_owner),
    session: AsyncSession = Depends(get_async_session),
):
    members = await list_members_for_organization(
        session=session,
        organization_id=context.organization.id,
    )
    return [
        OrganizationMemberRead(
            id=membership.user.id,
            email=membership.user.email,
            is_active=membership.user.is_active,
            is_verified=membership.user.is_verified,
            location_id=membership.location_id,
            created_at=getattr(membership.user, "created_at", None),
        )
        for membership in members
    ]
