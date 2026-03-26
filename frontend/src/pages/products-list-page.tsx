import { productRequestsApi, productsApi } from "@/api";
import type { ProductRead } from "@/api/contracts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/hooks/use-auth";
import { getApiErrorMessage } from "@/lib/errors";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";

type ProductsFilter = "all" | "active" | "inactive";

interface ProductRequestFormValues {
  subject: string;
  message: string;
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
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ProductRequestFormValues>({
    defaultValues: {
      subject: "",
      message: "",
    },
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

  const onSubmitProductRequest = handleSubmit(async (formValues) => {
    setRequestSuccessMessage(null);
    setRequestErrorMessage(null);
    try {
      await productRequestsApi.create({
        subject: formValues.subject,
        message: formValues.message,
      });
      setRequestSuccessMessage("Solicitud enviada. El owner recibirá una notificación por email.");
      reset();
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
              Enviá una petición al owner con el producto que necesitás incorporar.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-3" noValidate onSubmit={onSubmitProductRequest}>
              <div className="space-y-2">
                <Label htmlFor="product-request-subject">Asunto</Label>
                <Input
                  id="product-request-subject"
                  placeholder="Ej: Agregar harina integral"
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

              <div className="space-y-2">
                <Label htmlFor="product-request-message">Detalle</Label>
                <Textarea
                  id="product-request-message"
                  placeholder="Contá qué producto necesitás y cualquier detalle relevante."
                  rows={4}
                  {...register("message", {
                    required: "El detalle es obligatorio.",
                    setValueAs: (value: string) => value.trim(),
                    minLength: {
                      value: 10,
                      message: "El detalle debe tener al menos 10 caracteres.",
                    },
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
        <div className="grid gap-3">
          {filteredProducts.map((product) => (
            <Card key={product.id}>
              <CardHeader>
                <CardTitle className="flex flex-wrap items-center gap-2 text-base">
                  {product.name}
                  <span
                    className={
                      product.is_active
                        ? "status-chip status-chip-success"
                        : "status-chip status-chip-muted"
                    }
                  >
                    {product.is_active ? "Activo" : "Inactivo"}
                  </span>
                </CardTitle>
                <CardDescription>{product.description || "Sin descripción"}</CardDescription>
              </CardHeader>
              {isOwner ? (
                <CardContent className="flex justify-end">
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
