import type {
  DeliveryCreateRequest,
  DeliveryRead,
  ListDeliveriesParams,
} from "@/api/contracts/deliveries";
import { apiRequest } from "@/api/http-client";
import { buildQueryParams } from "@/api/query-params";

export const deliveriesApi = {
  list(params: ListDeliveriesParams = {}): Promise<DeliveryRead[]> {
    const query = buildQueryParams({
      location_id: params.location_id,
      delivered_from: params.delivered_from,
      delivered_to: params.delivered_to,
    });

    return apiRequest<DeliveryRead[]>(`/deliveries${query}`);
  },

  getById(deliveryId: string): Promise<DeliveryRead> {
    return apiRequest<DeliveryRead>(`/deliveries/${deliveryId}`);
  },

  create(payload: DeliveryCreateRequest): Promise<DeliveryRead> {
    return apiRequest<DeliveryRead>("/deliveries", {
      method: "POST",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
    });
  },
};
