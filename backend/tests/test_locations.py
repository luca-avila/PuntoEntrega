import uuid
from typing import cast

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.sql.elements import ColumnElement

from core.db import async_session_maker
from features.auth.models import User

USER_PASSWORD = "StrongPass123!"


def build_location_payload() -> dict[str, object]:
    return {
        "name": "Sucursal Centro",
        "address": "Av. Siempre Viva 742",
        "contact_name": "Maria Perez",
        "contact_phone": "+54 11 1234 5678",
        "contact_email": "maria@example.com",
        "latitude": -34.6037,
        "longitude": -58.3816,
        "notes": "Entregar por la puerta lateral.",
    }


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


def _organization_name_from_email(email: str) -> str:
    local_part = email.split("@", maxsplit=1)[0].strip()
    if local_part:
        return f"Organización {local_part}"
    return "Organización Test"


async def create_organization_for_current_user(
    client: AsyncClient,
    email: str,
) -> None:
    response = await client.post(
        "/organizations",
        json={"name": _organization_name_from_email(email)},
    )
    assert response.status_code == 201


async def setup_authenticated_user_with_organization(
    client: AsyncClient,
    email: str,
) -> None:
    await register_user(client, email)
    await mark_user_verified(email)
    await login_user(client, email)
    await create_organization_for_current_user(client, email)


class TestLocationsAuth:
    async def test_locations_endpoints_require_authentication(self, client: AsyncClient):
        payload = build_location_payload()
        location_id = uuid.uuid4()

        list_response = await client.get("/locations")
        create_response = await client.post("/locations", json=payload)
        get_response = await client.get(f"/locations/{location_id}")
        patch_response = await client.patch(f"/locations/{location_id}", json={"notes": "x"})

        assert list_response.status_code == 401
        assert create_response.status_code == 401
        assert get_response.status_code == 401
        assert patch_response.status_code == 401


class TestLocationsCrud:
    async def test_create_list_get_and_patch_location(self, client: AsyncClient):
        user_email = "locations-owner@example.com"
        await setup_authenticated_user_with_organization(client, user_email)

        payload = build_location_payload()
        create_response = await client.post("/locations", json=payload)
        assert create_response.status_code == 201
        created_location = create_response.json()
        location_id = created_location["id"]
        assert created_location["name"] == payload["name"]
        assert created_location["organization_id"] is not None

        list_response = await client.get("/locations")
        assert list_response.status_code == 200
        listed_locations = list_response.json()
        assert len(listed_locations) == 1
        assert listed_locations[0]["id"] == location_id

        get_response = await client.get(f"/locations/{location_id}")
        assert get_response.status_code == 200
        assert get_response.json()["address"] == payload["address"]

        patch_response = await client.patch(
            f"/locations/{location_id}",
            json={"notes": "Actualizar horario de recepcion."},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["notes"] == "Actualizar horario de recepcion."

    async def test_patch_location_requires_non_empty_payload(self, client: AsyncClient):
        user_email = "locations-empty-patch@example.com"
        await setup_authenticated_user_with_organization(client, user_email)

        create_response = await client.post("/locations", json=build_location_payload())
        location_id = create_response.json()["id"]

        patch_response = await client.patch(f"/locations/{location_id}", json={})
        assert patch_response.status_code == 422
        assert "Debe enviar al menos un campo" in patch_response.text

    async def test_create_location_rejects_blank_name_or_address(self, client: AsyncClient):
        user_email = "locations-invalid-text@example.com"
        await setup_authenticated_user_with_organization(client, user_email)

        blank_name_payload = build_location_payload()
        blank_name_payload["name"] = "   "
        blank_name_response = await client.post("/locations", json=blank_name_payload)
        assert blank_name_response.status_code == 422

        blank_address_payload = build_location_payload()
        blank_address_payload["address"] = "   "
        blank_address_response = await client.post("/locations", json=blank_address_payload)
        assert blank_address_response.status_code == 422

    async def test_create_location_rejects_invalid_contact_email(self, client: AsyncClient):
        user_email = "locations-invalid-email@example.com"
        await setup_authenticated_user_with_organization(client, user_email)

        payload = build_location_payload()
        payload["contact_email"] = "email-invalido"

        response = await client.post("/locations", json=payload)
        assert response.status_code == 422
        assert "email de contacto válido" in response.text

    async def test_create_location_rejects_invalid_contact_phone(self, client: AsyncClient):
        user_email = "locations-invalid-phone@example.com"
        await setup_authenticated_user_with_organization(client, user_email)

        payload = build_location_payload()
        payload["contact_phone"] = "abc###"

        response = await client.post("/locations", json=payload)
        assert response.status_code == 422
        assert "teléfono de contacto válido" in response.text


class TestLocationsIsolation:
    async def test_cannot_access_another_organizations_location(self, client: AsyncClient):
        first_email = "locations-org-a@example.com"
        second_email = "locations-org-b@example.com"

        await setup_authenticated_user_with_organization(client, first_email)

        create_response = await client.post("/locations", json=build_location_payload())
        assert create_response.status_code == 201
        first_location_id = create_response.json()["id"]

        logout_response = await client.post("/auth/jwt/logout")
        assert logout_response.status_code in (200, 204)

        await setup_authenticated_user_with_organization(client, second_email)

        get_response = await client.get(f"/locations/{first_location_id}")
        patch_response = await client.patch(
            f"/locations/{first_location_id}",
            json={"notes": "Intento no autorizado."},
        )
        list_response = await client.get("/locations")

        assert get_response.status_code == 404
        assert get_response.json()["detail"] == "Ubicación no encontrada."
        assert patch_response.status_code == 404
        assert patch_response.json()["detail"] == "Ubicación no encontrada."
        assert list_response.status_code == 200
        assert list_response.json() == []
