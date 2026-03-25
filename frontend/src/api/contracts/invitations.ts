import type { ISODateTime, UUID } from "@/api/contracts/common";

export type OrganizationInvitationStatus =
  | "pending"
  | "accepted"
  | "expired"
  | "cancelled";

export interface OrganizationInvitationCreateRequest {
  email: string;
}

export interface OrganizationInvitationRead {
  id: UUID;
  organization_id: UUID;
  invited_email: string;
  invited_by_user_id: UUID;
  status: OrganizationInvitationStatus;
  expires_at: ISODateTime;
  accepted_at: ISODateTime | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export type InvitationAcceptInfoStatus =
  | "valid"
  | "invalid"
  | "expired"
  | "cancelled"
  | "accepted";

export interface OrganizationInvitationAcceptInfoRead {
  status: InvitationAcceptInfoStatus;
  is_valid: boolean;
  invited_email: string | null;
  organization_id: UUID | null;
  organization_name: string | null;
  expires_at: ISODateTime | null;
}

export interface OrganizationInvitationAcceptCreateRequest {
  token: string;
  password: string;
  password_confirm: string;
}

export interface OrganizationInvitationAcceptAuthenticatedRequest {
  token: string;
}

export interface OrganizationInvitationAcceptResult {
  invitation_id: UUID;
  organization_id: UUID;
  user_id: UUID;
  invited_email: string;
}
