import uuid

from httpx import AsyncClient

from tests.test_locations import login_user, mark_user_verified, register_user


def build_product_payload() -> dict[str, object]:
    return {
        "name": "Harina de almendras",
        "description": "Paquete de 1kg.",
        "is_active": True,
    }


class TestProductsAuth:
    async def test_products_endpoints_require_authentication(self, client: AsyncClient):
        payload = build_product_payload()
        product_id = uuid.uuid4()

        list_response = await client.get("/products")
        create_response = await client.post("/products", json=payload)
        get_response = await client.get(f"/products/{product_id}")
        patch_response = await client.patch(f"/products/{product_id}", json={"is_active": False})

        assert list_response.status_code == 401
        assert create_response.status_code == 401
        assert get_response.status_code == 401
        assert patch_response.status_code == 401


class TestProductsCrud:
    async def test_create_list_get_and_patch_product(self, client: AsyncClient):
        user_email = "products-owner@example.com"
        await register_user(client, user_email)
        await mark_user_verified(user_email)
        await login_user(client, user_email)

        payload = build_product_payload()
        create_response = await client.post("/products", json=payload)
        assert create_response.status_code == 201
        created_product = create_response.json()
        product_id = created_product["id"]
        assert created_product["name"] == payload["name"]
        assert created_product["is_active"] is True
        assert created_product["organization_id"] is not None

        list_response = await client.get("/products")
        assert list_response.status_code == 200
        listed_products = list_response.json()
        assert len(listed_products) == 1
        assert listed_products[0]["id"] == product_id

        get_response = await client.get(f"/products/{product_id}")
        assert get_response.status_code == 200
        assert get_response.json()["description"] == payload["description"]

        patch_response = await client.patch(
            f"/products/{product_id}",
            json={"is_active": False},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["is_active"] is False

    async def test_patch_product_requires_non_empty_payload(self, client: AsyncClient):
        user_email = "products-empty-patch@example.com"
        await register_user(client, user_email)
        await mark_user_verified(user_email)
        await login_user(client, user_email)

        create_response = await client.post("/products", json=build_product_payload())
        product_id = create_response.json()["id"]

        patch_response = await client.patch(f"/products/{product_id}", json={})
        assert patch_response.status_code == 422
        assert "Debe enviar al menos un campo" in patch_response.text

    async def test_active_only_query_excludes_inactive_products(self, client: AsyncClient):
        user_email = "products-active-filter@example.com"
        await register_user(client, user_email)
        await mark_user_verified(user_email)
        await login_user(client, user_email)

        active_product_response = await client.post(
            "/products",
            json={"name": "Producto Activo", "description": "Disponible", "is_active": True},
        )
        inactive_product_response = await client.post(
            "/products",
            json={"name": "Producto Inactivo", "description": "No disponible", "is_active": False},
        )
        assert active_product_response.status_code == 201
        assert inactive_product_response.status_code == 201

        all_products_response = await client.get("/products")
        assert all_products_response.status_code == 200
        assert len(all_products_response.json()) == 2

        active_only_response = await client.get("/products", params={"active_only": True})
        assert active_only_response.status_code == 200
        active_products = active_only_response.json()
        assert len(active_products) == 1
        assert active_products[0]["name"] == "Producto Activo"
        assert active_products[0]["is_active"] is True


class TestProductsIsolation:
    async def test_cannot_access_another_organizations_product(self, client: AsyncClient):
        first_email = "products-org-a@example.com"
        second_email = "products-org-b@example.com"

        await register_user(client, first_email)
        await mark_user_verified(first_email)
        await login_user(client, first_email)

        create_response = await client.post("/products", json=build_product_payload())
        assert create_response.status_code == 201
        first_product_id = create_response.json()["id"]

        logout_response = await client.post("/auth/jwt/logout")
        assert logout_response.status_code in (200, 204)

        await register_user(client, second_email)
        await mark_user_verified(second_email)
        await login_user(client, second_email)

        get_response = await client.get(f"/products/{first_product_id}")
        patch_response = await client.patch(
            f"/products/{first_product_id}",
            json={"is_active": False},
        )
        list_response = await client.get("/products")

        assert get_response.status_code == 404
        assert get_response.json()["detail"] == "Producto no encontrado."
        assert patch_response.status_code == 404
        assert patch_response.json()["detail"] == "Producto no encontrado."
        assert list_response.status_code == 200
        assert list_response.json() == []
