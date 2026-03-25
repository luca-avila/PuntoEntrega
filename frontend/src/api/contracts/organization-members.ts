import type { ISODateTime, UUID } from "@/api/contracts/common";

export interface OrganizationMemberRead {
  id: UUID;
  email: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: ISODateTime | null;
}
