import { authApi } from "@/api/auth-api";
import { organizationsApi } from "@/api/organizations-api";
import { ApiError, setUnauthorizedHandler } from "@/api/http-client";
import {
  AuthContext,
  type AuthContextValue,
  type AuthStatus,
} from "@/features/auth/auth-context-store";
import type { LoginRequest, SessionUser } from "@/api/contracts/auth";
import type { OrganizationMembershipCurrentRead } from "@/api/contracts/organization-memberships";
import type { OrganizationRead } from "@/api/contracts/organizations";
import {
  type PropsWithChildren,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

function isUnauthorizedError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [membership, setMembership] = useState<OrganizationMembershipCurrentRead | null>(null);
  const [organization, setOrganization] = useState<OrganizationRead | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");

  const fetchMembershipForUser = useCallback(async (): Promise<OrganizationMembershipCurrentRead | null> => {
    try {
      return await organizationsApi.getCurrentMembership();
    } catch (error) {
      if (isUnauthorizedError(error)) {
        throw error;
      }

      if (error instanceof ApiError && (error.status === 403 || error.status === 404)) {
        return null;
      }

      console.error("No se pudo recuperar la membresía actual.", error);
      return null;
    }
  }, []);

  const fetchOrganizationForMembership = useCallback(
    async (currentMembership: OrganizationMembershipCurrentRead | null): Promise<OrganizationRead | null> => {
      if (!currentMembership) {
        return null;
      }

      try {
        return await organizationsApi.getCurrent();
      } catch (error) {
        if (isUnauthorizedError(error)) {
          throw error;
        }

        if (error instanceof ApiError && (error.status === 403 || error.status === 404)) {
          return null;
        }

        console.error("No se pudo recuperar la organización actual.", error);
        return null;
      }
    },
    [],
  );

  const refreshSession = useCallback(async () => {
    setStatus("loading");
    try {
      const currentUser = await authApi.getSession();
      const currentMembership = await fetchMembershipForUser();
      const currentOrganization = await fetchOrganizationForMembership(currentMembership);
      setUser(currentUser);
      setMembership(currentMembership);
      setOrganization(currentOrganization);
      setStatus("authenticated");
    } catch (error) {
      if (!isUnauthorizedError(error)) {
        console.error("No se pudo recuperar la sesión activa.", error);
      }
      setUser(null);
      setMembership(null);
      setOrganization(null);
      setStatus("unauthenticated");
    }
  }, [fetchMembershipForUser, fetchOrganizationForMembership]);

  const refreshOrganization = useCallback(async () => {
    if (!user) {
      setMembership(null);
      setOrganization(null);
      return;
    }

    const currentMembership = await fetchMembershipForUser();
    const currentOrganization = await fetchOrganizationForMembership(currentMembership);
    setMembership(currentMembership);
    setOrganization(currentOrganization);
  }, [fetchMembershipForUser, fetchOrganizationForMembership, user]);

  const login = useCallback(
    async (payload: LoginRequest) => {
      await authApi.login(payload);
      await refreshSession();
    },
    [refreshSession],
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
      setMembership(null);
      setOrganization(null);
      setStatus("unauthenticated");
    }
  }, []);

  useEffect(() => {
    void refreshSession();
  }, [refreshSession]);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null);
      setMembership(null);
      setOrganization(null);
      setStatus("unauthenticated");
    });

    return () => {
      setUnauthorizedHandler(null);
    };
  }, []);

  const isOwner = membership?.role === "owner";

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      membership,
      organization,
      isOwner,
      status,
      login,
      logout,
      refreshSession,
      refreshOrganization,
    }),
    [
      user,
      membership,
      organization,
      isOwner,
      status,
      login,
      logout,
      refreshSession,
      refreshOrganization,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
