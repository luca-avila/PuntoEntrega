import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from tests.test_locations import (
    build_location_payload,
    login_user,
    setup_authenticated_user_with_organization,
    setup_authenticated_user_without_organization,
    setup_member_user_in_organization,
)
from tests.test_products import build_product_payload


@pytest.fixture(autouse=True)
def mock_delivery_email_success(monkeypatch: pytest.MonkeyPatch):
    async def _success_sender(_delivery, summary_recipient_email=None):
        return None

    monkeypatch.setattr(
        "features.deliveries.emails.send_delivery_summary_email",
        _success_sender,
    )


async def setup_owner_and_member(
    client: AsyncClient,
    owner_email: str,
    member_email: str,
) -> tuple[str, str, uuid.UUID]:
    organization_payload = await setup_authenticated_user_with_organization(client, owner_email)
    organization_id = uuid.UUID(organization_payload["id"])

    logout_response = await client.post("/auth/jwt/logout")
    assert logout_response.status_code in (200, 204)

    await setup_member_user_in_organization(client, member_email, organization_id)

    logout_response = await client.post("/auth/jwt/logout")
    assert logout_response.status_code in (200, 204)

    return owner_email, member_email, organization_id


async def create_resources_as_owner(client: AsyncClient) -> tuple[dict[str, object], dict[str, object]]:
    location_response = await client.post("/locations", json=build_location_payload())
    assert location_response.status_code == 201

    product_response = await client.post("/products", json=build_product_payload())
    assert product_response.status_code == 201

    return location_response.json(), product_response.json()


class TestOwnerMemberAuthorization:
    async def test_owner_can_create_and_update_products_and_locations(self, client: AsyncClient):
        owner_email = "authz-owner-write@example.com"
        await setup_authenticated_user_with_organization(client, owner_email)

        product_create_response = await client.post("/products", json=build_product_payload())
        assert product_create_response.status_code == 201
        product_id = product_create_response.json()["id"]

        product_patch_response = await client.patch(
            f"/products/{product_id}",
            json={"is_active": False},
        )
        assert product_patch_response.status_code == 200

        location_create_response = await client.post("/locations", json=build_location_payload())
        assert location_create_response.status_code == 201
        location_id = location_create_response.json()["id"]

        location_patch_response = await client.patch(
            f"/locations/{location_id}",
            json={"notes": "Actualizado por owner."},
        )
        assert location_patch_response.status_code == 200

    async def test_member_cannot_create_or_update_products_and_locations(self, client: AsyncClient):
        owner_email, member_email, _organization_id = await setup_owner_and_member(
            client,
            owner_email="authz-owner-products-locations@example.com",
            member_email="authz-member-products-locations@example.com",
        )

        await login_user(client, owner_email)
        location, product = await create_resources_as_owner(client)

        logout_response = await client.post("/auth/jwt/logout")
        assert logout_response.status_code in (200, 204)

        await login_user(client, member_email)

        product_create_response = await client.post("/products", json=build_product_payload())
        product_patch_response = await client.patch(
            f"/products/{product['id']}",
            json={"is_active": False},
        )

        location_create_response = await client.post("/locations", json=build_location_payload())
        location_patch_response = await client.patch(
            f"/locations/{location['id']}",
            json={"notes": "Intento member"},
        )

        assert product_create_response.status_code == 403
        assert product_patch_response.status_code == 403
        assert location_create_response.status_code == 403
        assert location_patch_response.status_code == 403

    async def test_owner_can_create_deliveries(self, client: AsyncClient):
        owner_email = "authz-owner-deliveries@example.com"
        await setup_authenticated_user_with_organization(client, owner_email)

        location, product = await create_resources_as_owner(client)

        create_delivery_response = await client.post(
            "/deliveries",
            json={
                "location_id": location["id"],
                "delivered_at": datetime.now(UTC).isoformat(),
                "payment_method": "cash",
                "summary_recipient_email": "owner-deliveries@example.com",
                "items": [{"product_id": product["id"], "quantity": "1"}],
            },
        )

        assert create_delivery_response.status_code == 201

    async def test_member_cannot_create_deliveries(self, client: AsyncClient):
        owner_email, member_email, _organization_id = await setup_owner_and_member(
            client,
            owner_email="authz-owner-deliveries-member@example.com",
            member_email="authz-member-deliveries@example.com",
        )

        await login_user(client, owner_email)
        location, product = await create_resources_as_owner(client)

        logout_response = await client.post("/auth/jwt/logout")
        assert logout_response.status_code in (200, 204)

        await login_user(client, member_email)

        create_delivery_response = await client.post(
            "/deliveries",
            json={
                "location_id": location["id"],
                "delivered_at": datetime.now(UTC).isoformat(),
                "payment_method": "cash",
                "summary_recipient_email": "member-deliveries@example.com",
                "items": [{"product_id": product["id"], "quantity": "1"}],
            },
        )

        assert create_delivery_response.status_code == 403

    async def test_owner_and_member_have_scoped_read_access(self, client: AsyncClient):
        owner_email, member_email, _organization_id = await setup_owner_and_member(
            client,
            owner_email="authz-owner-read@example.com",
            member_email="authz-member-read@example.com",
        )

        await login_user(client, owner_email)
        location, product = await create_resources_as_owner(client)
        members_response = await client.get("/organization-members")
        assert members_response.status_code == 200
        members_payload = members_response.json()
        member_record = next((item for item in members_payload if item["email"] == member_email), None)
        assert member_record is not None
        member_location_id = member_record["location_id"]
        assert member_location_id is not None

        owner_delivery_response = await client.post(
            "/deliveries",
            json={
                "location_id": location["id"],
                "delivered_at": datetime.now(UTC).isoformat(),
                "payment_method": "cash",
                "summary_recipient_email": "read-resources@example.com",
                "items": [{"product_id": product["id"], "quantity": "1"}],
            },
        )
        assert owner_delivery_response.status_code == 201
        owner_delivery_id = owner_delivery_response.json()["id"]

        member_delivery_response = await client.post(
            "/deliveries",
            json={
                "location_id": member_location_id,
                "delivered_at": datetime.now(UTC).isoformat(),
                "payment_method": "cash",
                "summary_recipient_email": "read-resources-member-location@example.com",
                "items": [{"product_id": product["id"], "quantity": "2"}],
            },
        )
        assert member_delivery_response.status_code == 201
        member_delivery_id = member_delivery_response.json()["id"]

        logout_response = await client.post("/auth/jwt/logout")
        assert logout_response.status_code in (200, 204)

        await login_user(client, owner_email)
        owner_products_response = await client.get("/products")
        owner_product_response = await client.get(f"/products/{product['id']}")
        owner_locations_response = await client.get("/locations")
        owner_location_response = await client.get(f"/locations/{location['id']}")
        owner_deliveries_response = await client.get("/deliveries")
        owner_delivery_single_response = await client.get(f"/deliveries/{owner_delivery_id}")

        assert owner_products_response.status_code == 200
        assert owner_product_response.status_code == 200
        assert owner_locations_response.status_code == 200
        assert owner_location_response.status_code == 200
        assert owner_deliveries_response.status_code == 200
        assert owner_delivery_single_response.status_code == 200

        logout_response = await client.post("/auth/jwt/logout")
        assert logout_response.status_code in (200, 204)

        await login_user(client, member_email)
        member_products_response = await client.get("/products")
        member_product_response = await client.get(f"/products/{product['id']}")
        member_locations_response = await client.get("/locations")
        member_location_response = await client.get(f"/locations/{location['id']}")
        member_deliveries_response = await client.get("/deliveries")
        member_owner_delivery_response = await client.get(f"/deliveries/{owner_delivery_id}")
        member_own_delivery_response = await client.get(f"/deliveries/{member_delivery_id}")

        assert member_products_response.status_code == 200
        assert member_product_response.status_code == 200
        assert member_locations_response.status_code == 403
        assert member_location_response.status_code == 403
        assert member_deliveries_response.status_code == 200
        member_delivery_ids = {item["id"] for item in member_deliveries_response.json()}
        assert member_delivery_id in member_delivery_ids
        assert owner_delivery_id not in member_delivery_ids
        assert member_owner_delivery_response.status_code == 404
        assert member_own_delivery_response.status_code == 200

    async def test_user_without_organization_gets_403_in_organization_scoped_endpoints(
        self,
        client: AsyncClient,
    ):
        user_email = "authz-without-org@example.com"
        await setup_authenticated_user_without_organization(client, user_email)

        products_response = await client.get("/products")
        create_product_response = await client.post("/products", json=build_product_payload())
        create_delivery_response = await client.post(
            "/deliveries",
            json={
                "location_id": str(uuid.uuid4()),
                "delivered_at": datetime.now(UTC).isoformat(),
                "payment_method": "cash",
                "summary_recipient_email": "without-org@example.com",
                "items": [{"product_id": str(uuid.uuid4()), "quantity": "1"}],
            },
        )

        assert products_response.status_code == 403
        assert create_product_response.status_code == 403
        assert create_delivery_response.status_code == 403


class TestOrganizationMembersEndpoint:
    async def test_owner_can_list_organization_members(self, client: AsyncClient):
        owner_email, member_email, _organization_id = await setup_owner_and_member(
            client,
            owner_email="org-members-owner@example.com",
            member_email="org-members-member@example.com",
        )

        await login_user(client, owner_email)
        response = await client.get("/organization-members")

        assert response.status_code == 200
        payload = response.json()
        emails = {member["email"] for member in payload}
        assert owner_email in emails
        assert member_email in emails
        assert all(member["created_at"] is not None for member in payload)

    async def test_member_cannot_list_organization_members(self, client: AsyncClient):
        _owner_email, member_email, _organization_id = await setup_owner_and_member(
            client,
            owner_email="org-members-owner-forbidden@example.com",
            member_email="org-members-member-forbidden@example.com",
        )

        await login_user(client, member_email)
        response = await client.get("/organization-members")

        assert response.status_code == 403

    async def test_unauthenticated_cannot_list_organization_members(self, client: AsyncClient):
        response = await client.get("/organization-members")

        assert response.status_code == 401
