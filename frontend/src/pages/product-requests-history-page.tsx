import { locationsApi, productRequestsApi, productsApi } from "@/api";
import type { LocationRead, ProductRead, ProductRequestRead } from "@/api/contracts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  formatProductRequestDateTime,
  getProductRequestEmailStatusClassName,
  getProductRequestEmailStatusLabel,
} from "@/features/product-requests/display";
import { useAuth } from "@/hooks/use-auth";
import { getApiErrorMessage } from "@/lib/errors";
import { useCallback, useEffect, useMemo, useState } from "react";

function toFilterIsoDate(value: string, mode: "from" | "to"): string | undefined {
  const trimmedValue = value.trim();
  if (!trimmedValue) {
    return undefined;
  }

  const boundaryTime = mode === "from" ? "T00:00:00" : "T23:59:59";
  const date = new Date(`${trimmedValue}${boundaryTime}`);
  if (Number.isNaN(date.getTime())) {
    return undefined;
  }

  return date.toISOString();
}

function getItemsSummary(
  productRequest: ProductRequestRead,
  productsById: Map<string, ProductRead>,
): string {
  const parts = productRequest.items.map((item) => {
    const productName = productsById.get(item.product_id)?.name ?? "Producto";
    return `${productName} x ${item.quantity}`;
  });

  if (parts.length <= 2) {
    return parts.join(" · ");
  }

  const remaining = parts.length - 2;
  return `${parts.slice(0, 2).join(" · ")} · +${remaining} ítem(s)`;
}

export function ProductRequestsHistoryPage() {
  const { isOwner } = useAuth();
  const [productRequests, setProductRequests] = useState<ProductRequestRead[]>([]);
  const [locations, setLocations] = useState<LocationRead[]>([]);
  const [products, setProducts] = useState<ProductRead[]>([]);

  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [filterError, setFilterError] = useState<string | null>(null);

  const [locationFilter, setLocationFilter] = useState("");
  const [dateFromFilter, setDateFromFilter] = useState("");
  const [dateToFilter, setDateToFilter] = useState("");

  const loadDependencies = useCallback(async () => {
    if (isOwner) {
      const [locationRecords, productRecords] = await Promise.all([
        locationsApi.list(),
        productsApi.list(),
      ]);
      setLocations(locationRecords);
      setProducts(productRecords);
      return;
    }

    const productRecords = await productsApi.list();
    setLocations([]);
    setProducts(productRecords);
  }, [isOwner]);

  const loadProductRequests = useCallback(async () => {
    const records = await productRequestsApi.list({
      requested_for_location_id: isOwner ? (locationFilter || undefined) : undefined,
      created_from: toFilterIsoDate(dateFromFilter, "from"),
      created_to: toFilterIsoDate(dateToFilter, "to"),
    });
    setProductRequests(records);
  }, [isOwner, locationFilter, dateFromFilter, dateToFilter]);

  const loadHistory = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      await Promise.all([loadDependencies(), loadProductRequests()]);
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error, "No pudimos cargar el historial de pedidos."));
    } finally {
      setIsLoading(false);
    }
  }, [loadDependencies, loadProductRequests]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const locationsById = useMemo(
    () => new Map(locations.map((location) => [location.id, location])),
    [locations],
  );
  const productsById = useMemo(
    () => new Map(products.map((product) => [product.id, product])),
    [products],
  );

  const applyFilters = async () => {
    const fromDate = dateFromFilter.trim();
    const toDate = dateToFilter.trim();
    if (fromDate && toDate && fromDate > toDate) {
      setFilterError("La fecha Desde debe ser menor o igual a la fecha Hasta.");
      return;
    }

    setFilterError(null);
    setIsLoading(true);
    setErrorMessage(null);
    try {
      await loadProductRequests();
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error, "No pudimos aplicar los filtros del historial."));
    } finally {
      setIsLoading(false);
    }
  };

  const clearFilters = async () => {
    setLocationFilter("");
    setDateFromFilter("");
    setDateToFilter("");
    setFilterError(null);

    setIsLoading(true);
    setErrorMessage(null);
    try {
      const records = await productRequestsApi.list();
      setProductRequests(records);
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error, "No pudimos limpiar los filtros del historial."));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="page-section">
      <div className="page-header">
        <h2 className="page-title">Historial de pedidos</h2>
        <p className="page-description">Revisá pedidos registrados y estado de notificación por email.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Filtros</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {isOwner ? (
            <div className="space-y-2 lg:col-span-1">
              <Label htmlFor="filter_request_location_id">Ubicación</Label>
              <Select
                disabled={isLoading}
                id="filter_request_location_id"
                onChange={(event) => setLocationFilter(event.target.value)}
                value={locationFilter}
              >
                <option value="">Todas</option>
                {locations.map((location) => (
                  <option key={location.id} value={location.id}>
                    {location.name}
                  </option>
                ))}
              </Select>
            </div>
          ) : null}

          <div className="space-y-2">
            <Label htmlFor="filter_request_date_from">Desde</Label>
            <Input
              disabled={isLoading}
              id="filter_request_date_from"
              onChange={(event) => setDateFromFilter(event.target.value)}
              type="date"
              value={dateFromFilter}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="filter_request_date_to">Hasta</Label>
            <Input
              disabled={isLoading}
              id="filter_request_date_to"
              onChange={(event) => setDateToFilter(event.target.value)}
              type="date"
              value={dateToFilter}
            />
          </div>

          <div className="flex items-end gap-2">
            <Button disabled={isLoading} onClick={() => void applyFilters()} type="button">
              Aplicar
            </Button>
            <Button
              disabled={isLoading}
              onClick={() => void clearFilters()}
              type="button"
              variant="outline"
            >
              Limpiar
            </Button>
          </div>

          {filterError ? (
            <p className="text-sm text-destructive sm:col-span-2 lg:col-span-4">{filterError}</p>
          ) : null}
        </CardContent>
      </Card>

      {errorMessage ? (
        <Card className="border-destructive/40">
          <CardHeader>
            <CardTitle className="text-base">No pudimos cargar el historial</CardTitle>
            <CardDescription>{errorMessage}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => void loadHistory()} type="button" variant="outline">
              Reintentar
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {isLoading ? (
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            Cargando historial de pedidos...
          </CardContent>
        </Card>
      ) : null}

      {!isLoading && !errorMessage && productRequests.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">No hay pedidos registrados</CardTitle>
            <CardDescription>Todavía no hay pedidos para mostrar con los filtros aplicados.</CardDescription>
          </CardHeader>
        </Card>
      ) : null}

      {!isLoading && !errorMessage && productRequests.length > 0 ? (
        <div className="grid gap-3">
          {productRequests.map((productRequest) => {
            const location = productRequest.requested_for_location_id
              ? locationsById.get(productRequest.requested_for_location_id)
              : undefined;
            const locationName =
              productRequest.requested_for_location_name ??
              location?.name ??
              "Sin ubicación asignada";
            const locationAddress =
              productRequest.requested_for_location_address ??
              location?.address ??
              "Sin dirección";

            return (
              <Card key={productRequest.id}>
                <CardHeader>
                  <CardTitle className="flex flex-wrap items-center gap-2 text-base">
                    {productRequest.subject}
                    <span
                      className={`status-chip ${getProductRequestEmailStatusClassName(
                        productRequest.email_status,
                      )}`}
                    >
                      Email: {getProductRequestEmailStatusLabel(productRequest.email_status)}
                    </span>
                  </CardTitle>
                  <CardDescription className="space-y-1">
                    <span className="block">Ubicación: {locationName}</span>
                    <span className="block">{locationAddress}</span>
                    <span className="block">
                      Pedido: {formatProductRequestDateTime(productRequest.created_at)}
                    </span>
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <p>
                    <strong>Items:</strong> {getItemsSummary(productRequest, productsById)}
                  </p>
                  {productRequest.message ? (
                    <p>
                      <strong>Mensaje:</strong> {productRequest.message}
                    </p>
                  ) : (
                    <p className="text-muted-foreground">Sin mensaje adicional.</p>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
