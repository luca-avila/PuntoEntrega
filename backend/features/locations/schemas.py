import uuid
import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_PATTERN = re.compile(r"^[0-9+\-()\s]+$")


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    return normalized


class LocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str = Field(min_length=1, max_length=500)
    contact_name: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=50)
    contact_email: str | None = Field(default=None, max_length=320)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    notes: str | None = None

    @field_validator("name", "address")
    @classmethod
    def normalize_required_text(cls, value: str, info: ValidationInfo) -> str:
        normalized = value.strip()
        if normalized:
            return normalized

        if info.field_name == "name":
            raise ValueError("El nombre es obligatorio.")
        raise ValueError("La dirección es obligatoria.")

    @field_validator("contact_name", "contact_phone", "contact_email", "notes", mode="before")
    @classmethod
    def normalize_optional_fields(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Ingresá un email de contacto válido.")
        return value

    @field_validator("contact_phone")
    @classmethod
    def validate_contact_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not PHONE_PATTERN.fullmatch(value) or not any(char.isdigit() for char in value):
            raise ValueError("Ingresá un teléfono de contacto válido.")
        return value


class LocationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = Field(default=None, min_length=1, max_length=500)
    contact_name: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=50)
    contact_email: str | None = Field(default=None, max_length=320)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    notes: str | None = None

    @field_validator("name", "address")
    @classmethod
    def normalize_optional_required_text(
        cls,
        value: str | None,
        info: ValidationInfo,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        if normalized:
            return normalized

        if info.field_name == "name":
            raise ValueError("El nombre no puede estar vacío.")
        raise ValueError("La dirección no puede estar vacía.")

    @field_validator("contact_name", "contact_phone", "contact_email", "notes", mode="before")
    @classmethod
    def normalize_optional_fields(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Ingresá un email de contacto válido.")
        return value

    @field_validator("contact_phone")
    @classmethod
    def validate_contact_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not PHONE_PATTERN.fullmatch(value) or not any(char.isdigit() for char in value):
            raise ValueError("Ingresá un teléfono de contacto válido.")
        return value

    @model_validator(mode="after")
    def validate_non_empty_payload(self) -> "LocationUpdate":
        if not self.model_fields_set:
            raise ValueError("Debe enviar al menos un campo para actualizar.")
        return self


class LocationRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    address: str
    contact_name: str | None
    contact_phone: str | None
    contact_email: str | None
    latitude: float
    longitude: float
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
