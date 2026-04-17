import uuid
import re
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from features.deliveries.models import PaymentMethod


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class DeliveryItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: Decimal = Field(gt=0)


class DeliveryCreate(BaseModel):
    location_id: uuid.UUID
    delivered_at: datetime
    payment_method: PaymentMethod
    payment_notes: str | None = None
    observations: str | None = None
    summary_recipient_email: str = Field(max_length=320)
    items: list[DeliveryItemCreate] = Field(min_length=1)

    @field_validator("payment_notes", "observations", mode="before")
    @classmethod
    def normalize_optional_text_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            return None

        return normalized

    @field_validator("summary_recipient_email")
    @classmethod
    def normalize_summary_recipient_email(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El email destinatario del resumen es obligatorio.")
        if not EMAIL_PATTERN.fullmatch(normalized):
            raise ValueError("Ingresá un email destinatario válido.")
        return normalized

    @model_validator(mode="after")
    def validate_no_duplicate_products(self) -> "DeliveryCreate":
        seen_product_ids: set[uuid.UUID] = set()

        for item in self.items:
            if item.product_id in seen_product_ids:
                raise ValueError("No repitas el mismo producto en varias líneas.")
            seen_product_ids.add(item.product_id)

        return self


class DeliveryItemRead(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    quantity: Decimal

    model_config = ConfigDict(from_attributes=True)


class DeliveryRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    location_id: uuid.UUID
    location_name: str | None = None
    location_address: str | None = None
    delivered_at: datetime
    payment_method: PaymentMethod
    payment_notes: str | None
    observations: str | None
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
