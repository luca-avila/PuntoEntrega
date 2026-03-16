import uuid

from fastapi_users import schemas


class UserRead(schemas.BaseUser[uuid.UUID]):
    """User read schema - returned from API."""

    pass


class UserCreate(schemas.BaseUserCreate):
    """User creation schema - for registration."""

    pass


class UserUpdate(schemas.BaseUserUpdate):
    """User update schema - for patches."""

    pass
