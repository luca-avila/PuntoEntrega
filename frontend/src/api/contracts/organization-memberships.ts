import type { UUID } from "@/api/contracts/common";

export type OrganizationMembershipRole = "owner" | "member";

export interface OrganizationMembershipCurrentRead {
  organization_id: UUID;
  organization_name: string;
  role: OrganizationMembershipRole;
  location_id: UUID | null;
}
