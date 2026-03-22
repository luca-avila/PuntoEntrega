import type { DeliveryRead } from "@/api/contracts";

export function formatDeliveryDateTime(value: string): string {
  return new Intl.DateTimeFormat("es-AR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function getDeliveryEmailStatusLabel(
  status: DeliveryRead["email_status"],
): string {
  if (status === "sent") {
    return "Enviado";
  }

  if (status === "failed") {
    return "Fallido";
  }

  return "Pendiente";
}

export function getDeliveryEmailStatusClassName(
  status: DeliveryRead["email_status"],
): string {
  if (status === "sent") {
    return "status-chip-success";
  }

  if (status === "failed") {
    return "status-chip-danger";
  }

  return "status-chip-muted";
}

export function getDeliveryPaymentMethodLabel(
  paymentMethod: DeliveryRead["payment_method"],
): string {
  if (paymentMethod === "cash") {
    return "Efectivo";
  }

  if (paymentMethod === "transfer") {
    return "Transferencia";
  }

  if (paymentMethod === "current_account") {
    return "Cuenta corriente";
  }

  return "Otro";
}
