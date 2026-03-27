import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from features.product_requests.models import ProductRequestEmailStatus


class ProductRequestItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: Decimal = Field(gt=0)


class ProductRequestItemRead(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    quantity: Decimal

    model_config = ConfigDict(from_attributes=True)


class ProductRequestCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=255)
    message: str | None = None
    items: list[ProductRequestItemCreate] = Field(min_length=1)

    @field_validator("subject")
    @classmethod
    def normalize_subject(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El asunto es obligatorio.")
        return normalized

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized

    @model_validator(mode="after")
    def validate_no_duplicate_products(self) -> "ProductRequestCreate":
        seen_product_ids: set[uuid.UUID] = set()
        for item in self.items:
            if item.product_id in seen_product_ids:
                raise ValueError("No repitas el mismo producto en varias líneas.")
            seen_product_ids.add(item.product_id)
        return self


class ProductRequestRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    requested_by_user_id: uuid.UUID
    requested_for_location_id: uuid.UUID | None
    requested_for_location_name: str | None = None
    requested_for_location_address: str | None = None
    subject: str
    message: str | None
    items: list[ProductRequestItemRead]
    email_status: ProductRequestEmailStatus
    email_attempts: int
    email_last_error: str | None
    email_sent_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductRequestListFilters(BaseModel):
    requested_for_location_id: uuid.UUID | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> "ProductRequestListFilters":
        if (
            self.created_from is not None
            and self.created_to is not None
            and self.created_from > self.created_to
        ):
            raise ValueError("La fecha desde debe ser menor o igual a la fecha hasta.")
        return self
