import type { ISODateTime, UUID } from "@/api/contracts/common";

export type ProductRequestEmailStatus = "pending" | "sent" | "failed";

export interface ProductRequestCreateRequest {
  subject: string;
  message: string;
}

export interface ProductRequestRead {
  id: UUID;
  organization_id: UUID;
  requested_by_user_id: UUID;
  subject: string;
  message: string;
  email_status: ProductRequestEmailStatus;
  email_attempts: number;
  email_last_error: string | null;
  email_sent_at: ISODateTime | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}
