import type {
  ProductRequestCreateRequest,
  ListProductRequestsParams,
  ProductRequestRead,
} from "@/api/contracts/product-requests";
import { apiRequest } from "@/api/http-client";
import { buildQueryParams } from "@/api/query-params";

export const productRequestsApi = {
  create(payload: ProductRequestCreateRequest): Promise<ProductRequestRead> {
    return apiRequest<ProductRequestRead>("/product-requests", {
      method: "POST",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
    });
  },

  list(params: ListProductRequestsParams = {}): Promise<ProductRequestRead[]> {
    const query = buildQueryParams({
      requested_for_location_id: params.requested_for_location_id,
      created_from: params.created_from,
      created_to: params.created_to,
    });

    return apiRequest<ProductRequestRead[]>(`/product-requests${query}`);
  },
};
