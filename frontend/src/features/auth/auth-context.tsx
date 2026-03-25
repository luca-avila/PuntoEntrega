import { authApi } from "@/api/auth-api";
import { organizationsApi } from "@/api/organizations-api";
import { ApiError, setUnauthorizedHandler } from "@/api/http-client";
import {
  AuthContext,
  type AuthContextValue,
  type AuthStatus,
} from "@/features/auth/auth-context-store";
import type { LoginRequest, SessionUser } from "@/api/contracts/auth";
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
  const [organization, setOrganization] = useState<OrganizationRead | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");

  const fetchOrganizationForUser = useCallback(
    async (sessionUser: SessionUser): Promise<OrganizationRead | null> => {
      if (!sessionUser.organization_id) {
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
      const currentOrganization = await fetchOrganizationForUser(currentUser);
      setUser(currentUser);
      setOrganization(currentOrganization);
      setStatus("authenticated");
    } catch (error) {
      if (!isUnauthorizedError(error)) {
        console.error("No se pudo recuperar la sesión activa.", error);
      }
      setUser(null);
      setOrganization(null);
      setStatus("unauthenticated");
    }
  }, [fetchOrganizationForUser]);

  const refreshOrganization = useCallback(async () => {
    if (!user) {
      setOrganization(null);
      return;
    }

    const currentOrganization = await fetchOrganizationForUser(user);
    setOrganization(currentOrganization);
  }, [fetchOrganizationForUser, user]);

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
      setOrganization(null);
      setStatus("unauthenticated");
    });

    return () => {
      setUnauthorizedHandler(null);
    };
  }, []);

  const isOwner = Boolean(user && organization && organization.owner_user_id === user.id);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      organization,
      isOwner,
      status,
      login,
      logout,
      refreshSession,
      refreshOrganization,
    }),
    [user, organization, isOwner, status, login, logout, refreshSession, refreshOrganization],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
