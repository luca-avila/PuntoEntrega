import { productsApi } from "@/api";
import type { ProductRead } from "@/api/contracts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getApiErrorMessage } from "@/lib/errors";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

type ProductsFilter = "all" | "active" | "inactive";

const FILTER_OPTIONS: Array<{ value: ProductsFilter; label: string }> = [
  { value: "all", label: "Todos" },
  { value: "active", label: "Activos" },
  { value: "inactive", label: "Inactivos" },
];

export function ProductsListPage() {
  const navigate = useNavigate();
  const [products, setProducts] = useState<ProductRead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [filter, setFilter] = useState<ProductsFilter>("all");

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

  return (
    <section className="page-section">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="page-title">Productos</h2>
          <p className="page-description">
            Administrá el catálogo de productos de tu organización.
          </p>
        </div>
        <Button onClick={() => navigate("/productos/nuevo")}>Nuevo producto</Button>
      </div>

      <Card>
        <CardContent className="flex flex-wrap items-center gap-2 p-4">
          {FILTER_OPTIONS.map((option) => (
            <Button
              key={option.value}
              onClick={() => setFilter(option.value)}
              size="sm"
              variant={filter === option.value ? "default" : "outline"}
            >
              {option.label}
            </Button>
          ))}
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
              Creá el primer producto para usarlo en nuevas entregas.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => navigate("/productos/nuevo")}>Crear producto</Button>
          </CardContent>
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
              <CardContent className="flex justify-end">
                <Button onClick={() => navigate(`/productos/${product.id}/editar`)} variant="outline">
                  Editar
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}
    </section>
  );
}
