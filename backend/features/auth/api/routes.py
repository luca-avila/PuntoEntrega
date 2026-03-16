import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users.authentication import Strategy
from fastapi_users.manager import BaseUserManager
from fastapi_users.openapi import OpenAPIResponseType
from fastapi_users.router.common import ErrorCode, ErrorModel

from features.auth.models import User
from features.auth.schemas import UserCreate, UserRead, UserUpdate
from features.auth.service import (
    auth_backend,
    fastapi_users,
    get_user_manager,
    maybe_resend_verify_email_for_unverified_login,
)


def get_auth_jwt_router() -> APIRouter:
    router = APIRouter()
    get_current_user_token = fastapi_users.authenticator.current_user_token(
        active=True,
        verified=True,
    )

    login_responses: OpenAPIResponseType = {
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorModel,
            "content": {
                "application/json": {
                    "examples": {
                        ErrorCode.LOGIN_BAD_CREDENTIALS: {
                            "summary": "Bad credentials or the user is inactive.",
                            "value": {"detail": ErrorCode.LOGIN_BAD_CREDENTIALS},
                        },
                        ErrorCode.LOGIN_USER_NOT_VERIFIED: {
                            "summary": "The user is not verified.",
                            "value": {"detail": ErrorCode.LOGIN_USER_NOT_VERIFIED},
                        },
                    }
                }
            },
        },
        **auth_backend.transport.get_openapi_login_responses_success(),
    }

    @router.post(
        "/login",
        name=f"auth:{auth_backend.name}.login",
        responses=login_responses,
    )
    async def login(
        request: Request,
        credentials: OAuth2PasswordRequestForm = Depends(),
        user_manager: BaseUserManager[User, uuid.UUID] = Depends(get_user_manager),
        strategy: Strategy = Depends(auth_backend.get_strategy),
    ):
        user = await user_manager.authenticate(credentials)

        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorCode.LOGIN_BAD_CREDENTIALS,
            )

        if not user.is_verified:
            await maybe_resend_verify_email_for_unverified_login(user_manager, user, request)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorCode.LOGIN_USER_NOT_VERIFIED,
            )

        response = await auth_backend.login(strategy, user)
        await user_manager.on_after_login(user, request, response)
        return response

    logout_responses: OpenAPIResponseType = {
        **{
            status.HTTP_401_UNAUTHORIZED: {
                "description": "Missing token or inactive user.",
            }
        },
        **auth_backend.transport.get_openapi_logout_responses_success(),
    }

    @router.post(
        "/logout",
        name=f"auth:{auth_backend.name}.logout",
        responses=logout_responses,
    )
    async def logout(
        user_token: tuple[User, str] = Depends(get_current_user_token),
        strategy: Strategy = Depends(auth_backend.get_strategy),
    ):
        user, token = user_token
        return await auth_backend.logout(strategy, user, token)

    return router


def get_auth_register_router() -> APIRouter:
    return fastapi_users.get_register_router(UserRead, UserCreate)


def get_auth_verify_router() -> APIRouter:
    return fastapi_users.get_verify_router(UserRead)


def get_auth_reset_password_router() -> APIRouter:
    return fastapi_users.get_reset_password_router()


def get_users_router() -> APIRouter:
    return fastapi_users.get_users_router(UserRead, UserUpdate)
