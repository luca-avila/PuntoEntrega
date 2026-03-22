import { locationsApi } from "@/api";
import type {
  LocationCreateRequest,
  LocationRead,
  LocationUpdateRequest,
} from "@/api/contracts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { LocationMapPicker } from "@/features/locations/location-map-picker";
import { getApiErrorMessage } from "@/lib/errors";
import type { LatLngLiteral } from "leaflet";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, useParams } from "react-router-dom";

interface LocationFormValues {
  name: string;
  address: string;
  contact_name: string;
  contact_phone: string;
  contact_email: string;
  notes: string;
  latitude: number | null;
  longitude: number | null;
}

interface LocationFormPageProps {
  mode: "create" | "edit";
}

interface NominatimResult {
  lat: string;
  lon: string;
}

const DEFAULT_VALUES: LocationFormValues = {
  name: "",
  address: "",
  contact_name: "",
  contact_phone: "",
  contact_email: "",
  notes: "",
  latitude: null,
  longitude: null,
};

function emptyToNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function mapLocationToFormValues(location: LocationRead): LocationFormValues {
  return {
    name: location.name,
    address: location.address,
    contact_name: location.contact_name ?? "",
    contact_phone: location.contact_phone ?? "",
    contact_email: location.contact_email ?? "",
    notes: location.notes ?? "",
    latitude: location.latitude,
    longitude: location.longitude,
  };
}

export function LocationFormPage({ mode }: LocationFormPageProps) {
  const navigate = useNavigate();
  const { locationId } = useParams<{ locationId: string }>();

  const [isLoadingLocation, setIsLoadingLocation] = useState(mode === "edit");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [mapError, setMapError] = useState<string | null>(null);
  const [isLocatingAddress, setIsLocatingAddress] = useState(false);
  const [selectedPoint, setSelectedPoint] = useState<LatLngLiteral | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    setError,
    getValues,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<LocationFormValues>({
    defaultValues: DEFAULT_VALUES,
  });

  const latitude = watch("latitude");
  const longitude = watch("longitude");

  const pageTitle = useMemo(
    () => (mode === "create" ? "Nueva ubicación" : "Editar ubicación"),
    [mode],
  );

  useEffect(() => {
    if (mode !== "edit" || !locationId) {
      setIsLoadingLocation(false);
      return;
    }

    const loadLocation = async () => {
      setIsLoadingLocation(true);
      setSubmitError(null);

      try {
        const location = await locationsApi.getById(locationId);
        reset(mapLocationToFormValues(location));
        setSelectedPoint({ lat: location.latitude, lng: location.longitude });
      } catch (error) {
        setSubmitError(
          getApiErrorMessage(error, "No pudimos cargar la ubicación para editar."),
        );
      } finally {
        setIsLoadingLocation(false);
      }
    };

    void loadLocation();
  }, [mode, locationId, reset]);

  const handlePointSelection = (point: LatLngLiteral) => {
    setSelectedPoint(point);
    setMapError(null);
    setValue("latitude", Number(point.lat.toFixed(6)), { shouldValidate: true });
    setValue("longitude", Number(point.lng.toFixed(6)), { shouldValidate: true });
  };

  const handleAddressLookup = async () => {
    const address = getValues("address").trim();
    if (!address) {
      setMapError("Ingresá una dirección antes de buscar en el mapa.");
      return;
    }

    setIsLocatingAddress(true);
    setMapError(null);

    try {
      const query = new URLSearchParams({
        format: "jsonv2",
        limit: "1",
        q: address,
      });
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?${query.toString()}`,
      );

      if (!response.ok) {
        throw new Error("No se pudo consultar Nominatim");
      }

      const results = (await response.json()) as NominatimResult[];
      if (results.length === 0) {
        setMapError(
          "No encontramos la dirección. Ajustá el texto o seleccioná manualmente en el mapa.",
        );
        return;
      }

      const firstResult = results[0];
      const lat = Number(firstResult.lat);
      const lng = Number(firstResult.lon);

      if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
        setMapError("La búsqueda devolvió coordenadas inválidas.");
        return;
      }

      handlePointSelection({ lat, lng });
    } catch {
      setMapError("No pudimos ubicar la dirección. Probá de nuevo o marcá el punto manualmente.");
    } finally {
      setIsLocatingAddress(false);
    }
  };

  const onSubmit = handleSubmit(async (formValues) => {
    setSubmitError(null);
    setMapError(null);

    if (formValues.latitude === null || formValues.longitude === null) {
      setMapError("Seleccioná en el mapa el punto exacto de la ubicación.");
      setError("latitude", {
        type: "manual",
        message: "Debés seleccionar un punto en el mapa.",
      });
      return;
    }

    const basePayload: LocationCreateRequest = {
      name: formValues.name.trim(),
      address: formValues.address.trim(),
      contact_name: emptyToNull(formValues.contact_name),
      contact_phone: emptyToNull(formValues.contact_phone),
      contact_email: emptyToNull(formValues.contact_email),
      latitude: formValues.latitude,
      longitude: formValues.longitude,
      notes: emptyToNull(formValues.notes),
    };

    try {
      if (mode === "edit" && locationId) {
        const updatePayload: LocationUpdateRequest = { ...basePayload };
        await locationsApi.update(locationId, updatePayload);
      } else {
        await locationsApi.create(basePayload);
      }

      navigate("/ubicaciones", { replace: true });
    } catch (error) {
      setSubmitError(
        getApiErrorMessage(error, "No pudimos guardar la ubicación. Revisá los datos e intentá nuevamente."),
      );
    }
  });

  if (mode === "edit" && !locationId) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-destructive">
          Falta el identificador de la ubicación a editar.
        </CardContent>
      </Card>
    );
  }

  if (isLoadingLocation) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-muted-foreground">
          Cargando ubicación...
        </CardContent>
      </Card>
    );
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-2">
        <h2 className="text-2xl font-semibold">{pageTitle}</h2>
        <p className="text-sm text-muted-foreground">
          Completá los datos y elegí el punto exacto en el mapa.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Datos de la ubicación</CardTitle>
          <CardDescription>
            Las coordenadas se guardan al seleccionar el punto en el mapa.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={onSubmit}>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="name">Nombre</Label>
                <Input
                  id="name"
                  placeholder="Sucursal Centro"
                  {...register("name", {
                    required: "El nombre es obligatorio.",
                    validate: (value) =>
                      value.trim().length > 0 || "El nombre no puede estar vacío.",
                  })}
                />
                {errors.name ? <p className="text-sm text-destructive">{errors.name.message}</p> : null}
              </div>

              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="address">Dirección</Label>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Input
                    id="address"
                    placeholder="Av. Corrientes 1234, CABA"
                    {...register("address", {
                      required: "La dirección es obligatoria.",
                      validate: (value) =>
                        value.trim().length > 0 || "La dirección no puede estar vacía.",
                    })}
                  />
                  <Button
                    disabled={isLocatingAddress}
                    onClick={() => void handleAddressLookup()}
                    type="button"
                    variant="outline"
                  >
                    {isLocatingAddress ? "Buscando..." : "Buscar en mapa"}
                  </Button>
                </div>
                {errors.address ? (
                  <p className="text-sm text-destructive">{errors.address.message}</p>
                ) : null}
              </div>

              <div className="space-y-2 sm:col-span-2">
                <Label>Ubicación en mapa</Label>
                <LocationMapPicker
                  onSelectPoint={handlePointSelection}
                  selectedPoint={selectedPoint}
                />
                <p className="text-xs text-muted-foreground">
                  Hacé click en el mapa para marcar el punto exacto.
                </p>
                <p className="text-sm">
                  Punto seleccionado:{" "}
                  {latitude !== null && longitude !== null
                    ? `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`
                    : "Sin seleccionar"}
                </p>
                {mapError ? <p className="text-sm text-destructive">{mapError}</p> : null}
              </div>

              <div className="space-y-2">
                <Label htmlFor="contact_name">Contacto</Label>
                <Input id="contact_name" placeholder="Nombre y apellido" {...register("contact_name")} />
              </div>

              <div className="space-y-2">
                <Label htmlFor="contact_phone">Teléfono</Label>
                <Input id="contact_phone" placeholder="+54 11 ..." {...register("contact_phone")} />
              </div>

              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="contact_email">Email de contacto</Label>
                <Input
                  id="contact_email"
                  placeholder="contacto@negocio.com"
                  type="email"
                  {...register("contact_email", {
                    validate: (value) => {
                      if (!value || value.trim().length === 0) {
                        return true;
                      }

                      const isValidEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
                      return isValidEmail || "Ingresá un email válido.";
                    },
                  })}
                />
                {errors.contact_email ? (
                  <p className="text-sm text-destructive">{errors.contact_email.message}</p>
                ) : null}
              </div>

              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="notes">Notas</Label>
                <Textarea id="notes" placeholder="Información útil para la entrega." {...register("notes")} />
              </div>
            </div>

            {submitError ? (
              <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {submitError}
              </p>
            ) : null}

            <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
              <Button
                onClick={() => navigate("/ubicaciones")}
                type="button"
                variant="outline"
              >
                Cancelar
              </Button>
              <Button disabled={isSubmitting} type="submit">
                {isSubmitting ? "Guardando..." : "Guardar ubicación"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </section>
  );
}
