import { locationsApi } from "@/api";
import type { LocationRead } from "@/api/contracts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getApiErrorMessage } from "@/lib/errors";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

export function LocationsListPage() {
  const navigate = useNavigate();
  const [locations, setLocations] = useState<LocationRead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadLocations = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const records = await locationsApi.list();
      setLocations(records);
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error, "No pudimos cargar las ubicaciones."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadLocations();
  }, [loadLocations]);

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Ubicaciones</h2>
          <p className="text-sm text-muted-foreground">
            Administrá los puntos físicos de entrega de tu organización.
          </p>
        </div>
        <Button onClick={() => navigate("/locations/nueva")}>Nueva ubicación</Button>
      </div>

      {errorMessage ? (
        <Card className="border-destructive/40">
          <CardHeader>
            <CardTitle className="text-base">No pudimos cargar las ubicaciones</CardTitle>
            <CardDescription>{errorMessage}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => void loadLocations()} variant="outline">
              Reintentar
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {isLoading ? (
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">Cargando ubicaciones...</CardContent>
        </Card>
      ) : null}

      {!isLoading && !errorMessage && locations.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Todavía no hay ubicaciones</CardTitle>
            <CardDescription>
              Creá la primera ubicación para poder registrar entregas.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => navigate("/locations/nueva")}>Crear ubicación</Button>
          </CardContent>
        </Card>
      ) : null}

      {!isLoading && !errorMessage && locations.length > 0 ? (
        <div className="grid gap-3">
          {locations.map((location) => (
            <Card key={location.id}>
              <CardHeader>
                <CardTitle className="text-base">{location.name}</CardTitle>
                <CardDescription>{location.address}</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-3 text-sm sm:flex-row sm:items-center sm:justify-between">
                <div className="space-y-1 text-muted-foreground">
                  <p>
                    Contacto: {location.contact_name ?? "Sin contacto"}
                    {location.contact_phone ? ` · ${location.contact_phone}` : ""}
                  </p>
                  <p>
                    Coordenadas: {location.latitude.toFixed(5)}, {location.longitude.toFixed(5)}
                  </p>
                </div>
                <Button
                  onClick={() => navigate(`/locations/${location.id}/editar`)}
                  variant="outline"
                >
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
