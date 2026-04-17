import uuid
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.sql.elements import ColumnElement

from core.db import async_session_maker
from features.auth.models import User
from features.invitations.models import InvitationStatus, OrganizationInvitation
from features.notifications.outbox import (
    EVENT_INVITATION_EMAIL_REQUESTED,
    enqueue_notification_event as real_enqueue_notification_event,
)
from features.organizations.models import MembershipRole, OrganizationMembership
from tests.test_locations import (
    build_location_payload,
    assign_user_to_organization,
    login_user,
    setup_authenticated_user_with_organization,
    setup_authenticated_user_without_organization,
    setup_member_user_in_organization,
)


@pytest.fixture
def sent_invitation_emails(monkeypatch: pytest.MonkeyPatch):
    sent_items: list[dict[str, str]] = []

    async def _capture_enqueue(*args, **kwargs):
        if kwargs.get("event_type") == EVENT_INVITATION_EMAIL_REQUESTED:
            payload = kwargs["payload"]
            sent_items.append(
                {
                    "to_email": payload["to_email"],
                    "organization_name": payload["organization_name"],
                    "token": payload["token"],
                }
            )
        return await real_enqueue_notification_event(*args, **kwargs)

    monkeypatch.setattr(
        "features.invitations.service.enqueue_notification_event",
        _capture_enqueue,
    )

    return sent_items


async def logout(client: AsyncClient) -> None:
    response = await client.post("/auth/jwt/logout")
    assert response.status_code in (200, 204)


async def setup_owner_and_member(
    client: AsyncClient,
    owner_email: str,
    member_email: str,
) -> tuple[str, str, uuid.UUID]:
    organization_payload = await setup_authenticated_user_with_organization(client, owner_email)
    organization_id = uuid.UUID(organization_payload["id"])

    await logout(client)
    await setup_member_user_in_organization(client, member_email, organization_id)
    await logout(client)

    return owner_email, member_email, organization_id


async def create_location_for_current_owner(client: AsyncClient, *, name_suffix: str) -> uuid.UUID:
    payload = build_location_payload()
    payload["name"] = f"{payload['name']} {name_suffix}".strip()
    response = await client.post("/locations", json=payload)
    assert response.status_code == 201
    return uuid.UUID(response.json()["id"])


class TestOrganizationInvitations:
    async def test_owner_can_create_invitation(self, client: AsyncClient, sent_invitation_emails):
        owner_email = "inv-owner-create@example.com"
        await setup_authenticated_user_with_organization(client, owner_email)
        location_id = await create_location_for_current_owner(
            client,
            name_suffix="create-invitation",
        )

        response = await client.post(
            "/organization-invitations",
            json={
                "email": "INVITED.USER@example.com",
                "location_id": str(location_id),
            },
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["invited_email"] == "invited.user@example.com"
        assert payload["location_id"] == str(location_id)
        assert payload["status"] == InvitationStatus.PENDING.value
        assert sent_invitation_emails[0]["to_email"] == "invited.user@example.com"
        assert sent_invitation_emails[0]["token"]

    async def test_member_cannot_create_list_or_cancel_invitations(
        self,
        client: AsyncClient,
        sent_invitation_emails,
    ):
        owner_email, member_email, _organization_id = await setup_owner_and_member(
            client,
            owner_email="inv-owner-protected@example.com",
            member_email="inv-member-protected@example.com",
        )

        await login_user(client, owner_email)
        invitation_location_id = await create_location_for_current_owner(
            client,
            name_suffix="member-cannot-create",
        )
        invitation_response = await client.post(
            "/organization-invitations",
            json={
                "email": "invitee-protected@example.com",
                "location_id": str(invitation_location_id),
            },
        )
        assert invitation_response.status_code == 201
        invitation_id = invitation_response.json()["id"]

        await logout(client)
        await login_user(client, member_email)

        create_response = await client.post(
            "/organization-invitations",
            json={
                "email": "another@example.com",
                "location_id": str(invitation_location_id),
            },
        )
        list_response = await client.get("/organization-invitations")
        cancel_response = await client.post(f"/organization-invitations/{invitation_id}/cancel")

        assert create_response.status_code == 403
        assert list_response.status_code == 403
        assert cancel_response.status_code == 403

    async def test_unauthenticated_gets_401_on_owner_invitation_endpoints(self, client: AsyncClient):
        invitation_id = uuid.uuid4()

        create_response = await client.post(
            "/organization-invitations",
            json={
                "email": "unauth@example.com",
                "location_id": str(uuid.uuid4()),
            },
        )
        list_response = await client.get("/organization-invitations")
        cancel_response = await client.post(f"/organization-invitations/{invitation_id}/cancel")

        assert create_response.status_code == 401
        assert list_response.status_code == 401
        assert cancel_response.status_code == 401

    async def test_reuses_existing_pending_invitation_for_same_email_and_org(
        self,
        client: AsyncClient,
        sent_invitation_emails,
    ):
        owner_email = "inv-owner-reuse@example.com"
        organization_payload = await setup_authenticated_user_with_organization(client, owner_email)
        organization_id = uuid.UUID(organization_payload["id"])
        location_id = await create_location_for_current_owner(
            client,
            name_suffix="reuse-pending",
        )

        first_response = await client.post(
            "/organization-invitations",
            json={
                "email": "reuse@example.com",
                "location_id": str(location_id),
            },
        )
        second_response = await client.post(
            "/organization-invitations",
            json={
                "email": "reuse@example.com",
                "location_id": str(location_id),
            },
        )

        assert first_response.status_code == 201
        assert second_response.status_code == 201
        assert first_response.json()["id"] == second_response.json()["id"]
        assert len(sent_invitation_emails) == 2

        async with async_session_maker() as session:
            result = await session.execute(
                select(OrganizationInvitation).where(
                    OrganizationInvitation.organization_id == organization_id,
                    OrganizationInvitation.invited_email == "reuse@example.com",
                    OrganizationInvitation.status == InvitationStatus.PENDING,
                )
            )
            pending_invitations = list(result.scalars().all())

        assert len(pending_invitations) == 1

    async def test_rejects_inviting_user_from_another_organization(self, client: AsyncClient):
        owner_email = "inv-owner-another-org@example.com"
        await setup_authenticated_user_with_organization(client, owner_email)
        owner_location_id = await create_location_for_current_owner(
            client,
            name_suffix="another-org",
        )

        await logout(client)
        target_email = "existing-other-org@example.com"
        await setup_authenticated_user_with_organization(client, target_email)

        await logout(client)
        await login_user(client, owner_email)

        response = await client.post(
            "/organization-invitations",
            json={
                "email": target_email,
                "location_id": str(owner_location_id),
            },
        )

        assert response.status_code == 409

    async def test_rejects_inviting_user_already_in_same_organization(self, client: AsyncClient):
        owner_email, member_email, _organization_id = await setup_owner_and_member(
            client,
            owner_email="inv-owner-same-org@example.com",
            member_email="inv-member-same-org@example.com",
        )

        await login_user(client, owner_email)
        owner_location_id = await create_location_for_current_owner(
            client,
            name_suffix="same-org",
        )

        response = await client.post(
            "/organization-invitations",
            json={
                "email": member_email,
                "location_id": str(owner_location_id),
            },
        )

        assert response.status_code == 409

    async def test_accept_info_reports_valid_for_active_token(self, client: AsyncClient, sent_invitation_emails):
        owner_email = "inv-owner-accept-info-valid@example.com"
        await setup_authenticated_user_with_organization(client, owner_email)
        location_id = await create_location_for_current_owner(
            client,
            name_suffix="accept-info-valid",
        )

        create_response = await client.post(
            "/organization-invitations",
            json={
                "email": "accept-info-valid@example.com",
                "location_id": str(location_id),
            },
        )
        assert create_response.status_code == 201
        token = sent_invitation_emails[0]["token"]

        response = await client.get(
            "/organization-invitations/accept-info",
            params={"token": token},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["is_valid"] is True
        assert payload["status"] == "valid"
        assert payload["invited_email"] == "accept-info-valid@example.com"
        assert payload["location_id"] == str(location_id)
        assert payload["invited_user_exists"] is False

    async def test_accept_info_reports_invalid_expired_cancelled_and_accepted_states(
        self,
        client: AsyncClient,
        sent_invitation_emails,
    ):
        owner_email = "inv-owner-accept-info-states@example.com"
        await setup_authenticated_user_with_organization(client, owner_email)
        invitation_location_id = await create_location_for_current_owner(
            client,
            name_suffix="accept-info-states",
        )

        invalid_response = await client.get(
            "/organization-invitations/accept-info",
            params={"token": "token-no-existe"},
        )
        assert invalid_response.status_code == 200
        assert invalid_response.json()["status"] == "invalid"

        expired_email = "expired-state@example.com"
        create_expired_response = await client.post(
            "/organization-invitations",
            json={
                "email": expired_email,
                "location_id": str(invitation_location_id),
            },
        )
        assert create_expired_response.status_code == 201
        expired_token = sent_invitation_emails[-1]["token"]

        async with async_session_maker() as session:
            result = await session.execute(
                select(OrganizationInvitation).where(
                    OrganizationInvitation.invited_email == expired_email
                )
            )
            invitation = result.scalar_one()
            invitation.expires_at = datetime.now(UTC) - timedelta(minutes=1)
            await session.commit()

        expired_response = await client.get(
            "/organization-invitations/accept-info",
            params={"token": expired_token},
        )
        assert expired_response.status_code == 200
        assert expired_response.json()["status"] == "expired"

        cancelled_email = "cancelled-state@example.com"
        create_cancelled_response = await client.post(
            "/organization-invitations",
            json={
                "email": cancelled_email,
                "location_id": str(invitation_location_id),
            },
        )
        assert create_cancelled_response.status_code == 201
        cancelled_invitation_id = create_cancelled_response.json()["id"]
        cancelled_token = sent_invitation_emails[-1]["token"]

        cancel_response = await client.post(
            f"/organization-invitations/{cancelled_invitation_id}/cancel"
        )
        assert cancel_response.status_code == 200

        cancelled_state_response = await client.get(
            "/organization-invitations/accept-info",
            params={"token": cancelled_token},
        )
        assert cancelled_state_response.status_code == 200
        assert cancelled_state_response.json()["status"] == "cancelled"

        accepted_email = "accepted-state@example.com"
        create_accepted_response = await client.post(
            "/organization-invitations",
            json={
                "email": accepted_email,
                "location_id": str(invitation_location_id),
            },
        )
        assert create_accepted_response.status_code == 201
        accepted_token = sent_invitation_emails[-1]["token"]

        accept_response = await client.post(
            "/organization-invitations/accept",
            json={
                "token": accepted_token,
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
        )
        assert accept_response.status_code == 200

        accepted_state_response = await client.get(
            "/organization-invitations/accept-info",
            params={"token": accepted_token},
        )
        assert accepted_state_response.status_code == 200
        accepted_payload = accepted_state_response.json()
        assert accepted_payload["status"] == "accepted"
        assert accepted_payload["organization_name"] == "Organización inv-owner-accept-info-states"
        assert accepted_payload["invited_email"] == accepted_email
        assert accepted_payload["invited_user_exists"] is True

    async def test_accept_invitation_new_account_creates_user_and_marks_invitation_accepted(
        self,
        client: AsyncClient,
        sent_invitation_emails,
    ):
        owner_email = "inv-owner-accept-new@example.com"
        invited_email = "accept-new-user@example.com"

        await setup_authenticated_user_with_organization(client, owner_email)
        location_id = await create_location_for_current_owner(
            client,
            name_suffix="accept-new-account",
        )

        create_response = await client.post(
            "/organization-invitations",
            json={
                "email": invited_email,
                "location_id": str(location_id),
            },
        )
        assert create_response.status_code == 201
        invitation_id = create_response.json()["id"]
        organization_id = create_response.json()["organization_id"]
        token = sent_invitation_emails[0]["token"]

        accept_response = await client.post(
            "/organization-invitations/accept",
            json={
                "token": token,
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
        )

        assert accept_response.status_code == 200
        payload = accept_response.json()
        assert payload["invitation_id"] == invitation_id
        assert payload["organization_id"] == organization_id

        async with async_session_maker() as session:
            user_result = await session.execute(
                select(User).where(User.email == invited_email)
            )
            invited_user = user_result.scalar_one()
            invitation = await session.get(OrganizationInvitation, uuid.UUID(invitation_id))
            membership_result = await session.execute(
                select(OrganizationMembership).where(
                    OrganizationMembership.user_id == invited_user.id,
                    OrganizationMembership.organization_id == uuid.UUID(organization_id),
                )
            )
            membership = membership_result.scalar_one_or_none()

        assert membership is not None
        assert membership.role == MembershipRole.MEMBER
        assert membership.location_id == location_id
        assert invited_user.is_verified is True
        assert invitation is not None
        assert invitation.status == InvitationStatus.ACCEPTED
        assert invitation.accepted_at is not None

    async def test_accept_invitation_authenticated_requires_matching_email_and_user_without_organization(
        self,
        client: AsyncClient,
        sent_invitation_emails,
    ):
        owner_email = "inv-owner-authenticated-rules@example.com"
        invited_email = "invited-authenticated@example.com"

        organization_payload = await setup_authenticated_user_with_organization(client, owner_email)
        organization_id = uuid.UUID(organization_payload["id"])
        location_id = await create_location_for_current_owner(
            client,
            name_suffix="auth-rules",
        )

        create_response = await client.post(
            "/organization-invitations",
            json={
                "email": invited_email,
                "location_id": str(location_id),
            },
        )
        assert create_response.status_code == 201
        token = sent_invitation_emails[0]["token"]

        await logout(client)
        await setup_authenticated_user_without_organization(client, "another-user@example.com")

        mismatch_response = await client.post(
            "/organization-invitations/accept-authenticated",
            json={"token": token},
        )
        assert mismatch_response.status_code == 409
        assert (
            mismatch_response.json()["detail"]
            == "El email autenticado no coincide con la invitación. Cerrá sesión y volvé a abrir esta invitación para continuar con el email invitado (podés ingresar con una cuenta existente o crear una nueva)."
        )

        await logout(client)
        await setup_authenticated_user_without_organization(client, invited_email)
        await assign_user_to_organization(invited_email, organization_id)

        already_in_org_response = await client.post(
            "/organization-invitations/accept-authenticated",
            json={"token": token},
        )
        assert already_in_org_response.status_code == 409

    async def test_accept_invitation_authenticated_assigns_existing_user_without_org(
        self,
        client: AsyncClient,
        sent_invitation_emails,
    ):
        owner_email = "inv-owner-authenticated-success@example.com"
        invited_email = "invited-auth-success@example.com"

        organization_payload = await setup_authenticated_user_with_organization(client, owner_email)
        organization_id = uuid.UUID(organization_payload["id"])
        location_id = await create_location_for_current_owner(
            client,
            name_suffix="auth-success",
        )

        create_response = await client.post(
            "/organization-invitations",
            json={
                "email": invited_email,
                "location_id": str(location_id),
            },
        )
        assert create_response.status_code == 201
        invitation_id = create_response.json()["id"]
        token = sent_invitation_emails[0]["token"]

        await logout(client)
        await setup_authenticated_user_without_organization(client, invited_email)

        accept_response = await client.post(
            "/organization-invitations/accept-authenticated",
            json={"token": token},
        )

        assert accept_response.status_code == 200
        payload = accept_response.json()
        assert payload["invitation_id"] == invitation_id

        async with async_session_maker() as session:
            email_filter = cast(ColumnElement[bool], User.email == invited_email)
            user_result = await session.execute(select(User).where(email_filter))
            invited_user = user_result.scalar_one()
            invitation = await session.get(OrganizationInvitation, uuid.UUID(invitation_id))
            membership_result = await session.execute(
                select(OrganizationMembership).where(
                    OrganizationMembership.user_id == invited_user.id,
                    OrganizationMembership.organization_id == organization_id,
                )
            )
            membership = membership_result.scalar_one_or_none()

        assert membership is not None
        assert membership.role == MembershipRole.MEMBER
        assert membership.location_id == location_id
        assert invitation is not None
        assert invitation.status == InvitationStatus.ACCEPTED
        assert invitation.accepted_at is not None

    async def test_token_cannot_be_reused_after_acceptance(
        self,
        client: AsyncClient,
        sent_invitation_emails,
    ):
        owner_email = "inv-owner-token-reuse@example.com"
        invited_email = "token-reuse@example.com"

        await setup_authenticated_user_with_organization(client, owner_email)
        location_id = await create_location_for_current_owner(
            client,
            name_suffix="token-reuse",
        )

        create_response = await client.post(
            "/organization-invitations",
            json={
                "email": invited_email,
                "location_id": str(location_id),
            },
        )
        assert create_response.status_code == 201
        token = sent_invitation_emails[0]["token"]

        first_accept_response = await client.post(
            "/organization-invitations/accept",
            json={
                "token": token,
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
        )
        second_accept_response = await client.post(
            "/organization-invitations/accept",
            json={
                "token": token,
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
        )

        assert first_accept_response.status_code == 200
        assert second_accept_response.status_code == 400
