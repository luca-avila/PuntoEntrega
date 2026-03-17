import type {
  LocationCreateRequest,
  LocationRead,
  LocationUpdateRequest,
} from "@/api/contracts/locations";
import { apiRequest } from "@/api/http-client";

export const locationsApi = {
  list(): Promise<LocationRead[]> {
    return apiRequest<LocationRead[]>("/locations");
  },

  getById(locationId: string): Promise<LocationRead> {
    return apiRequest<LocationRead>(`/locations/${locationId}`);
  },

  create(payload: LocationCreateRequest): Promise<LocationRead> {
    return apiRequest<LocationRead>("/locations", {
      method: "POST",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
    });
  },

  update(locationId: string, payload: LocationUpdateRequest): Promise<LocationRead> {
    return apiRequest<LocationRead>(`/locations/${locationId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
    });
  },
};
