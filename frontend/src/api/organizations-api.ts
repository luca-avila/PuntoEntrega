import type {
  OrganizationCreate,
  OrganizationMembershipCurrentRead,
  OrganizationRead,
} from "@/api/contracts";
import { apiRequest } from "@/api/http-client";

export const organizationsApi = {
  create(payload: OrganizationCreate): Promise<OrganizationRead> {
    return apiRequest<OrganizationRead>("/organizations", {
      method: "POST",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
    });
  },

  getCurrent(): Promise<OrganizationRead> {
    return apiRequest<OrganizationRead>("/organizations/current");
  },

  getCurrentMembership(): Promise<OrganizationMembershipCurrentRead> {
    return apiRequest<OrganizationMembershipCurrentRead>("/organization-memberships/current");
  },
};
