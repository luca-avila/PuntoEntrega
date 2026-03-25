import { locationsApi } from "@/api";
import type { LocationRead } from "@/api/contracts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { getApiErrorMessage } from "@/lib/errors";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

export function LocationsListPage() {
  const navigate = useNavigate();
  const { isOwner } = useAuth();
  const [locations, setLocations] = useState<LocationRead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const hasLocations = locations.length > 0;

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

  const handleCreateLocation = () => {
    navigate("/ubicaciones/nueva");
  };

  return (
    <section className="page-section">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="page-title">Ubicaciones</h2>
          <p className="page-description">
            Administrá los puntos físicos de entrega de tu organización.
          </p>
        </div>
        {hasLocations && isOwner ? (
          <Button onClick={handleCreateLocation}>Nueva ubicación</Button>
        ) : null}
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

      {!isLoading && !errorMessage && !hasLocations ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Todavía no hay ubicaciones</CardTitle>
            <CardDescription>
              {isOwner
                ? "Creá la primera ubicación para poder registrar entregas."
                : "Tu organización todavía no tiene ubicaciones cargadas."}
            </CardDescription>
          </CardHeader>
          {isOwner ? (
            <CardContent>
              <Button onClick={handleCreateLocation}>Crear ubicación</Button>
            </CardContent>
          ) : null}
        </Card>
      ) : null}

      {!isLoading && !errorMessage && hasLocations ? (
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
                </div>
                {isOwner ? (
                  <Button
                    onClick={() => navigate(`/ubicaciones/${location.id}/editar`)}
                    variant="outline"
                  >
                    Editar
                  </Button>
                ) : null}
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}
    </section>
  );
}
