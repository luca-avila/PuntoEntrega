import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from tests.test_locations import setup_authenticated_user_with_organization
from tests.test_products import build_product_payload


@pytest.fixture(autouse=True)
def mock_delivery_email_success(monkeypatch: pytest.MonkeyPatch):
    async def _success_sender(_delivery, summary_recipient_email=None):
        return None

    monkeypatch.setattr(
        "features.deliveries.service.send_delivery_summary_email",
        _success_sender,
    )


def build_location_payload(name: str = "Sucursal Centro") -> dict[str, object]:
    return {
        "name": name,
        "address": "Av. Siempre Viva 742",
        "contact_name": "Maria Perez",
        "contact_phone": "+54 11 1234 5678",
        "contact_email": "maria@example.com",
        "latitude": -34.6037,
        "longitude": -58.3816,
        "notes": "Entregar por la puerta lateral.",
    }


async def create_location(client: AsyncClient, name: str = "Sucursal Centro") -> dict[str, object]:
    response = await client.post("/locations", json=build_location_payload(name=name))
    assert response.status_code == 201
    return response.json()


async def create_product(
    client: AsyncClient,
    *,
    name: str = "Harina de almendras",
    is_active: bool = True,
) -> dict[str, object]:
    payload = build_product_payload()
    payload["name"] = name
    payload["is_active"] = is_active
    response = await client.post("/products", json=payload)
    assert response.status_code == 201
    return response.json()


async def wait_for_delivery_status(
    client: AsyncClient,
    delivery_id: str,
    expected_status: str,
    *,
    attempts: int = 10,
    delay_seconds: float = 0.05,
) -> dict[str, object]:
    for _ in range(attempts):
        response = await client.get(f"/deliveries/{delivery_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["email_status"] == expected_status:
            return payload
        await asyncio.sleep(delay_seconds)
    raise AssertionError(
        f"Delivery {delivery_id} did not reach status {expected_status} "
        f"after {attempts} attempts."
    )


class TestDeliveriesAuth:
    async def test_deliveries_endpoints_require_authentication(self, client: AsyncClient):
        delivery_id = uuid.uuid4()

        list_response = await client.get("/deliveries")
        create_response = await client.post("/deliveries", json={})
        get_response = await client.get(f"/deliveries/{delivery_id}")

        assert list_response.status_code == 401
        assert create_response.status_code == 401
        assert get_response.status_code == 401


class TestDeliveriesCrud:
    async def test_create_list_and_get_delivery(self, client: AsyncClient):
        user_email = "deliveries-owner@example.com"
        await setup_authenticated_user_with_organization(client, user_email)

        location = await create_location(client)
        product = await create_product(client)
        delivered_at = datetime.now(UTC).replace(microsecond=0)

        create_response = await client.post(
            "/deliveries",
            json={
                "location_id": location["id"],
                "delivered_at": delivered_at.isoformat(),
                "payment_method": "transfer",
                "payment_notes": "Pagado contra entrega.",
                "observations": "Entregado en depósito.",
                "summary_recipient_email": "resumen-owner@example.com",
                "items": [{"product_id": product["id"], "quantity": "3.50"}],
            },
        )
        assert create_response.status_code == 201
        created_delivery = create_response.json()
        delivery_id = created_delivery["id"]
        assert created_delivery["location_id"] == location["id"]
        assert created_delivery["payment_method"] == "transfer"
        assert created_delivery["email_status"] == "pending"
        assert len(created_delivery["items"]) == 1

        list_response = await client.get("/deliveries")
        assert list_response.status_code == 200
        listed_deliveries = list_response.json()
        assert len(listed_deliveries) == 1
        assert listed_deliveries[0]["id"] == delivery_id

        fetched_delivery = await wait_for_delivery_status(client, delivery_id, "sent")
        assert fetched_delivery["id"] == delivery_id
        assert fetched_delivery["items"][0]["product_id"] == product["id"]

    async def test_create_delivery_uses_summary_recipient_email_override(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ):
        captured: dict[str, str | None] = {"summary_recipient_email": None}

        async def _capture_sender(_delivery, summary_recipient_email=None):
            captured["summary_recipient_email"] = summary_recipient_email

        monkeypatch.setattr(
            "features.deliveries.service.send_delivery_summary_email",
            _capture_sender,
        )

        user_email = "deliveries-recipient-override@example.com"
        await setup_authenticated_user_with_organization(client, user_email)

        location = await create_location(client)
        product = await create_product(client)
        summary_recipient_email = "avisos+entregas@example.com"

        response = await client.post(
            "/deliveries",
            json={
                "location_id": location["id"],
                "delivered_at": datetime.now(UTC).isoformat(),
                "payment_method": "cash",
                "summary_recipient_email": summary_recipient_email,
                "items": [{"product_id": product["id"], "quantity": "1"}],
            },
        )
        assert response.status_code == 201
        delivery_id = response.json()["id"]

        await wait_for_delivery_status(client, delivery_id, "sent")
        assert captured["summary_recipient_email"] == summary_recipient_email

    async def test_email_failure_keeps_delivery_and_sets_failed_status(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ):
        async def _failing_sender(_delivery, summary_recipient_email=None):
            raise RuntimeError("smtp down")

        monkeypatch.setattr(
            "features.deliveries.service.send_delivery_summary_email",
            _failing_sender,
        )

        user_email = "deliveries-email-failed@example.com"
        await setup_authenticated_user_with_organization(client, user_email)

        location = await create_location(client)
        product = await create_product(client)

        response = await client.post(
            "/deliveries",
            json={
                "location_id": location["id"],
                "delivered_at": datetime.now(UTC).isoformat(),
                "payment_method": "cash",
                "summary_recipient_email": "resumen-failed@example.com",
                "items": [{"product_id": product["id"], "quantity": "1"}],
            },
        )
        assert response.status_code == 201
        delivery = response.json()
        assert delivery["email_status"] == "pending"

        persisted_delivery = await wait_for_delivery_status(client, delivery["id"], "failed")
        assert persisted_delivery["id"] == delivery["id"]

    async def test_create_delivery_requires_items(self, client: AsyncClient):
        user_email = "deliveries-missing-items@example.com"
        await setup_authenticated_user_with_organization(client, user_email)

        location = await create_location(client)

        response = await client.post(
            "/deliveries",
            json={
                "location_id": location["id"],
                "delivered_at": datetime.now(UTC).isoformat(),
                "payment_method": "cash",
                "summary_recipient_email": "resumen-missing-items@example.com",
                "items": [],
            },
        )
        assert response.status_code == 422

    async def test_create_delivery_requires_summary_recipient_email(self, client: AsyncClient):
        user_email = "deliveries-missing-recipient@example.com"
        await setup_authenticated_user_with_organization(client, user_email)

        location = await create_location(client)
        product = await create_product(client)

        response = await client.post(
            "/deliveries",
            json={
                "location_id": location["id"],
                "delivered_at": datetime.now(UTC).isoformat(),
                "payment_method": "cash",
                "items": [{"product_id": product["id"], "quantity": "1"}],
            },
        )
        assert response.status_code == 422

    async def test_create_delivery_rejects_non_positive_quantity(self, client: AsyncClient):
        user_email = "deliveries-invalid-quantity@example.com"
        await setup_authenticated_user_with_organization(client, user_email)

        location = await create_location(client)
        product = await create_product(client)

        response = await client.post(
            "/deliveries",
            json={
                "location_id": location["id"],
                "delivered_at": datetime.now(UTC).isoformat(),
                "payment_method": "cash",
                "summary_recipient_email": "resumen-invalid-quantity@example.com",
                "items": [{"product_id": product["id"], "quantity": "0"}],
            },
        )
        assert response.status_code == 422

    async def test_create_delivery_rejects_duplicate_products(self, client: AsyncClient):
        user_email = "deliveries-duplicate-products@example.com"
        await setup_authenticated_user_with_organization(client, user_email)

        location = await create_location(client)
        product = await create_product(client)

        response = await client.post(
            "/deliveries",
            json={
                "location_id": location["id"],
                "delivered_at": datetime.now(UTC).isoformat(),
                "payment_method": "cash",
                "summary_recipient_email": "resumen-duplicado@example.com",
                "items": [
                    {"product_id": product["id"], "quantity": "1"},
                    {"product_id": product["id"], "quantity": "2"},
                ],
            },
        )
        assert response.status_code == 422
        assert "No repitas el mismo producto" in response.text

    async def test_list_deliveries_supports_location_and_date_filters(self, client: AsyncClient):
        user_email = "deliveries-filter@example.com"
        await setup_authenticated_user_with_organization(client, user_email)

        first_location = await create_location(client, name="Sucursal Norte")
        second_location = await create_location(client, name="Sucursal Sur")
        product = await create_product(client)

        old_delivery_time = datetime.now(UTC) - timedelta(days=3)
        recent_delivery_time = datetime.now(UTC) - timedelta(days=1)

        old_delivery_response = await client.post(
            "/deliveries",
            json={
                "location_id": first_location["id"],
                "delivered_at": old_delivery_time.isoformat(),
                "payment_method": "cash",
                "summary_recipient_email": "resumen-old@example.com",
                "items": [{"product_id": product["id"], "quantity": "1"}],
            },
        )
        recent_delivery_response = await client.post(
            "/deliveries",
            json={
                "location_id": second_location["id"],
                "delivered_at": recent_delivery_time.isoformat(),
                "payment_method": "transfer",
                "summary_recipient_email": "resumen-recent@example.com",
                "items": [{"product_id": product["id"], "quantity": "2"}],
            },
        )
        assert old_delivery_response.status_code == 201
        assert recent_delivery_response.status_code == 201

        location_filtered_response = await client.get(
            "/deliveries",
            params={"location_id": second_location["id"]},
        )
        assert location_filtered_response.status_code == 200
        location_filtered_deliveries = location_filtered_response.json()
        assert len(location_filtered_deliveries) == 1
        assert location_filtered_deliveries[0]["location_id"] == second_location["id"]

        date_filtered_response = await client.get(
            "/deliveries",
            params={"delivered_from": (datetime.now(UTC) - timedelta(days=2)).isoformat()},
        )
        assert date_filtered_response.status_code == 200
        date_filtered_deliveries = date_filtered_response.json()
        assert len(date_filtered_deliveries) == 1
        assert date_filtered_deliveries[0]["location_id"] == second_location["id"]

    async def test_list_deliveries_rejects_invalid_date_range(self, client: AsyncClient):
        user_email = "deliveries-invalid-date-range@example.com"
        await setup_authenticated_user_with_organization(client, user_email)

        delivered_from = datetime(2026, 5, 10, tzinfo=UTC).isoformat()
        delivered_to = datetime(2026, 5, 1, tzinfo=UTC).isoformat()

        response = await client.get(
            "/deliveries",
            params={
                "delivered_from": delivered_from,
                "delivered_to": delivered_to,
            },
        )

        assert response.status_code == 422
        assert "La fecha desde debe ser menor o igual a la fecha hasta." in response.text


class TestDeliveriesIsolation:
    async def test_cannot_access_or_create_with_foreign_resources(self, client: AsyncClient):
        first_email = "deliveries-org-a@example.com"
        second_email = "deliveries-org-b@example.com"

        await setup_authenticated_user_with_organization(client, first_email)

        location_a = await create_location(client)
        product_a = await create_product(client)
        delivery_response = await client.post(
            "/deliveries",
            json={
                "location_id": location_a["id"],
                "delivered_at": datetime.now(UTC).isoformat(),
                "payment_method": "cash",
                "summary_recipient_email": "resumen-org-a@example.com",
                "items": [{"product_id": product_a["id"], "quantity": "1"}],
            },
        )
        assert delivery_response.status_code == 201
        delivery_id = delivery_response.json()["id"]

        logout_response = await client.post("/auth/jwt/logout")
        assert logout_response.status_code in (200, 204)

        await setup_authenticated_user_with_organization(client, second_email)

        get_response = await client.get(f"/deliveries/{delivery_id}")
        assert get_response.status_code == 404
        assert get_response.json()["detail"] == "Entrega no encontrada."

        foreign_location_delivery_response = await client.post(
            "/deliveries",
            json={
                "location_id": location_a["id"],
                "delivered_at": datetime.now(UTC).isoformat(),
                "payment_method": "cash",
                "summary_recipient_email": "resumen-org-b-foreign-location@example.com",
                "items": [{"product_id": product_a["id"], "quantity": "1"}],
            },
        )
        assert foreign_location_delivery_response.status_code == 404
        assert foreign_location_delivery_response.json()["detail"] == "Ubicación no encontrada."

        location_b = await create_location(client, name="Sucursal B")
        foreign_product_delivery_response = await client.post(
            "/deliveries",
            json={
                "location_id": location_b["id"],
                "delivered_at": datetime.now(UTC).isoformat(),
                "payment_method": "cash",
                "summary_recipient_email": "resumen-org-b-foreign-product@example.com",
                "items": [{"product_id": product_a["id"], "quantity": "1"}],
            },
        )
        assert foreign_product_delivery_response.status_code == 404
        assert foreign_product_delivery_response.json()["detail"] == "Producto no encontrado."

    async def test_create_delivery_rejects_any_foreign_product_in_multi_item_payload(
        self, client: AsyncClient
    ):
        first_email = "deliveries-multi-item-org-a@example.com"
        second_email = "deliveries-multi-item-org-b@example.com"

        await setup_authenticated_user_with_organization(client, first_email)

        foreign_product = await create_product(client, name="Producto organización A")

        logout_response = await client.post("/auth/jwt/logout")
        assert logout_response.status_code in (200, 204)

        await setup_authenticated_user_with_organization(client, second_email)

        location = await create_location(client, name="Sucursal organización B")
        own_product = await create_product(client, name="Producto organización B")

        response = await client.post(
            "/deliveries",
            json={
                "location_id": location["id"],
                "delivered_at": datetime.now(UTC).isoformat(),
                "payment_method": "cash",
                "summary_recipient_email": "resumen-multi-item@example.com",
                "items": [
                    {"product_id": own_product["id"], "quantity": "1"},
                    {"product_id": foreign_product["id"], "quantity": "2"},
                ],
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Producto no encontrado."
