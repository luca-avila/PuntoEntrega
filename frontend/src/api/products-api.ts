import type {
  ListProductsParams,
  ProductCreateRequest,
  ProductRead,
  ProductUpdateRequest,
} from "@/api/contracts/products";
import { apiRequest } from "@/api/http-client";
import { buildQueryParams } from "@/api/query-params";

export const productsApi = {
  list(params: ListProductsParams = {}): Promise<ProductRead[]> {
    const query = buildQueryParams({ active_only: params.active_only });
    return apiRequest<ProductRead[]>(`/products${query}`);
  },

  getById(productId: string): Promise<ProductRead> {
    return apiRequest<ProductRead>(`/products/${productId}`);
  },

  create(payload: ProductCreateRequest): Promise<ProductRead> {
    return apiRequest<ProductRead>("/products", {
      method: "POST",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
    });
  },

  update(productId: string, payload: ProductUpdateRequest): Promise<ProductRead> {
    return apiRequest<ProductRead>(`/products/${productId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
      },
    });
  },
};
