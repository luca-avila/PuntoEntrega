import { authApi } from "@/api/auth-api";
import { ApiError } from "@/api/http-client";
import {
  AuthContext,
  type AuthContextValue,
  type AuthStatus,
} from "@/features/auth/auth-context-store";
import type { LoginRequest, SessionUser } from "@/api/contracts/auth";
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
  const [status, setStatus] = useState<AuthStatus>("loading");

  const refreshSession = useCallback(async () => {
    setStatus("loading");
    try {
      const currentUser = await authApi.getSession();
      setUser(currentUser);
      setStatus("authenticated");
    } catch (error) {
      if (!isUnauthorizedError(error)) {
        console.error("No se pudo recuperar la sesión activa.", error);
      }
      setUser(null);
      setStatus("unauthenticated");
    }
  }, []);

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
      setStatus("unauthenticated");
    }
  }, []);

  useEffect(() => {
    void refreshSession();
  }, [refreshSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      login,
      logout,
      refreshSession,
    }),
    [user, status, login, logout, refreshSession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
