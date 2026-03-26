import enum
import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from features.invitations.models import InvitationStatus

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class OrganizationInvitationCreate(BaseModel):
    email: str = Field(max_length=320)
    location_id: uuid.UUID

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("El email es obligatorio.")
        if not EMAIL_PATTERN.fullmatch(normalized):
            raise ValueError("Ingresá un email válido.")
        return normalized


class OrganizationInvitationRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    invited_email: str
    invited_by_user_id: uuid.UUID
    location_id: uuid.UUID | None
    status: InvitationStatus
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvitationAcceptInfoStatus(str, enum.Enum):
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    ACCEPTED = "accepted"


class OrganizationInvitationAcceptInfoRead(BaseModel):
    status: InvitationAcceptInfoStatus
    is_valid: bool
    invited_email: str | None = None
    organization_id: uuid.UUID | None = None
    organization_name: str | None = None
    location_id: uuid.UUID | None = None
    expires_at: datetime | None = None


class OrganizationInvitationAcceptCreate(BaseModel):
    token: str = Field(min_length=1)
    password: str = Field(min_length=1)
    password_confirm: str = Field(min_length=1)

    @field_validator("token")
    @classmethod
    def normalize_token(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El token es obligatorio.")
        return normalized

    @model_validator(mode="after")
    def validate_password_confirmation(self) -> "OrganizationInvitationAcceptCreate":
        if self.password != self.password_confirm:
            raise ValueError("Las contraseñas no coinciden.")
        return self


class OrganizationInvitationAcceptAuthenticated(BaseModel):
    token: str = Field(min_length=1)

    @field_validator("token")
    @classmethod
    def normalize_token(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El token es obligatorio.")
        return normalized


class OrganizationInvitationAcceptResult(BaseModel):
    invitation_id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    invited_email: str
