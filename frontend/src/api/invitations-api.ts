import type {
  OrganizationInvitationAcceptAuthenticatedRequest,
  OrganizationInvitationAcceptCreateRequest,
  OrganizationInvitationAcceptInfoRead,
  OrganizationInvitationAcceptResult,
  OrganizationInvitationCreateRequest,
  OrganizationInvitationRead,
} from "@/api/contracts/invitations";
import { apiRequest } from "@/api/http-client";
import { buildQueryParams } from "@/api/query-params";

export const invitationsApi = {
  create(payload: OrganizationInvitationCreateRequest): Promise<OrganizationInvitationRead> {
    return apiRequest<OrganizationInvitationRead>("/organization-invitations", {
      method: "POST",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
    });
  },

  list(): Promise<OrganizationInvitationRead[]> {
    return apiRequest<OrganizationInvitationRead[]>("/organization-invitations");
  },

  cancel(invitationId: string): Promise<OrganizationInvitationRead> {
    return apiRequest<OrganizationInvitationRead>(`/organization-invitations/${invitationId}/cancel`, {
      method: "POST",
    });
  },

  getAcceptInfo(token: string): Promise<OrganizationInvitationAcceptInfoRead> {
    const query = buildQueryParams({ token });
    return apiRequest<OrganizationInvitationAcceptInfoRead>(`/organization-invitations/accept-info${query}`);
  },

  acceptNewAccount(
    payload: OrganizationInvitationAcceptCreateRequest,
  ): Promise<OrganizationInvitationAcceptResult> {
    return apiRequest<OrganizationInvitationAcceptResult>("/organization-invitations/accept", {
      method: "POST",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
    });
  },

  acceptAuthenticated(
    payload: OrganizationInvitationAcceptAuthenticatedRequest,
  ): Promise<OrganizationInvitationAcceptResult> {
    return apiRequest<OrganizationInvitationAcceptResult>(
      "/organization-invitations/accept-authenticated",
      {
        method: "POST",
        body: JSON.stringify(payload),
        headers: {
          "Content-Type": "application/json",
        },
      },
    );
  },
};
