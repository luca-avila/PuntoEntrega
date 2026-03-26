import uuid
from typing import cast

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.sql.elements import ColumnElement

from core.db import async_session_maker
from features.auth.models import User
from features.organizations.models import Organization
from features.organizations.models import MembershipRole, OrganizationMembership

USER_PASSWORD = "StrongPass123!"


async def register_user(client: AsyncClient, email: str) -> None:
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": USER_PASSWORD},
    )
    assert response.status_code == 201


async def mark_user_verified(email: str) -> None:
    async with async_session_maker() as session:
        email_filter = cast(ColumnElement[bool], User.email == email)
        result = await session.execute(select(User).where(email_filter))
        user = result.scalar_one()
        user.is_verified = True
        await session.commit()


async def login_user(client: AsyncClient, email: str) -> None:
    response = await client.post(
        "/auth/jwt/login",
        data={"username": email, "password": USER_PASSWORD},
    )
    assert response.status_code in (200, 204)


async def setup_authenticated_user_without_organization(
    client: AsyncClient,
    email: str,
) -> None:
    await register_user(client, email)
    await mark_user_verified(email)
    await login_user(client, email)


class TestOrganizationsOnboarding:
    async def test_authenticated_user_without_organization_can_create_one(self, client: AsyncClient):
        user_email = "org-create@example.com"
        await setup_authenticated_user_without_organization(client, user_email)

        response = await client.post("/organizations", json={"name": "Org Principal"})

        assert response.status_code == 201
        payload = response.json()
        assert payload["name"] == "Org Principal"
        assert payload["slug"]
        assert payload["is_active"] is True

    async def test_create_organization_assigns_owner_and_user_membership(self, client: AsyncClient):
        user_email = "org-owner-assignment@example.com"
        await setup_authenticated_user_without_organization(client, user_email)

        response = await client.post("/organizations", json={"name": "Org de Owner"})
        assert response.status_code == 201
        organization_id = uuid.UUID(response.json()["id"])

        async with async_session_maker() as session:
            user_result = await session.execute(select(User).where(User.email == user_email))
            user = user_result.scalar_one()
            organization = await session.get(Organization, organization_id)
            membership_result = await session.execute(
                select(OrganizationMembership).where(
                    OrganizationMembership.organization_id == organization_id,
                    OrganizationMembership.user_id == user.id,
                    OrganizationMembership.role == MembershipRole.OWNER.value,
                )
            )
            owner_membership = membership_result.scalar_one_or_none()

        assert organization is not None
        assert owner_membership is not None

    async def test_user_with_organization_cannot_create_another(self, client: AsyncClient):
        user_email = "org-singleton@example.com"
        await setup_authenticated_user_without_organization(client, user_email)

        first_response = await client.post("/organizations", json={"name": "Org A"})
        second_response = await client.post("/organizations", json={"name": "Org B"})

        assert first_response.status_code == 201
        assert second_response.status_code == 409

    async def test_get_current_organization_returns_user_organization(self, client: AsyncClient):
        user_email = "org-current@example.com"
        await setup_authenticated_user_without_organization(client, user_email)

        create_response = await client.post("/organizations", json={"name": "Org Current"})
        assert create_response.status_code == 201
        created = create_response.json()

        response = await client.get("/organizations/current")

        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == created["id"]
        assert payload["name"] == "Org Current"
        assert payload["slug"] == created["slug"]

    async def test_get_current_organization_returns_403_without_organization(self, client: AsyncClient):
        user_email = "org-missing@example.com"
        await setup_authenticated_user_without_organization(client, user_email)

        response = await client.get("/organizations/current")

        assert response.status_code == 403

    async def test_organizations_endpoints_require_authentication(self, client: AsyncClient):
        create_response = await client.post("/organizations", json={"name": "Org Auth"})
        current_response = await client.get("/organizations/current")

        assert create_response.status_code == 401
        assert current_response.status_code == 401
