const DEFAULT_API_BASE_URL = "/api";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "") ?? DEFAULT_API_BASE_URL;
