import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from features.product_requests.models import ProductRequestEmailStatus


class ProductRequestCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=10)

    @field_validator("subject")
    @classmethod
    def normalize_subject(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El asunto es obligatorio.")
        return normalized

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El mensaje es obligatorio.")
        if len(normalized) < 10:
            raise ValueError("El mensaje debe tener al menos 10 caracteres.")
        return normalized


class ProductRequestRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    requested_by_user_id: uuid.UUID
    requested_for_location_id: uuid.UUID | None
    subject: str
    message: str
    email_status: ProductRequestEmailStatus
    email_attempts: int
    email_last_error: str | None
    email_sent_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
