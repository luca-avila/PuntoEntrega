from typing import cast

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.sql.elements import ColumnElement

from core.db import async_session_maker
from features.auth.models import User
from features.notifications.errors import EmailSendError
from features.notifications.worker import process_pending_events

USER_EMAIL = "test@example.com"
USER_PASSWORD = "StrongPass123!"


async def register_user(client: AsyncClient, email: str = USER_EMAIL, password: str = USER_PASSWORD):
    """Helper to register a user and return the response."""
    return await client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )


async def login_user(client: AsyncClient, email: str = USER_EMAIL, password: str = USER_PASSWORD):
    """Helper to log in and return the response (sets auth cookie)."""
    return await client.post(
        "/auth/jwt/login",
        data={"username": email, "password": password},
    )


async def mark_user_verified(email: str = USER_EMAIL) -> None:
    """Helper to set a user as verified in DB for tests."""
    async with async_session_maker() as session:
        email_filter = cast(ColumnElement[bool], User.email == email)
        result = await session.execute(select(User).where(email_filter))
        user = result.scalar_one()
        user.is_verified = True
        await session.commit()


# ── Registration Tests ──────────────────────────────────────────────


class TestRegistration:
    async def test_register_success(self, client: AsyncClient):
        response = await register_user(client)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == USER_EMAIL
        assert "id" in data
        assert data["is_active"] is True
        assert "role" not in data

    async def test_register_duplicate_email(self, client: AsyncClient):
        await register_user(client)
        response = await register_user(client)
        assert response.status_code == 400

    async def test_register_does_not_create_organization_automatically(self, client: AsyncClient):
        first_response = await register_user(client, email="same@example.com")
        second_response = await register_user(client, email="same@another.com")
        assert first_response.status_code == 201
        assert second_response.status_code == 201

    async def test_register_invalid_email(self, client: AsyncClient):
        response = await register_user(client, email="not-an-email")
        assert response.status_code == 422

    async def test_register_missing_password(self, client: AsyncClient):
        """Missing password field should return 422."""
        response = await client.post("/auth/register", json={"email": USER_EMAIL})
        assert response.status_code == 422


# ── Password Validation Tests ───────────────────────────────────────


class TestPasswordValidation:
    async def test_password_too_short(self, client: AsyncClient):
        response = await register_user(client, password="Ab1!")
        assert response.status_code == 400
        assert "8 characters" in response.json()["detail"]["reason"]

    async def test_password_no_uppercase(self, client: AsyncClient):
        response = await register_user(client, password="lowercase1!")
        assert response.status_code == 400
        assert "uppercase" in response.json()["detail"]["reason"]

    async def test_password_no_lowercase(self, client: AsyncClient):
        response = await register_user(client, password="UPPERCASE1!")
        assert response.status_code == 400
        assert "lowercase" in response.json()["detail"]["reason"]

    async def test_password_no_digit(self, client: AsyncClient):
        response = await register_user(client, password="NoDigits!!")
        assert response.status_code == 400
        assert "digit" in response.json()["detail"]["reason"]

    async def test_password_no_special_char(self, client: AsyncClient):
        response = await register_user(client, password="NoSpecial1A")
        assert response.status_code == 400
        assert "special character" in response.json()["detail"]["reason"]

    async def test_password_contains_email_username(self, client: AsyncClient):
        response = await register_user(client, email="john@example.com", password="John1234!")
        assert response.status_code == 400
        assert "email" in response.json()["detail"]["reason"]

    async def test_valid_strong_password(self, client: AsyncClient):
        response = await register_user(client, password="V3ryStr0ng!")
        assert response.status_code == 201


# ── Login Tests ──────────────────────────────────────────────────────


class TestLogin:
    async def test_login_success(self, client: AsyncClient):
        await register_user(client)
        await mark_user_verified()
        response = await login_user(client)
        assert response.status_code == 200 or response.status_code == 204
        assert "auth" in response.cookies

    async def test_login_unverified_user_rejected(self, client: AsyncClient):
        await register_user(client)
        response = await login_user(client)
        assert response.status_code == 400
        assert response.json()["detail"] == "LOGIN_USER_NOT_VERIFIED"

    async def test_login_unverified_user_does_not_resend_verify_within_1h(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        sent_calls: list[tuple[str, str]] = []

        async def fake_send_verify_email(email: str, token: str) -> None:
            sent_calls.append((email, token))

        monkeypatch.setattr(
            "features.auth.emails.send_verify_email",
            fake_send_verify_email,
        )

        register_response = await register_user(client)
        assert register_response.status_code == 201
        await process_pending_events()
        assert len(sent_calls) == 1

        response = await login_user(client)
        assert response.status_code == 400
        assert response.json()["detail"] == "LOGIN_USER_NOT_VERIFIED"
        await process_pending_events()
        assert len(sent_calls) == 1

    async def test_login_wrong_password(self, client: AsyncClient):
        await register_user(client)
        await mark_user_verified()
        response = await login_user(client, password="WrongPassword!")
        assert response.status_code == 400

    async def test_login_nonexistent_user(self, client: AsyncClient):
        response = await login_user(client, email="nobody@example.com")
        assert response.status_code == 400


# ── Logout Tests ─────────────────────────────────────────────────────


class TestLogout:
    async def test_logout(self, client: AsyncClient):
        await register_user(client)
        await mark_user_verified()
        await login_user(client)
        response = await client.post("/auth/jwt/logout")
        assert response.status_code == 200 or response.status_code == 204


# ── Current User / Users Tests ───────────────────────────────────────


class TestCurrentUser:
    async def test_get_me_authenticated(self, client: AsyncClient):
        await register_user(client)
        await mark_user_verified()
        await login_user(client)
        response = await client.get("/users/me")
        assert response.status_code == 200
        assert response.json()["email"] == USER_EMAIL
        assert "role" not in response.json()

    async def test_get_me_unauthenticated(self, client: AsyncClient):
        response = await client.get("/users/me")
        assert response.status_code == 401

    async def test_patch_me(self, client: AsyncClient):
        await register_user(client)
        await mark_user_verified()
        await login_user(client)
        response = await client.patch("/users/me", json={"email": "new@example.com"})
        # fastapi-users may return 200
        assert response.status_code == 200
        # Email should be unchanged or updated depending on verification settings
        assert "email" in response.json()


# ── Email Flow Tests ────────────────────────────────────────────────


class TestEmailFlows:
    async def test_register_triggers_verify_email_send(self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
        sent_calls: list[tuple[str, str]] = []

        async def fake_send_verify_email(email: str, token: str) -> None:
            sent_calls.append((email, token))

        monkeypatch.setattr(
            "features.auth.emails.send_verify_email",
            fake_send_verify_email,
        )

        response = await register_user(client)
        assert response.status_code == 201
        await process_pending_events()
        assert len(sent_calls) == 1
        assert sent_calls[0][0] == USER_EMAIL
        assert sent_calls[0][1]

    async def test_register_email_failure_keeps_verify_resend_cooldown_after_enqueue(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        sent_calls: list[tuple[str, str]] = []

        async def fake_send_verify_email(email: str, token: str) -> None:
            sent_calls.append((email, token))
            raise EmailSendError("resend unavailable")

        monkeypatch.setattr(
            "features.auth.emails.send_verify_email",
            fake_send_verify_email,
        )

        register_response = await register_user(client)
        assert register_response.status_code == 201
        await process_pending_events()
        assert len(sent_calls) == 1

        login_response = await login_user(client)
        assert login_response.status_code == 400
        assert login_response.json()["detail"] == "LOGIN_USER_NOT_VERIFIED"
        assert len(sent_calls) == 1

    async def test_request_verify_token_sends_email_for_existing_user(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        sent_calls: list[tuple[str, str]] = []

        async def fake_send_verify_email(email: str, token: str) -> None:
            sent_calls.append((email, token))

        monkeypatch.setattr(
            "features.auth.emails.send_verify_email",
            fake_send_verify_email,
        )

        register_response = await register_user(client)
        assert register_response.status_code == 201
        await process_pending_events()

        sent_calls.clear()
        response = await client.post("/auth/request-verify-token", json={"email": USER_EMAIL})
        assert response.status_code in (200, 202)
        await process_pending_events()
        assert len(sent_calls) == 1
        assert sent_calls[0][0] == USER_EMAIL
        assert sent_calls[0][1]

    async def test_forgot_password_sends_email_for_existing_user(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        sent_calls: list[tuple[str, str]] = []

        async def fake_send_reset_password_email(email: str, token: str) -> None:
            sent_calls.append((email, token))

        monkeypatch.setattr(
            "features.auth.emails.send_reset_password_email",
            fake_send_reset_password_email,
        )

        register_response = await register_user(client)
        assert register_response.status_code == 201

        response = await client.post("/auth/forgot-password", json={"email": USER_EMAIL})
        assert response.status_code in (200, 202)
        await process_pending_events()
        assert len(sent_calls) == 1
        assert sent_calls[0][0] == USER_EMAIL
        assert sent_calls[0][1]

    async def test_forgot_password_email_failure_does_not_fail_endpoint(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        async def fake_send_reset_password_email(email: str, token: str) -> None:
            raise EmailSendError("resend unavailable")

        monkeypatch.setattr(
            "features.auth.emails.send_reset_password_email",
            fake_send_reset_password_email,
        )

        register_response = await register_user(client)
        assert register_response.status_code == 201

        response = await client.post("/auth/forgot-password", json={"email": USER_EMAIL})
        assert response.status_code in (200, 202)
        await process_pending_events()

    async def test_forgot_password_nonexistent_user_does_not_send_email(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        sent_calls: list[tuple[str, str]] = []

        async def fake_send_reset_password_email(email: str, token: str) -> None:
            sent_calls.append((email, token))

        monkeypatch.setattr(
            "features.auth.emails.send_reset_password_email",
            fake_send_reset_password_email,
        )

        response = await client.post("/auth/forgot-password", json={"email": "missing@example.com"})
        assert response.status_code in (200, 202)
        assert sent_calls == []
