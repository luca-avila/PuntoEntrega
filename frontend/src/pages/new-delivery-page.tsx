import { deliveriesApi, locationsApi, productsApi } from "@/api";
import type {
  DeliveryCreateRequest,
  DeliveryRead,
  LocationRead,
  PaymentMethod,
  ProductRead,
} from "@/api/contracts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { getDeliveryEmailStatusLabel } from "@/features/deliveries/display";
import { getApiErrorMessage } from "@/lib/errors";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";

interface DeliveryItemFormValue {
  product_id: string;
  quantity: string;
}

interface DeliveryFormValues {
  location_id: string;
  delivered_at: string;
  payment_method: PaymentMethod;
  payment_notes: string;
  observations: string;
  items: DeliveryItemFormValue[];
}

const PAYMENT_METHOD_OPTIONS: Array<{ value: PaymentMethod; label: string }> = [
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

function buildDefaultValues(): DeliveryFormValues {
  return {
    location_id: "",
    delivered_at: getCurrentDatetimeForInput(),
    payment_method: "cash",
    payment_notes: "",
    observations: "",
    items: [{ product_id: "", quantity: "1" }],
  };
}

function emptyToNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function NewDeliveryPage() {
  const navigate = useNavigate();
  const [locations, setLocations] = useState<LocationRead[]>([]);
  const [activeProducts, setActiveProducts] = useState<ProductRead[]>([]);
  const [isLoadingDependencies, setIsLoadingDependencies] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [createdDelivery, setCreatedDelivery] = useState<DeliveryRead | null>(null);

  const {
    register,
    control,
    handleSubmit,
    reset,
    setError,
    clearErrors,
    formState: { errors, isSubmitting },
  } = useForm<DeliveryFormValues>({
    defaultValues: buildDefaultValues(),
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: "items",
  });

  const loadDependencies = useCallback(async () => {
    setIsLoadingDependencies(true);
    setLoadError(null);

    try {
      const [locationRecords, activeProductRecords] = await Promise.all([
        locationsApi.list(),
        productsApi.list({ active_only: true }),
      ]);

      setLocations(locationRecords);
      setActiveProducts(activeProductRecords);
    } catch (error) {
      setLoadError(
        getApiErrorMessage(
          error,
          "No pudimos cargar ubicaciones y productos para registrar la entrega.",
        ),
      );
    } finally {
      setIsLoadingDependencies(false);
    }
  }, []);

  useEffect(() => {
    void loadDependencies();
  }, [loadDependencies]);

  const isReadyForDelivery = useMemo(
    () => locations.length > 0 && activeProducts.length > 0,
    [locations.length, activeProducts.length],
  );

  const addItemRow = () => {
    append({ product_id: "", quantity: "1" });
  };

  const removeItemRow = (index: number) => {
    if (fields.length === 1) {
      return;
    }

    remove(index);
  };

  const onSubmit = handleSubmit(async (formValues) => {
    setSubmitError(null);
    setCreatedDelivery(null);
    clearErrors("items");

    const deliveredAtDate = new Date(formValues.delivered_at);
    if (Number.isNaN(deliveredAtDate.getTime())) {
      setError("delivered_at", {
        type: "manual",
        message: "Ingresá una fecha/hora válida.",
      });
      return;
    }

    const normalizedItems = formValues.items.map((item) => ({
      product_id: item.product_id,
      quantity: item.quantity.trim(),
    }));

    const selectedProductToIndexes = new Map<string, number[]>();
    normalizedItems.forEach((item, index) => {
      if (!item.product_id) {
        return;
      }
      const indexes = selectedProductToIndexes.get(item.product_id) ?? [];
      indexes.push(index);
      selectedProductToIndexes.set(item.product_id, indexes);
    });

    let hasDuplicateProducts = false;
    selectedProductToIndexes.forEach((indexes) => {
      if (indexes.length <= 1) {
        return;
      }
      hasDuplicateProducts = true;
      indexes.forEach((index) => {
        setError(`items.${index}.product_id`, {
          type: "manual",
          message: "No repitas el mismo producto en varias líneas.",
        });
      });
    });

    let hasInvalidQuantity = false;
    normalizedItems.forEach((item, index) => {
      const numericQuantity = Number(item.quantity);
      if (
        !Number.isFinite(numericQuantity)
        || numericQuantity <= 0
        || !Number.isInteger(numericQuantity)
      ) {
        hasInvalidQuantity = true;
        setError(`items.${index}.quantity`, {
          type: "manual",
          message: "La cantidad debe ser un entero mayor a 0.",
        });
      }
    });

    if (hasInvalidQuantity || hasDuplicateProducts) {
      return;
    }

    const payload: DeliveryCreateRequest = {
      location_id: formValues.location_id,
      delivered_at: deliveredAtDate.toISOString(),
      payment_method: formValues.payment_method,
      payment_notes: emptyToNull(formValues.payment_notes),
      observations: emptyToNull(formValues.observations),
      items: normalizedItems,
    };

    try {
      const delivery = await deliveriesApi.create(payload);
      setCreatedDelivery(delivery);
      reset(buildDefaultValues());
    } catch (error) {
      setSubmitError(
        getApiErrorMessage(error, "No pudimos registrar la entrega. Revisá los datos e intentá nuevamente."),
      );
    }
  });

  return (
    <section className="space-y-4">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold">Nueva entrega</h2>
        <p className="text-sm text-muted-foreground">
          Registrá una entrega con ubicación, productos y forma de pago.
        </p>
      </div>

      {createdDelivery ? (
        <Card className="border-emerald-300 bg-emerald-50/50">
          <CardHeader>
            <CardTitle className="text-base text-emerald-700">Entrega registrada</CardTitle>
            <CardDescription className="text-emerald-700/80">
              ID: {createdDelivery.id} · Estado de email:{" "}
              {getDeliveryEmailStatusLabel(createdDelivery.email_status)}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Button
              onClick={() => navigate(`/deliveries/${createdDelivery.id}`)}
              type="button"
              variant="outline"
            >
              Ver detalle
            </Button>
            <Button onClick={() => navigate("/deliveries")} type="button" variant="outline">
              Ir al historial
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {loadError ? (
        <Card className="border-destructive/40">
          <CardHeader>
            <CardTitle className="text-base">No pudimos cargar los datos base</CardTitle>
            <CardDescription>{loadError}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => void loadDependencies()} type="button" variant="outline">
              Reintentar
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {isLoadingDependencies ? (
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            Cargando ubicaciones y productos...
          </CardContent>
        </Card>
      ) : null}

      {!isLoadingDependencies && !loadError && locations.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Necesitás al menos una ubicación</CardTitle>
            <CardDescription>
              Primero creá una ubicación para asociarla a la entrega.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => navigate("/locations/nueva")} type="button">
              Crear ubicación
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {!isLoadingDependencies && !loadError && activeProducts.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Necesitás productos activos</CardTitle>
            <CardDescription>
              No hay productos activos disponibles para nuevas entregas.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => navigate("/products/nuevo")} type="button">
              Crear producto
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {!isLoadingDependencies && !loadError && isReadyForDelivery ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Formulario de entrega</CardTitle>
            <CardDescription>
              Podés agregar varias líneas de productos en una misma entrega.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-5" onSubmit={onSubmit}>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="location_id">Ubicación</Label>
                  <Select
                    id="location_id"
                    {...register("location_id", {
                      required: "La ubicación es obligatoria.",
                    })}
                  >
                    <option value="">Seleccionar ubicación</option>
                    {locations.map((location) => (
                      <option key={location.id} value={location.id}>
                        {location.name}
                      </option>
                    ))}
                  </Select>
                  {errors.location_id ? (
                    <p className="text-sm text-destructive">{errors.location_id.message}</p>
                  ) : null}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="delivered_at">Fecha y hora de entrega</Label>
                  <Input
                    id="delivered_at"
                    type="datetime-local"
                    {...register("delivered_at", {
                      required: "La fecha y hora son obligatorias.",
                    })}
                  />
                  {errors.delivered_at ? (
                    <p className="text-sm text-destructive">{errors.delivered_at.message}</p>
                  ) : null}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="payment_method">Método de pago</Label>
                  <Select
                    id="payment_method"
                    {...register("payment_method", {
                      required: "El método de pago es obligatorio.",
                    })}
                  >
                    {PAYMENT_METHOD_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </Select>
                  {errors.payment_method ? (
                    <p className="text-sm text-destructive">{errors.payment_method.message}</p>
                  ) : null}
                </div>

                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="payment_notes">Notas de pago</Label>
                  <Input
                    id="payment_notes"
                    placeholder="Ej: se abona por transferencia el viernes"
                    {...register("payment_notes")}
                  />
                </div>

                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="observations">Observaciones</Label>
                  <Textarea
                    id="observations"
                    placeholder="Detalle adicional de la entrega."
                    {...register("observations")}
                  />
                </div>
              </div>

              <div className="space-y-3 rounded-md border p-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium">Productos entregados</h3>
                  <Button onClick={addItemRow} size="sm" type="button" variant="outline">
                    Agregar línea
                  </Button>
                </div>

                <div className="space-y-3">
                  {fields.map((field, index) => (
                    <div
                      key={field.id}
                      className="grid gap-2 rounded-md border p-3 sm:grid-cols-[1fr_140px_auto] sm:items-end"
                    >
                      <div className="space-y-2">
                        <Label htmlFor={`items.${index}.product_id`}>Producto</Label>
                        <Select
                          id={`items.${index}.product_id`}
                          {...register(`items.${index}.product_id`, {
                            required: "Seleccioná un producto.",
                          })}
                        >
                          <option value="">Seleccionar producto</option>
                          {activeProducts.map((product) => (
                            <option key={product.id} value={product.id}>
                              {product.name}
                            </option>
                          ))}
                        </Select>
                        {errors.items?.[index]?.product_id ? (
                          <p className="text-sm text-destructive">
                            {errors.items[index]?.product_id?.message}
                          </p>
                        ) : null}
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor={`items.${index}.quantity`}>Cantidad</Label>
                        <Input
                          id={`items.${index}.quantity`}
                          inputMode="numeric"
                          min="1"
                          placeholder="1"
                          step="1"
                          type="number"
                          {...register(`items.${index}.quantity`, {
                            required: "La cantidad es obligatoria.",
                          })}
                        />
                        {errors.items?.[index]?.quantity ? (
                          <p className="text-sm text-destructive">
                            {errors.items[index]?.quantity?.message}
                          </p>
                        ) : null}
                      </div>

                      <Button
                        className="sm:self-end"
                        disabled={fields.length === 1}
                        onClick={() => removeItemRow(index)}
                        size="sm"
                        type="button"
                        variant="outline"
                      >
                        Quitar
                      </Button>
                    </div>
                  ))}
                </div>
              </div>

              {submitError ? (
                <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {submitError}
                </p>
              ) : null}

              <div className="flex justify-end">
                <Button disabled={isSubmitting} type="submit">
                  {isSubmitting ? "Registrando..." : "Registrar entrega"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : null}
    </section>
  );
}
