import type { DeliveryRead } from "@/api/contracts";

export function formatDeliveryDateTime(value: string): string {
  return new Intl.DateTimeFormat("es-AR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
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
