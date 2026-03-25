import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El nombre de la organización es obligatorio.")
        return normalized


class OrganizationRead(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    owner_user_id: uuid.UUID
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class OrganizationMemberRead(BaseModel):
    id: uuid.UUID
    email: str
    is_active: bool
    is_verified: bool
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
