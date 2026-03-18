import { ApiError } from "@/api/http-client";

export function getApiErrorMessage(error: unknown, fallbackMessage: string): string {
  if (error instanceof ApiError) {
    if (typeof error.payload === "object" && error.payload !== null && "detail" in error.payload) {
      const detail = (error.payload as Record<string, unknown>).detail;
      if (typeof detail === "string") {
        return detail;
      }
    }

    if (typeof error.payload === "string" && error.payload.trim().length > 0) {
      return error.payload;
    }
  }

  return fallbackMessage;
}
