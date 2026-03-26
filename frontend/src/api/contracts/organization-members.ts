import type { ISODateTime, UUID } from "@/api/contracts/common";

export interface OrganizationMemberRead {
  id: UUID;
  email: string;
  is_active: boolean;
  is_verified: boolean;
  location_id: UUID | null;
  created_at: ISODateTime | null;
}
