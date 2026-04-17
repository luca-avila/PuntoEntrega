import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fastapi import HTTPException, status
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.config import settings
from features.auth.models import User
from features.auth.service import UserManager
from features.invitations.models import InvitationStatus, OrganizationInvitation
from features.notifications.outbox import (
    EVENT_INVITATION_EMAIL_REQUESTED,
    enqueue_notification_event,
)
from features.organizations.models import MembershipRole, OrganizationMembership
from features.organizations.service import ensure_location_belongs_to_organization
from features.invitations.schemas import (
    InvitationAcceptInfoStatus,
    OrganizationInvitationAcceptInfoRead,
)

def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _generate_invitation_token() -> str:
    return secrets.token_urlsafe(32)


def _hash_invitation_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _build_invitation_expiration() -> datetime:
    return datetime.now(UTC) + timedelta(hours=settings.INVITATION_EXPIRATION_HOURS)


def _is_invitation_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        return expires_at <= datetime.now(UTC).replace(tzinfo=None)
    return expires_at <= datetime.now(UTC)


async def _find_user_by_email(session: AsyncSession, email: str) -> User | None:
    normalized_email = _normalize_email(email)
    result = await session.execute(
        select(User).where(func.lower(User.email) == normalized_email)
    )
    return result.scalar_one_or_none()


async def _list_memberships_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[OrganizationMembership]:
    result = await session.execute(
        select(OrganizationMembership)
        .where(OrganizationMembership.user_id == user_id)
        .order_by(OrganizationMembership.created_at.asc())
    )
    return list(result.scalars().all())


async def _get_pending_invitation_for_email(
    session: AsyncSession,
    organization_id: uuid.UUID,
    invited_email: str,
) -> OrganizationInvitation | None:
    result = await session.execute(
        select(OrganizationInvitation)
        .where(
            OrganizationInvitation.organization_id == organization_id,
            OrganizationInvitation.invited_email == invited_email,
            OrganizationInvitation.status == InvitationStatus.PENDING,
        )
        .order_by(OrganizationInvitation.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _build_invalid_accept_info(
    status_value: InvitationAcceptInfoStatus,
    invitation: OrganizationInvitation | None = None,
    invited_user_exists: bool | None = None,
) -> OrganizationInvitationAcceptInfoRead:
    return OrganizationInvitationAcceptInfoRead(
        status=status_value,
        is_valid=False,
        invited_email=invitation.invited_email if invitation is not None else None,
        organization_id=invitation.organization_id if invitation is not None else None,
        organization_name=invitation.organization.name if invitation is not None and invitation.organization else None,
        location_id=invitation.location_id if invitation is not None else None,
        expires_at=invitation.expires_at if invitation is not None else None,
        invited_user_exists=invited_user_exists,
    )


async def _expire_if_needed(
    session: AsyncSession,
    invitation: OrganizationInvitation,
) -> None:
    if (
        invitation.status == InvitationStatus.PENDING
        and _is_invitation_expired(invitation.expires_at)
    ):
        invitation.status = InvitationStatus.EXPIRED
        await session.commit()
        await session.refresh(invitation)


async def _get_invitation_by_token(
    session: AsyncSession,
    token: str,
) -> OrganizationInvitation | None:
    token_hash = _hash_invitation_token(token)
    result = await session.execute(
        select(OrganizationInvitation)
        .where(OrganizationInvitation.token_hash == token_hash)
        .options(selectinload(OrganizationInvitation.organization))
    )
    return result.scalar_one_or_none()


def _token_error_for_status(invitation_status: InvitationStatus | None) -> HTTPException:
    if invitation_status == InvitationStatus.EXPIRED:
        detail = "La invitación está expirada."
    elif invitation_status == InvitationStatus.CANCELLED:
        detail = "La invitación fue cancelada."
    elif invitation_status == InvitationStatus.ACCEPTED:
        detail = "La invitación ya fue aceptada."
    else:
        detail = "La invitación es inválida."

    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail,
    )


async def _get_invitation_ready_for_accept(
    session: AsyncSession,
    token: str,
) -> OrganizationInvitation:
    invitation = await _get_invitation_by_token(session, token)
    if invitation is None:
        raise _token_error_for_status(None)

    await _expire_if_needed(session, invitation)

    if invitation.status != InvitationStatus.PENDING:
        raise _token_error_for_status(invitation.status)

    return invitation


async def create_or_resend_invitation(
    session: AsyncSession,
    organization_id: uuid.UUID,
    organization_name: str,
    invited_by_user_id: uuid.UUID,
    invited_email: str,
    invited_location_id: uuid.UUID,
) -> OrganizationInvitation:
    normalized_email = _normalize_email(invited_email)
    await ensure_location_belongs_to_organization(
        session=session,
        organization_id=organization_id,
        location_id=invited_location_id,
    )
    existing_user = await _find_user_by_email(session, normalized_email)

    if existing_user is not None:
        existing_memberships = await _list_memberships_for_user(session, existing_user.id)
        if existing_memberships:
            if any(membership.organization_id == organization_id for membership in existing_memberships):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El usuario ya pertenece a esta organización.",
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El usuario ya pertenece a otra organización.",
            )

    invitation = await _get_pending_invitation_for_email(
        session=session,
        organization_id=organization_id,
        invited_email=normalized_email,
    )

    raw_token = _generate_invitation_token()
    invitation_expiration = _build_invitation_expiration()

    if invitation is None:
        invitation = OrganizationInvitation(
            organization_id=organization_id,
            invited_email=normalized_email,
            invited_by_user_id=invited_by_user_id,
            location_id=invited_location_id,
            token_hash=_hash_invitation_token(raw_token),
            status=InvitationStatus.PENDING,
            expires_at=invitation_expiration,
        )
        session.add(invitation)
    else:
        invitation.invited_by_user_id = invited_by_user_id
        invitation.location_id = invited_location_id
        invitation.token_hash = _hash_invitation_token(raw_token)
        invitation.expires_at = invitation_expiration
        invitation.status = InvitationStatus.PENDING
        invitation.accepted_at = None

    await session.flush()
    await enqueue_notification_event(
        session,
        event_type=EVENT_INVITATION_EMAIL_REQUESTED,
        aggregate_type="organization_invitation",
        aggregate_id=invitation.id,
        organization_id=organization_id,
        payload={
            "invitation_id": str(invitation.id),
            "to_email": normalized_email,
            "organization_name": organization_name,
            "token": raw_token,
        },
        deduplication_key=(
            f"organization_invitation:{invitation.id}:"
            f"{_hash_invitation_token(raw_token)}"
        ),
    )

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    await session.refresh(invitation)

    return invitation


async def list_invitations_for_organization(
    session: AsyncSession,
    organization_id: uuid.UUID,
) -> list[OrganizationInvitation]:
    result = await session.execute(
        select(OrganizationInvitation)
        .where(OrganizationInvitation.organization_id == organization_id)
        .order_by(OrganizationInvitation.created_at.desc())
    )
    return list(result.scalars().all())


async def cancel_invitation(
    session: AsyncSession,
    organization_id: uuid.UUID,
    invitation_id: uuid.UUID,
) -> OrganizationInvitation:
    result = await session.execute(
        select(OrganizationInvitation).where(
            OrganizationInvitation.id == invitation_id,
            OrganizationInvitation.organization_id == organization_id,
        )
    )
    invitation = result.scalar_one_or_none()
    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitación no encontrada.",
        )

    await _expire_if_needed(session, invitation)

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo podés cancelar invitaciones pendientes.",
        )

    invitation.status = InvitationStatus.CANCELLED

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    await session.refresh(invitation)
    return invitation


async def get_accept_info(
    session: AsyncSession,
    token: str,
) -> OrganizationInvitationAcceptInfoRead:
    invitation = await _get_invitation_by_token(session, token)
    if invitation is None:
        return _build_invalid_accept_info(InvitationAcceptInfoStatus.INVALID)

    await _expire_if_needed(session, invitation)
    invited_user = await _find_user_by_email(session, invitation.invited_email)
    invited_user_exists = invited_user is not None

    if invitation.status == InvitationStatus.PENDING:
        return OrganizationInvitationAcceptInfoRead(
            status=InvitationAcceptInfoStatus.VALID,
            is_valid=True,
            invited_email=invitation.invited_email,
            organization_id=invitation.organization_id,
            organization_name=invitation.organization.name if invitation.organization else None,
            location_id=invitation.location_id,
            invited_user_exists=invited_user_exists,
            expires_at=invitation.expires_at,
        )

    if invitation.status == InvitationStatus.EXPIRED:
        return _build_invalid_accept_info(
            InvitationAcceptInfoStatus.EXPIRED,
            invitation=invitation,
            invited_user_exists=invited_user_exists,
        )
    if invitation.status == InvitationStatus.CANCELLED:
        return _build_invalid_accept_info(
            InvitationAcceptInfoStatus.CANCELLED,
            invitation=invitation,
            invited_user_exists=invited_user_exists,
        )
    if invitation.status == InvitationStatus.ACCEPTED:
        return _build_invalid_accept_info(
            InvitationAcceptInfoStatus.ACCEPTED,
            invitation=invitation,
            invited_user_exists=invited_user_exists,
        )

    return _build_invalid_accept_info(InvitationAcceptInfoStatus.INVALID)


async def _hash_password_for_invited_email(
    session: AsyncSession,
    invited_email: str,
    password: str,
) -> str:
    user_db = SQLAlchemyUserDatabase(session, User)
    user_manager = UserManager(user_db)
    await user_manager.validate_password(
        password,
        SimpleNamespace(email=invited_email),
    )
    return user_manager.password_helper.hash(password)


async def accept_invitation_new_account(
    session: AsyncSession,
    token: str,
    password: str,
) -> tuple[User, OrganizationInvitation]:
    invitation = await _get_invitation_ready_for_accept(session, token)
    if invitation.location_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La invitación no tiene ubicación asignada. Solicitá una nueva invitación.",
        )

    existing_user = await _find_user_by_email(session, invitation.invited_email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese email. Iniciá sesión para aceptar la invitación.",
        )

    hashed_password = await _hash_password_for_invited_email(
        session=session,
        invited_email=invitation.invited_email,
        password=password,
    )

    user = User(
        email=invitation.invited_email,
        hashed_password=hashed_password,
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )
    membership = OrganizationMembership(
        user=user,
        organization_id=invitation.organization_id,
        role=MembershipRole.MEMBER,
        location_id=invitation.location_id,
    )

    invitation.status = InvitationStatus.ACCEPTED
    invitation.accepted_at = datetime.now(UTC)

    try:
        session.add(user)
        session.add(membership)
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    await session.refresh(user)
    await session.refresh(invitation)
    return user, invitation


async def accept_invitation_authenticated(
    session: AsyncSession,
    token: str,
    current_user_id: uuid.UUID,
    current_user_email: str,
) -> tuple[User, OrganizationInvitation]:
    invitation = await _get_invitation_ready_for_accept(session, token)
    if invitation.location_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La invitación no tiene ubicación asignada. Solicitá una nueva invitación.",
        )

    normalized_current_user_email = _normalize_email(current_user_email)
    if normalized_current_user_email != invitation.invited_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "El email autenticado no coincide con la invitación. "
                "Cerrá sesión y volvé a abrir esta invitación para continuar con el email invitado "
                "(podés ingresar con una cuenta existente o crear una nueva)."
            ),
        )

    user = await session.get(User, current_user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )

    existing_memberships = await _list_memberships_for_user(session, user.id)
    if existing_memberships:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario ya pertenece a una organización.",
        )

    user.is_verified = True
    membership = OrganizationMembership(
        user_id=user.id,
        organization_id=invitation.organization_id,
        role=MembershipRole.MEMBER,
        location_id=invitation.location_id,
    )
    invitation.status = InvitationStatus.ACCEPTED
    invitation.accepted_at = datetime.now(UTC)

    try:
        session.add(membership)
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    await session.refresh(user)
    await session.refresh(invitation)
    return user, invitation
