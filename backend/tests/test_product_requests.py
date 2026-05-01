import asyncio
import uuid
from typing import cast

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.sql.elements import ColumnElement

from core.db import async_session_maker
from features.auth.models import User
from features.notifications.models import NotificationOutboxEvent, NotificationOutboxStatus
from features.notifications.outbox import EVENT_PRODUCT_REQUEST_OWNER_NOTIFICATION_REQUESTED
from features.notifications.worker import process_pending_events
from features.organizations.models import OrganizationMembership
from features.product_requests.models import ProductRequestEmailStatus
from tests.test_locations import (
    build_location_payload,
    login_user,
    setup_authenticated_user_with_organization,
    setup_member_user_in_organization,
)
from tests.test_products import build_product_payload


@pytest.fixture(autouse=True)
def mock_product_request_email_success(monkeypatch: pytest.MonkeyPatch):
    async def _success_sender(**_kwargs):
        return None

    monkeypatch.setattr(
        "features.product_requests.emails.send_product_request_email",
        _success_sender,
    )


async def logout(client: AsyncClient) -> None:
    response = await client.post("/auth/jwt/logout")
    assert response.status_code in (200, 204)


async def setup_owner_and_member(
    client: AsyncClient,
    owner_email: str,
    member_email: str,
) -> tuple[str, str, uuid.UUID, uuid.UUID]:
    organization_payload = await setup_authenticated_user_with_organization(client, owner_email)
    organization_id = uuid.UUID(organization_payload["id"])
    product_payload = build_product_payload()
    owner_local_part = owner_email.split("@", maxsplit=1)[0]
    product_payload["name"] = f"Producto {owner_local_part}"
    create_product_response = await client.post("/products", json=product_payload)
    assert create_product_response.status_code == 201
    product_id = uuid.UUID(create_product_response.json()["id"])

    await logout(client)
    await setup_member_user_in_organization(client, member_email, organization_id)
    await logout(client)

    return owner_email, member_email, organization_id, product_id


async def set_user_verified(email: str, is_verified: bool) -> None:
    async with async_session_maker() as session:
        email_filter = cast(ColumnElement[bool], User.email == email)
        result = await session.execute(select(User).where(email_filter))
        user = result.scalar_one()
        user.is_verified = is_verified
        await session.commit()


async def get_user_assigned_location_id(email: str) -> uuid.UUID:
    async with async_session_maker() as session:
        email_filter = cast(ColumnElement[bool], User.email == email)
        result = await session.execute(
            select(OrganizationMembership.location_id)
            .join(User, OrganizationMembership.user_id == User.id)
            .where(email_filter)
            .limit(1)
        )
        location_id = result.scalar_one_or_none()
        assert location_id is not None
        return location_id


async def wait_for_product_request_status_in_db(
    product_request_id: uuid.UUID,
    expected_status: ProductRequestEmailStatus,
    *,
    attempts: int = 30,
    delay_seconds: float = 0.05,
) -> dict[str, object]:
    for _ in range(attempts):
        await process_pending_events()
        async with async_session_maker() as session:
            result = await session.execute(
                select(NotificationOutboxEvent).where(
                    NotificationOutboxEvent.event_type
                    == EVENT_PRODUCT_REQUEST_OWNER_NOTIFICATION_REQUESTED,
                    NotificationOutboxEvent.aggregate_id == product_request_id,
                )
            )
            event = result.scalar_one_or_none()
            if event is None:
                continue

            if event.status == NotificationOutboxStatus.PROCESSED:
                current_status = ProductRequestEmailStatus.SENT
                current_attempts = event.attempts
                current_last_error = None
                current_sent_at = event.processed_at
            elif event.status == NotificationOutboxStatus.FAILED:
                current_status = ProductRequestEmailStatus.FAILED
                current_attempts = event.attempts
                current_last_error = event.last_error
                current_sent_at = None
            else:
                current_status = ProductRequestEmailStatus.PENDING
                current_attempts = 0
                current_last_error = None
                current_sent_at = None

            if current_status == expected_status:
                return {
                    "id": str(product_request_id),
                    "email_status": current_status.value,
                    "email_attempts": current_attempts,
                    "email_last_error": current_last_error,
                    "email_sent_at": current_sent_at,
                }
        await asyncio.sleep(delay_seconds)

    raise AssertionError(
        f"Product request {product_request_id} did not reach status {expected_status.value}."
    )


class TestProductRequestsAuth:
    async def test_product_requests_endpoints_require_authentication(self, client: AsyncClient):
        list_response = await client.get("/product-requests")
        create_response = await client.post(
            "/product-requests",
            json={
                "subject": "Necesitamos un producto",
                "message": "Necesitamos incorporar este producto al catalogo.",
                "items": [{"product_id": str(uuid.uuid4()), "quantity": "1"}],
            },
        )

        assert list_response.status_code == 401
        assert create_response.status_code == 401


class TestProductRequestsPermissions:
    async def test_member_can_create_product_request(self, client: AsyncClient):
        owner_email, member_email, organization_id, product_id = await setup_owner_and_member(
            client,
            owner_email="pr-owner-create@example.com",
            member_email="pr-member-create@example.com",
        )

        await login_user(client, member_email)
        response = await client.post(
            "/product-requests",
            json={
                "subject": "Nuevo producto para stock",
                "message": "Necesitamos sumar este producto para la campaña de abril.",
                "items": [{"product_id": str(product_id), "quantity": "3"}],
            },
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["organization_id"] == str(organization_id)
        assert payload["subject"] == "Nuevo producto para stock"
        assert payload["message"] == "Necesitamos sumar este producto para la campaña de abril."
        assert payload["items"][0]["product_id"] == str(product_id)
        assert payload["items"][0]["quantity"] == "3.00"
        assert payload["email_status"] == ProductRequestEmailStatus.PENDING.value
        assert payload["email_attempts"] == 0

        await logout(client)
        await login_user(client, owner_email)

        status_payload = await wait_for_product_request_status_in_db(
            uuid.UUID(payload["id"]),
            ProductRequestEmailStatus.SENT,
        )
        assert status_payload["email_attempts"] == 1
        assert status_payload["email_last_error"] is None
        assert status_payload["email_sent_at"] is not None

    async def test_owner_cannot_create_product_request(self, client: AsyncClient):
        owner_email = "pr-owner-forbidden-create@example.com"
        await setup_authenticated_user_with_organization(client, owner_email)
        create_product_response = await client.post("/products", json=build_product_payload())
        assert create_product_response.status_code == 201
        product_id = create_product_response.json()["id"]

        response = await client.post(
            "/product-requests",
            json={
                "subject": "Intento owner",
                "message": "Este owner no deberia poder crear solicitudes.",
                "items": [{"product_id": product_id, "quantity": "1"}],
            },
        )

        assert response.status_code == 403

    async def test_owner_can_list_product_requests_for_organization(self, client: AsyncClient):
        owner_email, member_email, organization_id, product_id = await setup_owner_and_member(
            client,
            owner_email="pr-owner-list@example.com",
            member_email="pr-member-list@example.com",
        )

        await login_user(client, member_email)
        first_response = await client.post(
            "/product-requests",
            json={
                "subject": "Solicitud uno",
                "message": "Detalle de solicitud uno para revisar con compras.",
                "items": [{"product_id": str(product_id), "quantity": "1"}],
            },
        )
        second_response = await client.post(
            "/product-requests",
            json={
                "subject": "Solicitud dos",
                "message": "Detalle de solicitud dos para revisar con compras.",
                "items": [{"product_id": str(product_id), "quantity": "2"}],
            },
        )
        assert first_response.status_code == 201
        assert second_response.status_code == 201

        first_request_id = first_response.json()["id"]
        second_request_id = second_response.json()["id"]

        await logout(client)
        await login_user(client, owner_email)

        list_response = await client.get("/product-requests")
        assert list_response.status_code == 200
        payload = list_response.json()
        request_ids = {item["id"] for item in payload}
        assert first_request_id in request_ids
        assert second_request_id in request_ids
        assert {item["organization_id"] for item in payload} == {str(organization_id)}

    async def test_member_can_list_product_requests_for_assigned_location(self, client: AsyncClient):
        owner_email, member_email, organization_id, product_id = await setup_owner_and_member(
            client,
            owner_email="pr-owner-member-list@example.com",
            member_email="pr-member-list@example.com",
        )
        member_location_id = await get_user_assigned_location_id(member_email)

        await login_user(client, owner_email)
        second_location_payload = build_location_payload()
        second_location_payload["name"] = "Sucursal Secundaria"
        second_location_response = await client.post("/locations", json=second_location_payload)
        assert second_location_response.status_code == 201
        second_location_id = uuid.UUID(second_location_response.json()["id"])

        await logout(client)
        second_member_email = "pr-member-list-second@example.com"
        await setup_member_user_in_organization(
            client,
            second_member_email,
            organization_id,
            location_id=second_location_id,
        )

        await logout(client)
        await login_user(client, member_email)
        first_create_response = await client.post(
            "/product-requests",
            json={
                "subject": "Pedido ubicación principal",
                "message": "Pedido creado por member de ubicación principal.",
                "items": [{"product_id": str(product_id), "quantity": "1"}],
            },
        )
        assert first_create_response.status_code == 201
        first_request_id = first_create_response.json()["id"]

        await logout(client)
        await login_user(client, second_member_email)
        second_create_response = await client.post(
            "/product-requests",
            json={
                "subject": "Pedido ubicación secundaria",
                "message": "Pedido creado por member de ubicación secundaria.",
                "items": [{"product_id": str(product_id), "quantity": "1"}],
            },
        )
        assert second_create_response.status_code == 201
        second_request_id = second_create_response.json()["id"]

        await logout(client)
        await login_user(client, member_email)
        response = await client.get("/product-requests")

        assert response.status_code == 200
        payload = response.json()
        request_ids = {item["id"] for item in payload}
        assert first_request_id in request_ids
        assert second_request_id not in request_ids
        assert {item["requested_for_location_id"] for item in payload} == {str(member_location_id)}
        assert all(item["requested_for_location_name"] is not None for item in payload)
        assert all(item["requested_for_location_address"] is not None for item in payload)

    async def test_member_cannot_filter_product_requests_for_other_location(self, client: AsyncClient):
        owner_email, member_email, _organization_id, _product_id = await setup_owner_and_member(
            client,
            owner_email="pr-owner-member-filter-denied@example.com",
            member_email="pr-member-filter-denied@example.com",
        )

        await login_user(client, owner_email)
        second_location_payload = build_location_payload()
        second_location_payload["name"] = "Sucursal no asignada"
        second_location_response = await client.post("/locations", json=second_location_payload)
        assert second_location_response.status_code == 201
        second_location_id = second_location_response.json()["id"]

        await logout(client)
        await login_user(client, member_email)
        response = await client.get(
            "/product-requests",
            params={"requested_for_location_id": second_location_id},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "El miembro no puede consultar pedidos de otra ubicación."

    async def test_owner_list_supports_location_and_date_filters(self, client: AsyncClient):
        owner_email, member_email, organization_id, product_id = await setup_owner_and_member(
            client,
            owner_email="pr-owner-filter@example.com",
            member_email="pr-member-filter-a@example.com",
        )

        await login_user(client, owner_email)
        second_location_payload = build_location_payload()
        second_location_payload["name"] = "Sucursal filtro B"
        second_location_response = await client.post("/locations", json=second_location_payload)
        assert second_location_response.status_code == 201
        member_b_location_id = uuid.UUID(second_location_response.json()["id"])

        await logout(client)
        member_b_email = "pr-member-filter-b@example.com"
        await setup_member_user_in_organization(
            client,
            member_b_email,
            organization_id,
            location_id=member_b_location_id,
        )

        await logout(client)
        await login_user(client, member_email)
        first_create_response = await client.post(
            "/product-requests",
            json={
                "subject": "Pedido filtro A",
                "message": "Pedido para ubicación A.",
                "items": [{"product_id": str(product_id), "quantity": "1"}],
            },
        )
        assert first_create_response.status_code == 201
        first_request_id = first_create_response.json()["id"]

        await logout(client)
        await login_user(client, member_b_email)
        second_create_response = await client.post(
            "/product-requests",
            json={
                "subject": "Pedido filtro B",
                "message": "Pedido para ubicación B.",
                "items": [{"product_id": str(product_id), "quantity": "2"}],
            },
        )
        assert second_create_response.status_code == 201
        second_request_id = second_create_response.json()["id"]

        await logout(client)
        await login_user(client, owner_email)

        location_filtered_response = await client.get(
            "/product-requests",
            params={"requested_for_location_id": str(member_b_location_id)},
        )
        assert location_filtered_response.status_code == 200
        location_filtered_ids = {item["id"] for item in location_filtered_response.json()}
        assert second_request_id in location_filtered_ids
        assert first_request_id not in location_filtered_ids

        created_from_filtered_response = await client.get(
            "/product-requests",
            params={"created_from": "2100-01-01T00:00:00Z"},
        )
        assert created_from_filtered_response.status_code == 200
        assert created_from_filtered_response.json() == []

        created_to_filtered_response = await client.get(
            "/product-requests",
            params={"created_to": "2000-01-01T00:00:00Z"},
        )
        assert created_to_filtered_response.status_code == 200
        assert created_to_filtered_response.json() == []

    async def test_list_rejects_invalid_date_range(self, client: AsyncClient):
        owner_email = "pr-owner-invalid-date-range@example.com"
        await setup_authenticated_user_with_organization(client, owner_email)

        response = await client.get(
            "/product-requests",
            params={
                "created_from": "2026-03-28T00:00:00Z",
                "created_to": "2026-03-27T00:00:00Z",
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "Value error, La fecha desde debe ser menor o igual a la fecha hasta."


class TestProductRequestsEmailStatus:
    async def test_creation_persists_pending_before_background_send(
        self,
        client: AsyncClient,
    ):
        _owner_email, member_email, _organization_id, product_id = await setup_owner_and_member(
            client,
            owner_email="pr-owner-pending@example.com",
            member_email="pr-member-pending@example.com",
        )

        await login_user(client, member_email)
        response = await client.post(
            "/product-requests",
            json={
                "subject": "Estado pending",
                "message": "Esta solicitud se debe guardar en pending antes del envio.",
                "items": [{"product_id": str(product_id), "quantity": "1"}],
            },
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["email_status"] == ProductRequestEmailStatus.PENDING.value
        assert payload["email_attempts"] == 0

        product_request_id = uuid.UUID(payload["id"])

        async with async_session_maker() as session:
            outbox_events = list(
                (
                    await session.execute(
                        select(NotificationOutboxEvent).where(
                            NotificationOutboxEvent.event_type
                            == EVENT_PRODUCT_REQUEST_OWNER_NOTIFICATION_REQUESTED,
                            NotificationOutboxEvent.aggregate_id == product_request_id
                        )
                    )
                )
                .scalars()
                .all()
            )

        assert len(outbox_events) == 1
        assert outbox_events[0].status == NotificationOutboxStatus.PENDING
        assert outbox_events[0].attempts == 0

    async def test_email_failure_marks_request_as_failed_and_keeps_record(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ):
        async def _failing_sender(**_kwargs):
            raise RuntimeError("smtp down")

        monkeypatch.setattr(
            "features.product_requests.emails.send_product_request_email",
            _failing_sender,
        )
        monkeypatch.setattr("features.product_requests.service.EMAIL_SEND_MAX_ATTEMPTS", 2)

        _owner_email, member_email, _organization_id, product_id = await setup_owner_and_member(
            client,
            owner_email="pr-owner-email-fail@example.com",
            member_email="pr-member-email-fail@example.com",
        )

        await login_user(client, member_email)
        response = await client.post(
            "/product-requests",
            json={
                "subject": "Falla de email",
                "message": "Esta solicitud debe quedar registrada aunque falle el envio.",
                "items": [{"product_id": str(product_id), "quantity": "4"}],
            },
        )
        assert response.status_code == 201
        product_request_id = uuid.UUID(response.json()["id"])

        status_payload = await wait_for_product_request_status_in_db(
            product_request_id,
            ProductRequestEmailStatus.FAILED,
        )
        assert status_payload["email_attempts"] == 2
        assert "smtp down" in str(status_payload["email_last_error"])

    async def test_non_sendable_owner_marks_request_as_failed(self, client: AsyncClient):
        owner_email, member_email, _organization_id, product_id = await setup_owner_and_member(
            client,
            owner_email="pr-owner-not-sendable@example.com",
            member_email="pr-member-not-sendable@example.com",
        )
        await set_user_verified(owner_email, False)

        await login_user(client, member_email)
        response = await client.post(
            "/product-requests",
            json={
                "subject": "Owner no enviable",
                "message": "Si owner no es verificable, la solicitud debe terminar en failed.",
                "items": [{"product_id": str(product_id), "quantity": "2"}],
            },
        )
        assert response.status_code == 201
        product_request_id = uuid.UUID(response.json()["id"])

        status_payload = await wait_for_product_request_status_in_db(
            product_request_id,
            ProductRequestEmailStatus.FAILED,
        )
        assert status_payload["email_attempts"] == 1
        assert "no tiene email verificado" in str(status_payload["email_last_error"])


class TestProductRequestsIsolation:
    async def test_owner_list_is_isolated_by_organization(self, client: AsyncClient):
        owner_a, member_a, _organization_a_id, product_a_id = await setup_owner_and_member(
            client,
            owner_email="pr-owner-a@example.com",
            member_email="pr-member-a@example.com",
        )
        owner_b, member_b, _organization_b_id, product_b_id = await setup_owner_and_member(
            client,
            owner_email="pr-owner-b@example.com",
            member_email="pr-member-b@example.com",
        )

        await login_user(client, member_a)
        create_a_response = await client.post(
            "/product-requests",
            json={
                "subject": "Solicitud org A",
                "message": "Solicitud creada por member A para su organizacion.",
                "items": [{"product_id": str(product_a_id), "quantity": "5"}],
            },
        )
        assert create_a_response.status_code == 201
        request_a_id = create_a_response.json()["id"]

        await logout(client)
        await login_user(client, member_b)
        create_b_response = await client.post(
            "/product-requests",
            json={
                "subject": "Solicitud org B",
                "message": "Solicitud creada por member B para su organizacion.",
                "items": [{"product_id": str(product_b_id), "quantity": "6"}],
            },
        )
        assert create_b_response.status_code == 201
        request_b_id = create_b_response.json()["id"]

        await logout(client)
        await login_user(client, owner_a)
        owner_a_list_response = await client.get("/product-requests")
        assert owner_a_list_response.status_code == 200
        owner_a_ids = {item["id"] for item in owner_a_list_response.json()}
        assert request_a_id in owner_a_ids
        assert request_b_id not in owner_a_ids

        await logout(client)
        await login_user(client, owner_b)
        owner_b_list_response = await client.get("/product-requests")
        assert owner_b_list_response.status_code == 200
        owner_b_ids = {item["id"] for item in owner_b_list_response.json()}
        assert request_b_id in owner_b_ids
        assert request_a_id not in owner_b_ids
