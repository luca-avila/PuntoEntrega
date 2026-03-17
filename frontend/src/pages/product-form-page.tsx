import { productsApi } from "@/api";
import type {
  ProductCreateRequest,
  ProductRead,
  ProductUpdateRequest,
} from "@/api/contracts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { getApiErrorMessage } from "@/lib/errors";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, useParams } from "react-router-dom";

interface ProductFormValues {
  name: string;
  description: string;
  is_active: boolean;
}

interface ProductFormPageProps {
  mode: "create" | "edit";
}

const DEFAULT_VALUES: ProductFormValues = {
  name: "",
  description: "",
  is_active: true,
};

function mapProductToFormValues(product: ProductRead): ProductFormValues {
  return {
    name: product.name,
    description: product.description ?? "",
    is_active: product.is_active,
  };
}

function emptyToNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function ProductFormPage({ mode }: ProductFormPageProps) {
  const navigate = useNavigate();
  const { productId } = useParams<{ productId: string }>();

  const [isLoadingProduct, setIsLoadingProduct] = useState(mode === "edit");
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ProductFormValues>({
    defaultValues: DEFAULT_VALUES,
  });

  const pageTitle = useMemo(
    () => (mode === "create" ? "Nuevo producto" : "Editar producto"),
    [mode],
  );

  useEffect(() => {
    if (mode !== "edit" || !productId) {
      setIsLoadingProduct(false);
      return;
    }

    const loadProduct = async () => {
      setIsLoadingProduct(true);
      setSubmitError(null);

      try {
        const product = await productsApi.getById(productId);
        reset(mapProductToFormValues(product));
      } catch (error) {
        setSubmitError(
          getApiErrorMessage(error, "No pudimos cargar el producto para editar."),
        );
      } finally {
        setIsLoadingProduct(false);
      }
    };

    void loadProduct();
  }, [mode, productId, reset]);

  const onSubmit = handleSubmit(async (formValues) => {
    setSubmitError(null);

    const basePayload: ProductCreateRequest = {
      name: formValues.name.trim(),
      description: emptyToNull(formValues.description),
      is_active: formValues.is_active,
    };

    try {
      if (mode === "edit" && productId) {
        const updatePayload: ProductUpdateRequest = { ...basePayload };
        await productsApi.update(productId, updatePayload);
      } else {
        await productsApi.create(basePayload);
      }

      navigate("/products", { replace: true });
    } catch (error) {
      setSubmitError(
        getApiErrorMessage(error, "No pudimos guardar el producto. Revisá los datos e intentá nuevamente."),
      );
    }
  });

  if (mode === "edit" && !productId) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-destructive">
          Falta el identificador del producto a editar.
        </CardContent>
      </Card>
    );
  }

  if (isLoadingProduct) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-muted-foreground">
          Cargando producto...
        </CardContent>
      </Card>
    );
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-2">
        <h2 className="text-2xl font-semibold">{pageTitle}</h2>
        <p className="text-sm text-muted-foreground">
          Completá los datos del producto para el catálogo de tu organización.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Datos del producto</CardTitle>
          <CardDescription>
            Solo los productos activos estarán disponibles para nuevas entregas.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={onSubmit}>
            <div className="grid gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">Nombre</Label>
                <Input
                  id="name"
                  placeholder="Harina integral 1kg"
                  {...register("name", {
                    required: "El nombre es obligatorio.",
                    validate: (value) =>
                      value.trim().length > 0 || "El nombre no puede estar vacío.",
                  })}
                />
                {errors.name ? <p className="text-sm text-destructive">{errors.name.message}</p> : null}
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Descripción</Label>
                <Textarea
                  id="description"
                  placeholder="Detalles opcionales del producto."
                  {...register("description")}
                />
              </div>

              <div className="flex items-center gap-2 rounded-md border p-3">
                <input
                  id="is_active"
                  type="checkbox"
                  className="h-4 w-4 rounded border-input text-primary focus:ring-ring"
                  {...register("is_active")}
                />
                <Label htmlFor="is_active">Producto activo</Label>
              </div>
            </div>

            {submitError ? (
              <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {submitError}
              </p>
            ) : null}

            <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
              <Button
                onClick={() => navigate("/products")}
                type="button"
                variant="outline"
              >
                Cancelar
              </Button>
              <Button disabled={isSubmitting} type="submit">
                {isSubmitting ? "Guardando..." : "Guardar producto"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </section>
  );
}
