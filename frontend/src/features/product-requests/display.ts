import type { ProductRequestRead } from "@/api/contracts";

export function formatProductRequestDateTime(value: string): string {
  return new Intl.DateTimeFormat("es-AR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function getProductRequestEmailStatusLabel(
  status: ProductRequestRead["email_status"],
): string {
  if (status === "sent") {
    return "Enviado";
  }

  if (status === "failed") {
    return "Fallido";
  }

  return "Pendiente";
}

export function getProductRequestEmailStatusClassName(
  status: ProductRequestRead["email_status"],
): string {
  if (status === "sent") {
    return "status-chip-success";
  }

  if (status === "failed") {
    return "status-chip-danger";
  }

  return "status-chip-muted";
}
