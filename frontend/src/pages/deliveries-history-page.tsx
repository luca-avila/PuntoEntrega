import { deliveriesApi, locationsApi, productsApi } from "@/api";
import type { DeliveryRead, LocationRead, ProductRead } from "@/api/contracts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { getApiErrorMessage } from "@/lib/errors";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("es-AR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function getEmailStatusLabel(status: DeliveryRead["email_status"]): string {
  if (status === "sent") {
    return "Enviado";
  }

  if (status === "failed") {
    return "Fallido";
  }

  return "Pendiente";
}

function getEmailStatusClassName(status: DeliveryRead["email_status"]): string {
  if (status === "sent") {
    return "bg-emerald-100 text-emerald-700";
  }

  if (status === "failed") {
    return "bg-rose-100 text-rose-700";
  }

  return "bg-slate-200 text-slate-700";
}

function getPaymentMethodLabel(value: DeliveryRead["payment_method"]): string {
  if (value === "cash") {
    return "Efectivo";
  }

  if (value === "transfer") {
    return "Transferencia";
  }

  if (value === "current_account") {
    return "Cuenta corriente";
  }

  return "Otro";
}

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
  delivery: DeliveryRead,
  productsById: Map<string, ProductRead>,
): string {
  const parts = delivery.items.map((item) => {
    const productName = productsById.get(item.product_id)?.name ?? "Producto";
    return `${productName} x ${item.quantity}`;
  });

  if (parts.length <= 2) {
    return parts.join(" · ");
  }

  const remaining = parts.length - 2;
  return `${parts.slice(0, 2).join(" · ")} · +${remaining} ítem(s)`;
}

export function DeliveriesHistoryPage() {
  const navigate = useNavigate();

  const [deliveries, setDeliveries] = useState<DeliveryRead[]>([]);
  const [locations, setLocations] = useState<LocationRead[]>([]);
  const [products, setProducts] = useState<ProductRead[]>([]);

  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [locationFilter, setLocationFilter] = useState("");
  const [dateFromFilter, setDateFromFilter] = useState("");
  const [dateToFilter, setDateToFilter] = useState("");

  const loadDependencies = useCallback(async () => {
    const [locationRecords, productRecords] = await Promise.all([
      locationsApi.list(),
      productsApi.list(),
    ]);
    setLocations(locationRecords);
    setProducts(productRecords);
  }, []);

  const loadDeliveries = useCallback(async () => {
    const records = await deliveriesApi.list({
      location_id: locationFilter || undefined,
      delivered_from: toFilterIsoDate(dateFromFilter, "from"),
      delivered_to: toFilterIsoDate(dateToFilter, "to"),
    });
    setDeliveries(records);
  }, [locationFilter, dateFromFilter, dateToFilter]);

  const loadHistory = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      await Promise.all([loadDependencies(), loadDeliveries()]);
    } catch (error) {
      setErrorMessage(
        getApiErrorMessage(error, "No pudimos cargar el historial de entregas."),
      );
    } finally {
      setIsLoading(false);
    }
  }, [loadDependencies, loadDeliveries]);

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
    setIsLoading(true);
    setErrorMessage(null);
    try {
      await loadDeliveries();
    } catch (error) {
      setErrorMessage(
        getApiErrorMessage(error, "No pudimos aplicar los filtros de historial."),
      );
    } finally {
      setIsLoading(false);
    }
  };

  const clearFilters = async () => {
    setLocationFilter("");
    setDateFromFilter("");
    setDateToFilter("");

    setIsLoading(true);
    setErrorMessage(null);
    try {
      const records = await deliveriesApi.list();
      setDeliveries(records);
    } catch (error) {
      setErrorMessage(
        getApiErrorMessage(error, "No pudimos limpiar los filtros del historial."),
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="space-y-4">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold">Historial de entregas</h2>
        <p className="text-sm text-muted-foreground">
          Revisá entregas registradas y estado de envío de email.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Filtros</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="space-y-2 lg:col-span-1">
            <Label htmlFor="filter_location_id">Ubicación</Label>
            <Select
              id="filter_location_id"
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

          <div className="space-y-2">
            <Label htmlFor="filter_date_from">Desde</Label>
            <Input
              id="filter_date_from"
              onChange={(event) => setDateFromFilter(event.target.value)}
              type="date"
              value={dateFromFilter}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="filter_date_to">Hasta</Label>
            <Input
              id="filter_date_to"
              onChange={(event) => setDateToFilter(event.target.value)}
              type="date"
              value={dateToFilter}
            />
          </div>

          <div className="flex items-end gap-2">
            <Button onClick={() => void applyFilters()} type="button" variant="default">
              Aplicar
            </Button>
            <Button onClick={() => void clearFilters()} type="button" variant="outline">
              Limpiar
            </Button>
          </div>
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
            Cargando historial de entregas...
          </CardContent>
        </Card>
      ) : null}

      {!isLoading && !errorMessage && deliveries.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">No hay entregas registradas</CardTitle>
            <CardDescription>
              Registrá una entrega para verla en este historial.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => navigate("/deliveries/nueva")} type="button">
              Nueva entrega
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {!isLoading && !errorMessage && deliveries.length > 0 ? (
        <div className="grid gap-3">
          {deliveries.map((delivery) => {
            const location = locationsById.get(delivery.location_id);
            return (
              <Card key={delivery.id}>
                <CardHeader>
                  <CardTitle className="flex flex-wrap items-center gap-2 text-base">
                    {location?.name ?? "Ubicación"}
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${getEmailStatusClassName(
                        delivery.email_status,
                      )}`}
                    >
                      Email: {getEmailStatusLabel(delivery.email_status)}
                    </span>
                  </CardTitle>
                  <CardDescription>
                    {formatDateTime(delivery.delivered_at)} · {getPaymentMethodLabel(delivery.payment_method)}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex flex-col gap-3 text-sm sm:flex-row sm:items-end sm:justify-between">
                  <div className="space-y-1 text-muted-foreground">
                    <p>{location?.address ?? "Sin dirección"}</p>
                    <p>{getItemsSummary(delivery, productsById)}</p>
                  </div>
                  <Button
                    onClick={() => navigate(`/deliveries/${delivery.id}`)}
                    type="button"
                    variant="outline"
                  >
                    Ver detalle
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
