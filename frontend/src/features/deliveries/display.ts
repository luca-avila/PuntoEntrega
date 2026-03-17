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
    return "bg-emerald-100 text-emerald-700";
  }

  if (status === "failed") {
    return "bg-rose-100 text-rose-700";
  }

  return "bg-slate-200 text-slate-700";
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
