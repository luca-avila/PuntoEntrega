import asyncio
import uuid
from typing import cast

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.sql.elements import ColumnElement

from core.db import async_session_maker
from features.auth.models import User
from features.product_requests.models import ProductRequest, ProductRequestEmailStatus
from tests.test_locations import (
    login_user,
    setup_authenticated_user_with_organization,
    setup_member_user_in_organization,
)
from tests.test_products import build_product_payload


@pytest.fixture(autouse=True)
def fast_product_request_email_retries(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("features.product_requests.service.EMAIL_SEND_RETRY_DELAY_SECONDS", 0.0)


@pytest.fixture(autouse=True)
def mock_product_request_email_success(monkeypatch: pytest.MonkeyPatch):
    async def _success_sender(**_kwargs):
        return None

    monkeypatch.setattr(
        "features.product_requests.service.send_product_request_email",
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


async def wait_for_product_request_status_in_db(
    product_request_id: uuid.UUID,
    expected_status: ProductRequestEmailStatus,
    *,
    attempts: int = 30,
    delay_seconds: float = 0.05,
) -> dict[str, object]:
    for _ in range(attempts):
        async with async_session_maker() as session:
            product_request = await session.get(ProductRequest, product_request_id)
            if (
                product_request is not None
                and product_request.email_status == expected_status
            ):
                return {
                    "id": str(product_request.id),
                    "email_status": product_request.email_status.value,
                    "email_attempts": product_request.email_attempts,
                    "email_last_error": product_request.email_last_error,
                    "email_sent_at": product_request.email_sent_at,
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

    async def test_member_cannot_list_product_requests(self, client: AsyncClient):
        _owner_email, member_email, _organization_id, _product_id = await setup_owner_and_member(
            client,
            owner_email="pr-owner-member-list-forbidden@example.com",
            member_email="pr-member-list-forbidden@example.com",
        )

        await login_user(client, member_email)
        response = await client.get("/product-requests")

        assert response.status_code == 403


class TestProductRequestsEmailStatus:
    async def test_creation_persists_pending_before_background_send(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ):
        async def _noop_background(_product_request_id: uuid.UUID) -> None:
            return None

        monkeypatch.setattr(
            "features.product_requests.api.routes.send_product_request_email_in_background",
            _noop_background,
        )

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
            persisted_request = await session.get(ProductRequest, product_request_id)

        assert persisted_request is not None
        assert persisted_request.email_status == ProductRequestEmailStatus.PENDING
        assert persisted_request.email_attempts == 0
        assert persisted_request.email_sent_at is None

    async def test_email_failure_marks_request_as_failed_and_keeps_record(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ):
        async def _failing_sender(**_kwargs):
            raise RuntimeError("smtp down")

        monkeypatch.setattr(
            "features.product_requests.service.send_product_request_email",
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

        async with async_session_maker() as session:
            persisted_request = await session.get(ProductRequest, product_request_id)

        assert persisted_request is not None
        assert persisted_request.email_status == ProductRequestEmailStatus.FAILED

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
