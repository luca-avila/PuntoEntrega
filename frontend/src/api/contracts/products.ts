import type { ISODateTime, UUID } from "@/api/contracts/common";

export interface ProductRead {
  id: UUID;
  organization_id: UUID;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface ProductCreateRequest {
  name: string;
  description?: string | null;
  is_active?: boolean;
}

export interface ProductUpdateRequest {
  name?: string | null;
  description?: string | null;
  is_active?: boolean | null;
}

export interface ListProductsParams {
  active_only?: boolean;
}
