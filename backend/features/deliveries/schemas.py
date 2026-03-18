import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from features.deliveries.models import EmailStatus, PaymentMethod


class DeliveryItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: Decimal = Field(gt=0)


class DeliveryCreate(BaseModel):
    location_id: uuid.UUID
    delivered_at: datetime
    payment_method: PaymentMethod
    payment_notes: str | None = None
    observations: str | None = None
    summary_recipient_email: str | None = None
    items: list[DeliveryItemCreate] = Field(min_length=1)

    @field_validator("summary_recipient_email")
    @classmethod
    def normalize_summary_recipient_email(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None


class DeliveryItemRead(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    quantity: Decimal

    model_config = ConfigDict(from_attributes=True)


class DeliveryRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    location_id: uuid.UUID
    delivered_at: datetime
    payment_method: PaymentMethod
    payment_notes: str | None
    observations: str | None
    email_status: EmailStatus
    created_at: datetime
    updated_at: datetime
    items: list[DeliveryItemRead]

    model_config = ConfigDict(from_attributes=True)


class DeliveryListFilters(BaseModel):
    location_id: uuid.UUID | None = None
    delivered_from: datetime | None = None
    delivered_to: datetime | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> "DeliveryListFilters":
        if (
            self.delivered_from is not None
            and self.delivered_to is not None
            and self.delivered_from > self.delivered_to
        ):
            raise ValueError("La fecha desde debe ser menor o igual a la fecha hasta.")
        return self
