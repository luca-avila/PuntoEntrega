import logging
import re
import uuid
import hashlib
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
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db import get_async_session
from features.auth.models import User
from features.notifications.outbox import (
    EVENT_AUTH_PASSWORD_RESET_REQUESTED,
    EVENT_AUTH_VERIFY_EMAIL_REQUESTED,
    enqueue_notification_event,
)

logger = logging.getLogger(__name__)
VERIFY_EMAIL_TOKEN_LIFETIME_SECONDS = 3600
RESET_PASSWORD_TOKEN_LIFETIME_SECONDS = 3600
VERIFY_EMAIL_RESEND_COOLDOWN_SECONDS = 3600
_account_verification_last_sent_at: dict[uuid.UUID, datetime] = {}


def _cleanup_account_verification_send_tracker(now: datetime) -> None:
    cutoff = now - timedelta(seconds=VERIFY_EMAIL_RESEND_COOLDOWN_SECONDS)
    stale_user_ids = [
        user_id
        for user_id, sent_at in _account_verification_last_sent_at.items()
        if sent_at < cutoff
    ]
    for user_id in stale_user_ids:
        _account_verification_last_sent_at.pop(user_id, None)


def mark_account_verification_email_sent(user_id: uuid.UUID) -> None:
    now = datetime.now(UTC)
    _cleanup_account_verification_send_tracker(now)
    _account_verification_last_sent_at[user_id] = now


def can_send_account_verification_email(user_id: uuid.UUID) -> bool:
    now = datetime.now(UTC)
    _cleanup_account_verification_send_tracker(now)
    last_sent_at = _account_verification_last_sent_at.get(user_id)
    if last_sent_at is None:
        return True
    return now - last_sent_at >= timedelta(seconds=VERIFY_EMAIL_RESEND_COOLDOWN_SECONDS)


async def maybe_resend_account_verification_email_for_unverified_login(
    user_manager: BaseUserManager[User, uuid.UUID],
    user: User,
    request: Request,
) -> bool:
    """Resend the account verification email if the cooldown window has passed."""
    if user.is_verified:
        return False
    if not can_send_account_verification_email(user.id):
        return False

    await user_manager.request_verify(user, request)
    return True


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    """Provide the SQLAlchemy user repository used by FastAPI Users."""
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """PuntoEntrega account manager with product-specific password validation."""

    reset_password_token_secret = settings.SECRET_KEY
    verification_token_secret = settings.SECRET_KEY
    verification_token_lifetime_seconds = VERIFY_EMAIL_TOKEN_LIFETIME_SECONDS

    async def validate_password(self, password: str, user: Any) -> None:
        """Validate password strength."""
        errors = []

        if len(password) < settings.PASSWORD_MIN_LENGTH:
            errors.append(f"La contraseña debe tener al menos {settings.PASSWORD_MIN_LENGTH} caracteres.")

        if settings.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
            errors.append("La contraseña debe incluir al menos una mayúscula.")

        if settings.PASSWORD_REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
            errors.append("La contraseña debe incluir al menos una minúscula.")

        if settings.PASSWORD_REQUIRE_DIGIT and not re.search(r"\d", password):
            errors.append("La contraseña debe incluir al menos un número.")

        if settings.PASSWORD_REQUIRE_SPECIAL and not re.search(r"[^A-Za-z0-9]", password):
            errors.append("La contraseña debe incluir al menos un símbolo.")

        if hasattr(user, "email") and user.email:
            email_username = user.email.split("@")[0].lower()
            if email_username in password.lower():
                errors.append("La contraseña no debe contener el usuario de tu email.")

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
        user = user_db.user_table(**user_dict)

        try:
            session.add(user)
            await session.commit()
        except Exception:
            await session.rollback()
            raise

        await session.refresh(user)
        await self.on_after_register(user, request)
        return user

    async def on_after_register(self, user: User, request: Request | None = None):
        """Request account verification after registration."""
        logger.info("User %s has registered.", user.id)
        await self.request_verify(user, request)

    async def on_after_forgot_password(self, user: User, token: str, request: Request | None = None):
        """Queue a password reset email after a reset request."""
        logger.info("User %s has requested a password reset.", user.id)
        try:
            user_db = cast(SQLAlchemyUserDatabase, self.user_db)
            await enqueue_notification_event(
                user_db.session,
                event_type=EVENT_AUTH_PASSWORD_RESET_REQUESTED,
                aggregate_type="user",
                aggregate_id=user.id,
                organization_id=None,
                payload={"user_id": str(user.id), "email": user.email, "token": token},
                deduplication_key=(
                    f"user:{user.id}:password_reset:"
                    f"{hashlib.sha256(token.encode('utf-8')).hexdigest()}:"
                    f"{uuid.uuid4()}"
                ),
            )
            await user_db.session.commit()
        except Exception as exc:
            user_db = cast(SQLAlchemyUserDatabase, self.user_db)
            await user_db.session.rollback()
            logger.exception(
                "Failed to enqueue password reset email: user_id=%s email=%s error=%s",
                user.id,
                user.email,
                exc,
            )

    async def on_after_request_verify(self, user: User, token: str, request: Request | None = None):
        """Queue an account verification email."""
        logger.info("User %s has requested email verification.", user.id)
        try:
            user_db = cast(SQLAlchemyUserDatabase, self.user_db)
            await enqueue_notification_event(
                user_db.session,
                event_type=EVENT_AUTH_VERIFY_EMAIL_REQUESTED,
                aggregate_type="user",
                aggregate_id=user.id,
                organization_id=None,
                payload={"user_id": str(user.id), "email": user.email, "token": token},
                deduplication_key=(
                    f"user:{user.id}:verify_email:"
                    f"{hashlib.sha256(token.encode('utf-8')).hexdigest()}:"
                    f"{uuid.uuid4()}"
                ),
            )
            await user_db.session.commit()
        except Exception as exc:
            user_db = cast(SQLAlchemyUserDatabase, self.user_db)
            await user_db.session.rollback()
            logger.exception(
                "Failed to enqueue verification email: user_id=%s email=%s error=%s",
                user.id,
                user.email,
                exc,
            )
            return
        mark_account_verification_email_sent(user.id)


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    """Provide the account manager used by auth routes."""
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
