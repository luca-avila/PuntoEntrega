import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_async_session
from features.auth.models import User
from features.auth.service import current_active_user
from features.invitations.schemas import (
    OrganizationInvitationAcceptAuthenticated,
    OrganizationInvitationAcceptCreate,
    OrganizationInvitationAcceptInfoRead,
    OrganizationInvitationAcceptResult,
    OrganizationInvitationCreate,
    OrganizationInvitationRead,
)
from features.invitations.service import (
    accept_invitation_authenticated,
    accept_invitation_new_account,
    cancel_invitation,
    create_or_resend_invitation,
    get_accept_info,
    list_invitations_for_organization,
)
from features.organizations.service import OrganizationUserContext, require_organization_owner

router = APIRouter()


@router.post(
    "/organization-invitations",
    response_model=OrganizationInvitationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_organization_invitation(
    payload: OrganizationInvitationCreate,
    context: OrganizationUserContext = Depends(require_organization_owner),
    session: AsyncSession = Depends(get_async_session),
):
    return await create_or_resend_invitation(
        session=session,
        organization_id=context.organization.id,
        organization_name=context.organization.name,
        invited_by_user_id=context.user.id,
        invited_email=payload.email,
        invited_location_id=payload.location_id,
    )


@router.get(
    "/organization-invitations",
    response_model=list[OrganizationInvitationRead],
)
async def list_organization_invitations(
    context: OrganizationUserContext = Depends(require_organization_owner),
    session: AsyncSession = Depends(get_async_session),
):
    return await list_invitations_for_organization(
        session=session,
        organization_id=context.organization.id,
    )


@router.post(
    "/organization-invitations/{invitation_id}/cancel",
    response_model=OrganizationInvitationRead,
)
async def cancel_organization_invitation(
    invitation_id: uuid.UUID,
    context: OrganizationUserContext = Depends(require_organization_owner),
    session: AsyncSession = Depends(get_async_session),
):
    return await cancel_invitation(
        session=session,
        organization_id=context.organization.id,
        invitation_id=invitation_id,
    )


@router.get(
    "/organization-invitations/accept-info",
    response_model=OrganizationInvitationAcceptInfoRead,
)
async def get_organization_invitation_accept_info(
    token: str,
    session: AsyncSession = Depends(get_async_session),
):
    return await get_accept_info(session=session, token=token)


@router.post(
    "/organization-invitations/accept",
    response_model=OrganizationInvitationAcceptResult,
)
async def accept_organization_invitation_new_account(
    payload: OrganizationInvitationAcceptCreate,
    session: AsyncSession = Depends(get_async_session),
):
    user, invitation = await accept_invitation_new_account(
        session=session,
        token=payload.token,
        password=payload.password,
    )
    return OrganizationInvitationAcceptResult(
        invitation_id=invitation.id,
        organization_id=invitation.organization_id,
        user_id=user.id,
        invited_email=invitation.invited_email,
    )


@router.post(
    "/organization-invitations/accept-authenticated",
    response_model=OrganizationInvitationAcceptResult,
)
async def accept_organization_invitation_authenticated(
    payload: OrganizationInvitationAcceptAuthenticated,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    user, invitation = await accept_invitation_authenticated(
        session=session,
        token=payload.token,
        current_user_id=current_user.id,
        current_user_email=current_user.email,
    )
    return OrganizationInvitationAcceptResult(
        invitation_id=invitation.id,
        organization_id=invitation.organization_id,
        user_id=user.id,
        invited_email=invitation.invited_email,
    )
