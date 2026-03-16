import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from fastapi import Depends, Request
from fastapi_users import (
    BaseUserManager,
    FastAPIUsers,
    InvalidPasswordException,
    UUIDIDMixin,
    exceptions,
    schemas,
)
from fastapi_users.authentication import AuthenticationBackend, CookieTransport, JWTStrategy
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db import get_async_session
from features.auth.email import send_reset_password_email, send_verify_email
from features.auth.models import User
from features.organizations.models import Organization

logger = logging.getLogger(__name__)
VERIFY_EMAIL_TOKEN_LIFETIME_SECONDS = 3600
RESET_PASSWORD_TOKEN_LIFETIME_SECONDS = 3600
VERIFY_EMAIL_RESEND_COOLDOWN_SECONDS = 3600
_verify_email_last_sent_at: dict[uuid.UUID, datetime] = {}
ORGANIZATION_SLUG_MAX_LENGTH = 120


def _cleanup_verify_email_send_tracker(now: datetime) -> None:
    cutoff = now - timedelta(seconds=VERIFY_EMAIL_RESEND_COOLDOWN_SECONDS)
    stale_user_ids = [user_id for user_id, sent_at in _verify_email_last_sent_at.items() if sent_at < cutoff]
    for user_id in stale_user_ids:
        _verify_email_last_sent_at.pop(user_id, None)


def mark_verify_email_sent(user_id: uuid.UUID) -> None:
    now = datetime.now(UTC)
    _cleanup_verify_email_send_tracker(now)
    _verify_email_last_sent_at[user_id] = now


def can_send_verify_email(user_id: uuid.UUID) -> bool:
    now = datetime.now(UTC)
    _cleanup_verify_email_send_tracker(now)
    last_sent_at = _verify_email_last_sent_at.get(user_id)
    if last_sent_at is None:
        return True
    return now - last_sent_at >= timedelta(seconds=VERIFY_EMAIL_RESEND_COOLDOWN_SECONDS)


async def maybe_resend_verify_email_for_unverified_login(
    user_manager: BaseUserManager[User, uuid.UUID],
    user: User,
    request: Request,
) -> bool:
    """Resend verification email if the cooldown window has passed."""
    if user.is_verified:
        return False
    if not can_send_verify_email(user.id):
        return False

    await user_manager.request_verify(user, request)
    return True


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    """Get user database instance."""
    yield SQLAlchemyUserDatabase(session, User)


def _build_organization_name_from_email(email: str) -> str:
    local_part = email.split("@", maxsplit=1)[0]
    cleaned = re.sub(r"[._-]+", " ", local_part).strip()
    if not cleaned:
        return "Organization"
    return cleaned.title()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        slug = "organization"
    return slug[:ORGANIZATION_SLUG_MAX_LENGTH]


async def _organization_slug_exists(session: AsyncSession, slug: str) -> bool:
    result = await session.execute(
        select(Organization.id).where(Organization.slug == slug).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _build_unique_organization_slug(session: AsyncSession, email: str) -> str:
    base_slug = _slugify(email.split("@", maxsplit=1)[0])
    candidate = base_slug
    suffix = 2

    while await _organization_slug_exists(session, candidate):
        suffix_token = f"-{suffix}"
        max_base_length = ORGANIZATION_SLUG_MAX_LENGTH - len(suffix_token)
        truncated_base = base_slug[:max_base_length].rstrip("-")
        candidate = f"{truncated_base}{suffix_token}"
        suffix += 1

    return candidate


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """Custom user manager with strong password validation."""

    reset_password_token_secret = settings.SECRET_KEY
    verification_token_secret = settings.SECRET_KEY
    verification_token_lifetime_seconds = VERIFY_EMAIL_TOKEN_LIFETIME_SECONDS

    async def validate_password(self, password: str, user: Any) -> None:
        """Validate password strength."""
        errors = []

        if len(password) < settings.PASSWORD_MIN_LENGTH:
            errors.append(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long.")

        if settings.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter.")

        if settings.PASSWORD_REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter.")

        if settings.PASSWORD_REQUIRE_DIGIT and not re.search(r"\d", password):
            errors.append("Password must contain at least one digit.")

        if settings.PASSWORD_REQUIRE_SPECIAL and not re.search(r"[^A-Za-z0-9]", password):
            errors.append("Password must contain at least one special character.")

        if hasattr(user, "email") and user.email:
            email_username = user.email.split("@")[0].lower()
            if email_username in password.lower():
                errors.append("Password must not contain your email username.")

        if errors:
            raise InvalidPasswordException(reason=" ".join(errors))

    async def create(
        self,
        user_create: schemas.BaseUserCreate,
        safe: bool = False,
        request: Request | None = None,
    ) -> User:
        await self.validate_password(user_create.password, user_create)

        existing_user = await self.user_db.get_by_email(user_create.email)
        if existing_user is not None:
            raise exceptions.UserAlreadyExists()

        user_dict = (
            user_create.create_update_dict()
            if safe
            else user_create.create_update_dict_superuser()
        )
        password = user_dict.pop("password")
        user_dict["hashed_password"] = self.password_helper.hash(password)

        user_db = cast(SQLAlchemyUserDatabase, self.user_db)
        session = user_db.session
        organization_name = _build_organization_name_from_email(user_create.email)
        organization_slug = await _build_unique_organization_slug(
            session,
            user_create.email,
        )
        organization = Organization(
            name=organization_name,
            slug=organization_slug,
        )

        user = user_db.user_table(**user_dict)
        user.organization = organization
        if user.role is None:
            user.role = "owner"

        try:
            session.add(organization)
            session.add(user)
            await session.commit()
        except Exception:
            await session.rollback()
            raise

        await session.refresh(user)
        await self.on_after_register(user, request)
        return user

    async def on_after_register(self, user: User, request: Request | None = None):
        """Hook called after user registration."""
        logger.info("User %s has registered.", user.id)
        await self.request_verify(user, request)

    async def on_after_forgot_password(self, user: User, token: str, request: Request | None = None):
        """Hook called after password reset request."""
        logger.info("User %s has requested a password reset.", user.id)
        await send_reset_password_email(user.email, token)

    async def on_after_request_verify(self, user: User, token: str, request: Request | None = None):
        """Hook called after email verification request."""
        logger.info("User %s has requested email verification.", user.id)
        await send_verify_email(user.email, token)
        mark_verify_email_sent(user.id)


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    """Get user manager instance."""
    yield UserManager(user_db)


cookie_transport = CookieTransport(
    cookie_name="auth",
    cookie_max_age=3600,
    cookie_secure=settings.ENVIRONMENT == "production",
    cookie_httponly=True,
    cookie_samesite="lax",
)


def get_jwt_strategy() -> JWTStrategy:
    """Get JWT strategy."""
    return JWTStrategy(secret=settings.SECRET_KEY, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

current_active_user = fastapi_users.current_user(active=True)
