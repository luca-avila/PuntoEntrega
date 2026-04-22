import uuid

from fastapi_users import schemas


class UserRead(schemas.BaseUser[uuid.UUID]):
    """Authenticated account returned by the API."""
    pass


class UserCreate(schemas.BaseUserCreate):
    """Payload used to create a PuntoEntrega account."""

    pass


class UserUpdate(schemas.BaseUserUpdate):
    """Payload used to update account data."""

    pass
