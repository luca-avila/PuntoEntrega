import { deliveriesApi, locationsApi, productsApi } from "@/api";
import type { DeliveryRead, LocationRead, ProductRead } from "@/api/contracts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  formatDeliveryDateTime,
  getDeliveryEmailStatusClassName,
  getDeliveryEmailStatusLabel,
  getDeliveryPaymentMethodLabel,
} from "@/features/deliveries/display";
import { getApiErrorMessage } from "@/lib/errors";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

export function DeliveryDetailPage() {
  const navigate = useNavigate();
  const { deliveryId } = useParams<{ deliveryId: string }>();

  const [delivery, setDelivery] = useState<DeliveryRead | null>(null);
  const [location, setLocation] = useState<LocationRead | null>(null);
  const [products, setProducts] = useState<ProductRead[]>([]);

  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadDeliveryDetail = useCallback(async () => {
    if (!deliveryId) {
      setErrorMessage("Falta el identificador de la entrega.");
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const record = await deliveriesApi.getById(deliveryId);
      setDelivery(record);

      const [locationRecord, productRecords] = await Promise.all([
        locationsApi.getById(record.location_id),
        productsApi.list(),
      ]);

      setLocation(locationRecord);
      setProducts(productRecords);
    } catch (error) {
      setErrorMessage(
        getApiErrorMessage(error, "No pudimos cargar el detalle de la entrega."),
      );
    } finally {
      setIsLoading(false);
    }
  }, [deliveryId]);

  useEffect(() => {
    void loadDeliveryDetail();
  }, [loadDeliveryDetail]);

  const productsById = useMemo(
    () => new Map(products.map((product) => [product.id, product])),
    [products],
  );

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-muted-foreground">
          Cargando detalle de entrega...
        </CardContent>
      </Card>
    );
  }

  if (errorMessage) {
    return (
      <Card className="border-destructive/40">
        <CardHeader>
          <CardTitle className="text-base">No pudimos cargar la entrega</CardTitle>
          <CardDescription>{errorMessage}</CardDescription>
        </CardHeader>
        <CardContent className="flex gap-2">
          <Button onClick={() => void loadDeliveryDetail()} type="button" variant="outline">
            Reintentar
          </Button>
          <Button onClick={() => navigate("/deliveries")} type="button" variant="outline">
            Volver al historial
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!delivery) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-muted-foreground">
          No encontramos la entrega solicitada.
        </CardContent>
      </Card>
    );
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="space-y-1">
          <h2 className="text-2xl font-semibold">Detalle de entrega</h2>
          <p className="text-sm text-muted-foreground">ID: {delivery.id}</p>
        </div>

        <div className="flex gap-2">
          <Button onClick={() => navigate("/deliveries")} type="button" variant="outline">
            Historial
          </Button>
          <Button onClick={() => navigate("/deliveries/nueva")} type="button" variant="outline">
            Nueva entrega
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex flex-wrap items-center gap-2 text-lg">
            {location?.name ?? "Ubicación"}
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${getDeliveryEmailStatusClassName(
                delivery.email_status,
              )}`}
            >
              Email: {getDeliveryEmailStatusLabel(delivery.email_status)}
            </span>
          </CardTitle>
          <CardDescription>{location?.address ?? "Sin dirección"}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 text-sm sm:grid-cols-2">
          <div>
            <p className="font-medium">Fecha y hora</p>
            <p className="text-muted-foreground">{formatDeliveryDateTime(delivery.delivered_at)}</p>
          </div>
          <div>
            <p className="font-medium">Método de pago</p>
            <p className="text-muted-foreground">
              {getDeliveryPaymentMethodLabel(delivery.payment_method)}
            </p>
          </div>
          <div>
            <p className="font-medium">Notas de pago</p>
            <p className="text-muted-foreground">{delivery.payment_notes || "Sin notas"}</p>
          </div>
          <div>
            <p className="font-medium">Observaciones</p>
            <p className="text-muted-foreground">{delivery.observations || "Sin observaciones"}</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Items entregados</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {delivery.items.length === 0 ? (
            <p className="text-sm text-muted-foreground">La entrega no tiene items.</p>
          ) : (
            delivery.items.map((item) => {
              const productName = productsById.get(item.product_id)?.name ?? "Producto";
              return (
                <div
                  key={item.id}
                  className="flex items-center justify-between rounded-md border p-3 text-sm"
                >
                  <span>{productName}</span>
                  <span className="font-medium">Cantidad: {item.quantity}</span>
                </div>
              );
            })
          )}
        </CardContent>
      </Card>
    </section>
  );
}
