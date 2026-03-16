import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str = Field(min_length=1, max_length=500)
    contact_name: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=50)
    contact_email: str | None = Field(default=None, max_length=320)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    notes: str | None = None


class LocationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = Field(default=None, min_length=1, max_length=500)
    contact_name: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=50)
    contact_email: str | None = Field(default=None, max_length=320)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_non_empty_payload(self) -> "LocationUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
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

