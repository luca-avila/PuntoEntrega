import type { LoginRequest, RegisterRequest, SessionUser } from "@/api/contracts/auth";
import { apiRequest } from "@/api/http-client";

export const authApi = {
  getSession(): Promise<SessionUser> {
    return apiRequest<SessionUser>("/users/me");
  },

  register(payload: RegisterRequest): Promise<SessionUser> {
    return apiRequest<SessionUser>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
    });
  },

  verifyEmail(token: string): Promise<SessionUser> {
    return apiRequest<SessionUser>("/auth/verify", {
      method: "POST",
      body: JSON.stringify({ token }),
      headers: {
        "Content-Type": "application/json",
      },
    });
  },

  login(payload: LoginRequest): Promise<void> {
    const form = new URLSearchParams({
      username: payload.email,
      password: payload.password,
    });

    return apiRequest<void>("/auth/jwt/login", {
      method: "POST",
      body: form.toString(),
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });
  },

  logout(): Promise<void> {
    return apiRequest<void>("/auth/jwt/logout", {
      method: "POST",
    });
  },
};
