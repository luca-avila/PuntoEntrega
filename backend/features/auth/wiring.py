from fastapi import FastAPI

from features.auth.api.routes import (
    get_auth_jwt_router,
    get_auth_register_router,
    get_auth_reset_password_router,
    get_auth_verify_router,
    get_users_router,
)


def include_auth_routers(app: FastAPI) -> None:
    app.include_router(get_auth_jwt_router(), prefix="/auth/jwt", tags=["auth"])
    app.include_router(get_auth_register_router(), prefix="/auth", tags=["auth"])
    app.include_router(get_auth_verify_router(), prefix="/auth", tags=["auth"])
    app.include_router(get_auth_reset_password_router(), prefix="/auth", tags=["auth"])
    app.include_router(get_users_router(), prefix="/users", tags=["users"])
