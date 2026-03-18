import type { DecimalValue, ISODateTime, UUID } from "@/api/contracts/common";

export type PaymentMethod = "cash" | "transfer" | "current_account" | "other";

export type EmailStatus = "pending" | "sent" | "failed";

export interface DeliveryItemCreateRequest {
  product_id: UUID;
  quantity: DecimalValue;
}

export interface DeliveryCreateRequest {
  location_id: UUID;
  delivered_at: ISODateTime;
  payment_method: PaymentMethod;
  payment_notes?: string | null;
  observations?: string | null;
  summary_recipient_email: string;
  items: DeliveryItemCreateRequest[];
}

export interface DeliveryItemRead {
  id: UUID;
  product_id: UUID;
  quantity: DecimalValue;
}

export interface DeliveryRead {
  id: UUID;
  organization_id: UUID;
  location_id: UUID;
  delivered_at: ISODateTime;
  payment_method: PaymentMethod;
  payment_notes: string | null;
  observations: string | null;
  email_status: EmailStatus;
  created_at: ISODateTime;
  updated_at: ISODateTime;
  items: DeliveryItemRead[];
}

export interface ListDeliveriesParams {
  location_id?: UUID;
  delivered_from?: ISODateTime;
  delivered_to?: ISODateTime;
}
