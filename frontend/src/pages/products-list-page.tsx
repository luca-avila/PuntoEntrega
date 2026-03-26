import { productRequestsApi, productsApi } from "@/api";
import type { ProductRead } from "@/api/contracts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/hooks/use-auth";
import { getApiErrorMessage } from "@/lib/errors";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";

type ProductsFilter = "all" | "active" | "inactive";

interface ProductRequestFormValues {
  subject: string;
  message: string;
  items: Array<{
    product_id: string;
    quantity: string;
  }>;
}

const FILTER_OPTIONS: Array<{ value: ProductsFilter; label: string }> = [
  { value: "all", label: "Todos" },
  { value: "active", label: "Activos" },
  { value: "inactive", label: "Inactivos" },
];

export function ProductsListPage() {
  const navigate = useNavigate();
  const { isOwner } = useAuth();
  const [products, setProducts] = useState<ProductRead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [filter, setFilter] = useState<ProductsFilter>("all");
  const [requestSuccessMessage, setRequestSuccessMessage] = useState<string | null>(null);
  const [requestErrorMessage, setRequestErrorMessage] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    setError,
    clearErrors,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ProductRequestFormValues>({
    defaultValues: {
      subject: "",
      message: "",
      items: [{ product_id: "", quantity: "1" }],
    },
  });
  const { fields, append, remove } = useFieldArray({
    control,
    name: "items",
  });

  const loadProducts = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const records = await productsApi.list();
      setProducts(records);
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error, "No pudimos cargar los productos."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProducts();
  }, [loadProducts]);

  const filteredProducts = useMemo(() => {
    if (filter === "active") {
      return products.filter((product) => product.is_active);
    }

    if (filter === "inactive") {
      return products.filter((product) => !product.is_active);
    }

    return products;
  }, [products, filter]);
  const requestableProducts = useMemo(
    () => products.filter((product) => product.is_active),
    [products],
  );

  const addRequestItemRow = () => {
    append({ product_id: "", quantity: "1" });
  };

  const removeRequestItemRow = (index: number) => {
    if (fields.length === 1) {
      return;
    }
    remove(index);
  };

  const onSubmitProductRequest = handleSubmit(async (formValues) => {
    setRequestSuccessMessage(null);
    setRequestErrorMessage(null);
    clearErrors("items");

    const normalizedItems: Array<{ product_id: string; quantity: string }> = [];
    const seenProductIds = new Set<string>();
    let hasValidationError = false;

    formValues.items.forEach((item, index) => {
      const productId = item.product_id.trim();
      const quantity = item.quantity.trim();

      if (!productId) {
        hasValidationError = true;
        setError(`items.${index}.product_id`, {
          type: "manual",
          message: "Seleccioná un producto.",
        });
      }

      if (!quantity) {
        hasValidationError = true;
        setError(`items.${index}.quantity`, {
          type: "manual",
          message: "La cantidad es obligatoria.",
        });
      } else if (!/^[1-9]\d*$/.test(quantity)) {
        hasValidationError = true;
        setError(`items.${index}.quantity`, {
          type: "manual",
          message: "La cantidad debe ser un entero mayor a 0.",
        });
      }

      if (productId) {
        if (seenProductIds.has(productId)) {
          hasValidationError = true;
          setError(`items.${index}.product_id`, {
            type: "manual",
            message: "No repitas el mismo producto.",
          });
        } else {
          seenProductIds.add(productId);
        }
      }

      if (productId && quantity && /^[1-9]\d*$/.test(quantity)) {
        normalizedItems.push({ product_id: productId, quantity });
      }
    });

    if (hasValidationError || normalizedItems.length === 0) {
      return;
    }

    const normalizedMessage = formValues.message.trim();

    try {
      await productRequestsApi.create({
        subject: formValues.subject,
        message: normalizedMessage || undefined,
        items: normalizedItems,
      });
      setRequestSuccessMessage("Solicitud enviada. El owner recibirá una notificación por email.");
      reset({
        subject: "",
        message: "",
        items: [{ product_id: "", quantity: "1" }],
      });
    } catch (error) {
      setRequestErrorMessage(getApiErrorMessage(error, "No pudimos enviar la solicitud de producto."));
    }
  });

  return (
    <section className="page-section">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="page-title">{isOwner ? "Productos" : "Solicitar productos"}</h2>
          <p className="page-description">
            {isOwner
              ? "Administrá el catálogo de productos de tu organización."
              : "Consultá el catálogo y solicitá nuevos productos al owner."}
          </p>
        </div>
        {isOwner ? (
          <Button onClick={() => navigate("/productos/nuevo")}>Nuevo producto</Button>
        ) : null}
      </div>

      {!isOwner ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Solicitar producto</CardTitle>
            <CardDescription>
              Seleccioná productos y cantidades para solicitar al owner.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {requestableProducts.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No hay productos activos disponibles para solicitar en este momento.
              </p>
            ) : (
              <form className="space-y-4" noValidate onSubmit={onSubmitProductRequest}>
                <div className="space-y-2">
                  <Label htmlFor="product-request-subject">Asunto</Label>
                  <Input
                    id="product-request-subject"
                    placeholder="Ej: Pedido semanal de stock"
                    {...register("subject", {
                      required: "El asunto es obligatorio.",
                      setValueAs: (value: string) => value.trim(),
                      maxLength: {
                        value: 255,
                        message: "El asunto no puede superar los 255 caracteres.",
                      },
                    })}
                  />
                  {errors.subject ? (
                    <p className="text-sm text-destructive">{errors.subject.message}</p>
                  ) : null}
                </div>

                <div className="space-y-3 rounded-xl border border-border/80 bg-secondary/35 p-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-medium">Productos solicitados</h3>
                    <Button onClick={addRequestItemRow} size="sm" type="button" variant="outline">
                      Agregar línea
                    </Button>
                  </div>

                  <div className="space-y-3">
                    {fields.map((field, index) => (
                      <div
                        key={field.id}
                        className="grid gap-2 rounded-lg border border-border/80 bg-card/75 p-3 sm:grid-cols-[1fr_140px_auto] sm:items-end"
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
                            {requestableProducts.map((product) => (
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
                              setValueAs: (value: string) => value.trim(),
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
                          onClick={() => removeRequestItemRow(index)}
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

                <div className="space-y-2">
                  <Label htmlFor="product-request-message">Detalle adicional (opcional)</Label>
                  <Textarea
                    id="product-request-message"
                    placeholder="Información adicional para el owner (horarios, urgencia, etc.)."
                    rows={4}
                    {...register("message", {
                      setValueAs: (value: string) => value.trim(),
                    })}
                  />
                  {errors.message ? (
                    <p className="text-sm text-destructive">{errors.message.message}</p>
                  ) : null}
                </div>

                {requestSuccessMessage ? (
                  <p className="feedback-success">{requestSuccessMessage}</p>
                ) : null}
                {requestErrorMessage ? (
                  <p className="feedback-error">{requestErrorMessage}</p>
                ) : null}

                <Button className="w-full sm:w-auto" disabled={isSubmitting} type="submit">
                  {isSubmitting ? "Enviando..." : "Enviar solicitud"}
                </Button>
              </form>
            )}
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardContent className="px-4 py-5 sm:px-6 sm:py-6">
          <div className="mx-auto flex w-full max-w-xl flex-wrap items-center justify-center gap-2 rounded-xl border border-border/70 bg-background/35 p-2.5">
            {FILTER_OPTIONS.map((option) => (
              <Button
                key={option.value}
                onClick={() => setFilter(option.value)}
                size="sm"
                variant={filter === option.value ? "default" : "outline"}
                className="min-w-[110px]"
              >
                {option.label}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {errorMessage ? (
        <Card className="border-destructive/40">
          <CardHeader>
            <CardTitle className="text-base">No pudimos cargar los productos</CardTitle>
            <CardDescription>{errorMessage}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => void loadProducts()} variant="outline">
              Reintentar
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {isLoading ? (
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">Cargando productos...</CardContent>
        </Card>
      ) : null}

      {!isLoading && !errorMessage && products.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Todavía no hay productos</CardTitle>
            <CardDescription>
              {isOwner
                ? "Creá el primer producto para usarlo en nuevas entregas."
                : "Todavía no hay productos cargados en el catálogo."}
            </CardDescription>
          </CardHeader>
          {isOwner ? (
            <CardContent>
              <Button onClick={() => navigate("/productos/nuevo")}>Crear producto</Button>
            </CardContent>
          ) : null}
        </Card>
      ) : null}

      {!isLoading && !errorMessage && products.length > 0 && filteredProducts.length === 0 ? (
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            No hay productos para el filtro seleccionado.
          </CardContent>
        </Card>
      ) : null}

      {!isLoading && !errorMessage && filteredProducts.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filteredProducts.map((product) => (
            <Card key={product.id} className="flex min-h-[180px] flex-col">
              <CardHeader className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <CardTitle className="text-base leading-tight">{product.name}</CardTitle>
                  <span
                    className={
                      product.is_active
                        ? "status-chip status-chip-success shrink-0"
                        : "status-chip status-chip-muted shrink-0"
                    }
                  >
                    {product.is_active ? "Activo" : "Inactivo"}
                  </span>
                </div>
                <CardDescription>{product.description || "Sin descripción"}</CardDescription>
              </CardHeader>
              {isOwner ? (
                <CardContent className="mt-auto flex justify-end pt-0">
                  <Button onClick={() => navigate(`/productos/${product.id}/editar`)} variant="outline">
                    Editar
                  </Button>
                </CardContent>
              ) : null}
            </Card>
          ))}
        </div>
      ) : null}
    </section>
  );
}
