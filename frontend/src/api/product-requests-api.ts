import type {
  ProductRequestCreateRequest,
  ProductRequestRead,
} from "@/api/contracts/product-requests";
import { apiRequest } from "@/api/http-client";

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

  list(): Promise<ProductRequestRead[]> {
    return apiRequest<ProductRequestRead[]>("/product-requests");
  },
};
