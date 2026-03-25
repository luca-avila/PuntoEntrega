import type { LoginRequest, SessionUser } from "@/api/contracts/auth";
import type { OrganizationRead } from "@/api/contracts/organizations";
import { createContext } from "react";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export interface AuthContextValue {
  user: SessionUser | null;
  organization: OrganizationRead | null;
  isOwner: boolean;
  status: AuthStatus;
  login: (payload: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
  refreshOrganization: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);
