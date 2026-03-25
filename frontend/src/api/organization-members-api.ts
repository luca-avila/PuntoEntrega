import type { OrganizationMemberRead } from "@/api/contracts/organization-members";
import { apiRequest } from "@/api/http-client";

export const organizationMembersApi = {
  list(): Promise<OrganizationMemberRead[]> {
    return apiRequest<OrganizationMemberRead[]>("/organization-members");
  },
};
