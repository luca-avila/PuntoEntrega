import type { ISODateTime, UUID } from "@/api/contracts/common";

export interface LocationRead {
  id: UUID;
  organization_id: UUID;
  name: string;
  address: string;
  contact_name: string | null;
  contact_phone: string | null;
  contact_email: string | null;
  latitude: number;
  longitude: number;
  notes: string | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface LocationCreateRequest {
  name: string;
  address: string;
  contact_name?: string | null;
  contact_phone?: string | null;
  contact_email?: string | null;
  latitude: number;
  longitude: number;
  notes?: string | null;
}

export interface LocationUpdateRequest {
  name?: string | null;
  address?: string | null;
  contact_name?: string | null;
  contact_phone?: string | null;
  contact_email?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  notes?: string | null;
}
