import type { DeliveryCreateRequest, PaymentMethod } from "@/api/contracts";

export interface DeliveryItemFormValue {
  product_id: string;
  quantity: string;
}

export interface DeliveryFormValues {
  location_id: string;
  delivered_at: string;
  payment_method: PaymentMethod;
  payment_notes: string;
  observations: string;
  summary_recipient_email: string;
  items: DeliveryItemFormValue[];
}

export type DeliveryFormFieldName =
  | "delivered_at"
  | `items.${number}.product_id`
  | `items.${number}.quantity`;

export interface DeliveryFormIssue {
  field: DeliveryFormFieldName;
  message: string;
}

export interface DeliveryFormValidationResult {
  issues: DeliveryFormIssue[];
  payload: DeliveryCreateRequest | null;
}

export const PAYMENT_METHOD_OPTIONS: Array<{ value: PaymentMethod; label: string }> = [
  { value: "cash", label: "Efectivo" },
  { value: "transfer", label: "Transferencia" },
  { value: "current_account", label: "Cuenta corriente" },
  { value: "other", label: "Otro" },
];

function getCurrentDatetimeForInput(): string {
  const now = new Date();
  const timezoneOffsetMs = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - timezoneOffsetMs).toISOString().slice(0, 16);
}

export function buildDefaultDeliveryFormValues(summaryRecipientEmail = ""): DeliveryFormValues {
  return {
    location_id: "",
    delivered_at: getCurrentDatetimeForInput(),
    payment_method: "cash",
    payment_notes: "",
    observations: "",
    summary_recipient_email: summaryRecipientEmail,
    items: [{ product_id: "", quantity: "1" }],
  };
}

function emptyToNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function normalizeDeliveryItems(items: DeliveryItemFormValue[]): DeliveryItemFormValue[] {
  return items.map((item) => ({
    product_id: item.product_id,
    quantity: item.quantity.trim(),
  }));
}

function collectDuplicateProductIssues(items: DeliveryItemFormValue[]): DeliveryFormIssue[] {
  const selectedProductToIndexes = new Map<string, number[]>();

  items.forEach((item, index) => {
    if (!item.product_id) {
      return;
    }

    const indexes = selectedProductToIndexes.get(item.product_id) ?? [];
    indexes.push(index);
    selectedProductToIndexes.set(item.product_id, indexes);
  });

  const issues: DeliveryFormIssue[] = [];

  selectedProductToIndexes.forEach((indexes) => {
    if (indexes.length <= 1) {
      return;
    }

    indexes.forEach((index) => {
      issues.push({
        field: `items.${index}.product_id`,
        message: "No repitas el mismo producto en varias líneas.",
      });
    });
  });

  return issues;
}

function collectInvalidQuantityIssues(items: DeliveryItemFormValue[]): DeliveryFormIssue[] {
  return items.flatMap((item, index) => {
    const numericQuantity = Number(item.quantity);
    if (
      Number.isFinite(numericQuantity)
      && numericQuantity > 0
      && Number.isInteger(numericQuantity)
    ) {
      return [];
    }

    return [
      {
        field: `items.${index}.quantity`,
        message: "La cantidad debe ser un entero mayor a 0.",
      },
    ];
  });
}

export function validateDeliveryForm(
  formValues: DeliveryFormValues,
): DeliveryFormValidationResult {
  const deliveredAtDate = new Date(formValues.delivered_at);
  if (Number.isNaN(deliveredAtDate.getTime())) {
    return {
      issues: [
        {
          field: "delivered_at",
          message: "Ingresá una fecha/hora válida.",
        },
      ],
      payload: null,
    };
  }

  const normalizedItems = normalizeDeliveryItems(formValues.items);
  const issues = [
    ...collectDuplicateProductIssues(normalizedItems),
    ...collectInvalidQuantityIssues(normalizedItems),
  ];

  if (issues.length > 0) {
    return {
      issues,
      payload: null,
    };
  }

  return {
    issues: [],
    payload: {
      location_id: formValues.location_id,
      delivered_at: deliveredAtDate.toISOString(),
      payment_method: formValues.payment_method,
      payment_notes: emptyToNull(formValues.payment_notes),
      observations: emptyToNull(formValues.observations),
      summary_recipient_email: formValues.summary_recipient_email.trim(),
      items: normalizedItems,
    },
  };
}
