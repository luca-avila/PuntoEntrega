export interface SessionUser {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  organization_id: string | null;
  role: string | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}
