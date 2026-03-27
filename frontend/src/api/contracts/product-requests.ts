import type { ISODateTime, UUID } from "@/api/contracts/common";

export type ProductRequestEmailStatus = "pending" | "sent" | "failed";

export interface ProductRequestItemCreateRequest {
  product_id: UUID;
  quantity: string;
}

export interface ProductRequestItemRead {
  id: UUID;
  product_id: UUID;
  quantity: string;
}

export interface ProductRequestCreateRequest {
  subject: string;
  message?: string;
  items: ProductRequestItemCreateRequest[];
}

export interface ProductRequestRead {
  id: UUID;
  organization_id: UUID;
  requested_by_user_id: UUID;
  requested_for_location_id: UUID | null;
  requested_for_location_name: string | null;
  requested_for_location_address: string | null;
  subject: string;
  message: string | null;
  items: ProductRequestItemRead[];
  email_status: ProductRequestEmailStatus;
  email_attempts: number;
  email_last_error: string | null;
  email_sent_at: ISODateTime | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface ListProductRequestsParams {
  requested_for_location_id?: UUID;
  created_from?: ISODateTime;
  created_to?: ISODateTime;
}
