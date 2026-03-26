import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from features.organizations.models import MembershipRole


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
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class OrganizationMemberRead(BaseModel):
    id: uuid.UUID
    email: str
    is_active: bool
    is_verified: bool
    location_id: uuid.UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationMembershipCurrentRead(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    role: MembershipRole
    location_id: uuid.UUID | None
