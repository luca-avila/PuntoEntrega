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
import {
  reverseGeocodeCoordinates,
  searchAddressSuggestions,
  type GeocodingSuggestion,
} from "@/features/locations/geocoding";
import { Textarea } from "@/components/ui/textarea";
import { LocationMapPicker } from "@/features/locations/location-map-picker";
import { getApiErrorMessage } from "@/lib/errors";
import type { LatLngLiteral } from "leaflet";
import { useEffect, useMemo, useRef, useState } from "react";
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

const MIN_ADDRESS_QUERY_LENGTH = 3;
const ADDRESS_SUGGESTIONS_DEBOUNCE_MS = 350;
const PHONE_PATTERN = /^[0-9+\-()\s]+$/;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

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
  const [isAddressInputFocused, setIsAddressInputFocused] = useState(false);
  const [isSearchingAddressSuggestions, setIsSearchingAddressSuggestions] = useState(false);
  const [addressSuggestions, setAddressSuggestions] = useState<GeocodingSuggestion[]>([]);
  const addressSuggestionsAbortRef = useRef<AbortController | null>(null);
  const reverseGeocodeAbortRef = useRef<AbortController | null>(null);

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

  const address = watch("address");

  const pageTitle = useMemo(
    () => (mode === "create" ? "Nueva ubicación" : "Editar ubicación"),
    [mode],
  );

  const {
    onBlur: onAddressFieldBlur,
    ...addressFieldRegistration
  } = register("address", {
    required: "La dirección es obligatoria.",
    maxLength: {
      value: 500,
      message: "La dirección no puede superar los 500 caracteres.",
    },
    setValueAs: (value: string) => value.trim(),
    validate: (value) =>
      value.trim().length > 0 || "La dirección no puede estar vacía.",
  });

  const showAddressSuggestions =
    isAddressInputFocused &&
    address.trim().length >= MIN_ADDRESS_QUERY_LENGTH &&
    (isSearchingAddressSuggestions || addressSuggestions.length > 0);

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

  useEffect(() => {
    return () => {
      addressSuggestionsAbortRef.current?.abort();
      reverseGeocodeAbortRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    const query = address.trim();

    if (!isAddressInputFocused || query.length < MIN_ADDRESS_QUERY_LENGTH) {
      addressSuggestionsAbortRef.current?.abort();
      setAddressSuggestions([]);
      setIsSearchingAddressSuggestions(false);
      return;
    }

    const debounceTimer = window.setTimeout(() => {
      addressSuggestionsAbortRef.current?.abort();
      const controller = new AbortController();
      addressSuggestionsAbortRef.current = controller;

      setIsSearchingAddressSuggestions(true);

      void searchAddressSuggestions(query, {
        limit: 5,
        signal: controller.signal,
      })
        .then((results) => {
          setAddressSuggestions(results);
        })
        .catch((error: unknown) => {
          if (error instanceof DOMException && error.name === "AbortError") {
            return;
          }
          setAddressSuggestions([]);
        })
        .finally(() => {
          if (addressSuggestionsAbortRef.current === controller) {
            setIsSearchingAddressSuggestions(false);
          }
        });
    }, ADDRESS_SUGGESTIONS_DEBOUNCE_MS);

    return () => {
      window.clearTimeout(debounceTimer);
    };
  }, [address, isAddressInputFocused]);

  const applyPointSelection = (point: LatLngLiteral) => {
    setSelectedPoint(point);
    setMapError(null);
    setValue("latitude", Number(point.lat.toFixed(6)), { shouldValidate: true });
    setValue("longitude", Number(point.lng.toFixed(6)), { shouldValidate: true });
  };

  const autoFillAddressFromCoordinates = async (point: LatLngLiteral) => {
    reverseGeocodeAbortRef.current?.abort();
    const controller = new AbortController();
    reverseGeocodeAbortRef.current = controller;

    setIsLocatingAddress(true);
    setMapError(null);

    try {
      const geocodedAddress = await reverseGeocodeCoordinates(point.lat, point.lng, {
        signal: controller.signal,
      });

      if (!geocodedAddress) {
        setMapError(
          "Pudimos guardar el punto en el mapa, pero no encontramos una dirección para esas coordenadas.",
        );
        return;
      }

      setValue("address", geocodedAddress.displayName, {
        shouldDirty: true,
        shouldValidate: true,
      });
    } catch (error: unknown) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }

      setMapError(
        "Pudimos guardar el punto en el mapa, pero falló la búsqueda automática de la dirección.",
      );
    } finally {
      if (reverseGeocodeAbortRef.current === controller) {
        setIsLocatingAddress(false);
      }
    }
  };

  const handlePointSelection = (point: LatLngLiteral) => {
    applyPointSelection(point);
    void autoFillAddressFromCoordinates(point);
  };

  const handleAddressSuggestionSelection = (suggestion: GeocodingSuggestion) => {
    setValue("address", suggestion.displayName, {
      shouldDirty: true,
      shouldValidate: true,
    });
    applyPointSelection({
      lat: suggestion.latitude,
      lng: suggestion.longitude,
    });
    setAddressSuggestions([]);
    setIsAddressInputFocused(false);
  };

  const handleAddressLookup = async () => {
    const addressQuery = getValues("address").trim();
    if (!addressQuery) {
      setMapError("Ingresá una dirección antes de buscar en el mapa.");
      return;
    }

    setIsLocatingAddress(true);
    setMapError(null);

    try {
      const results = await searchAddressSuggestions(addressQuery, {
        limit: 1,
      });

      if (results.length === 0) {
        setMapError(
          "No encontramos la dirección. Ajustá el texto o seleccioná manualmente en el mapa.",
        );
        return;
      }

      const firstResult = results[0];
      setValue("address", firstResult.displayName, {
        shouldDirty: true,
        shouldValidate: true,
      });
      applyPointSelection({ lat: firstResult.latitude, lng: firstResult.longitude });
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
            Marcá el punto exacto en el mapa para ubicar mejor la dirección.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" noValidate onSubmit={onSubmit}>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="name">Nombre</Label>
                <Input
                  id="name"
                  placeholder="Sucursal Centro"
                  {...register("name", {
                    required: "El nombre es obligatorio.",
                    maxLength: {
                      value: 255,
                      message: "El nombre no puede superar los 255 caracteres.",
                    },
                    setValueAs: (value: string) => value.trim(),
                    validate: (value) =>
                      value.trim().length > 0 || "El nombre no puede estar vacío.",
                  })}
                />
                {errors.name ? <p className="text-sm text-destructive">{errors.name.message}</p> : null}
              </div>

              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="address">Dirección</Label>
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start">
                  <div className="relative flex-1">
                    <Input
                      autoComplete="off"
                      id="address"
                      onBlur={(event) => {
                        onAddressFieldBlur(event);
                        window.setTimeout(() => {
                          setIsAddressInputFocused(false);
                        }, 120);
                      }}
                      onFocus={() => {
                        setIsAddressInputFocused(true);
                      }}
                      placeholder="Av. Corrientes 1234, CABA"
                      {...addressFieldRegistration}
                    />
                    {showAddressSuggestions ? (
                      <div className="absolute z-20 mt-1 max-h-56 w-full overflow-y-auto rounded-md border bg-background shadow-md">
                        {isSearchingAddressSuggestions ? (
                          <p className="px-3 py-2 text-sm text-muted-foreground">
                            Buscando direcciones...
                          </p>
                        ) : null}
                        {!isSearchingAddressSuggestions && addressSuggestions.length === 0 ? (
                          <p className="px-3 py-2 text-sm text-muted-foreground">
                            No encontramos sugerencias para esta búsqueda.
                          </p>
                        ) : null}
                        {addressSuggestions.map((suggestion) => (
                          <button
                            className="w-full px-3 py-2 text-left text-sm hover:bg-muted"
                            key={`${suggestion.latitude}-${suggestion.longitude}-${suggestion.displayName}`}
                            onMouseDown={(event) => {
                              event.preventDefault();
                              handleAddressSuggestionSelection(suggestion);
                            }}
                            type="button"
                          >
                            {suggestion.displayName}
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>
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
                  Hacé click en el mapa para marcar el punto exacto. La dirección se completa automáticamente.
                </p>
                <p className="text-sm">
                  Punto en mapa: {selectedPoint ? "marcado" : "sin marcar"}
                </p>
                {mapError ? <p className="text-sm text-destructive">{mapError}</p> : null}
              </div>

              <div className="space-y-2">
                <Label htmlFor="contact_name">Contacto</Label>
                <Input
                  id="contact_name"
                  placeholder="Nombre y apellido"
                  {...register("contact_name", {
                    maxLength: {
                      value: 255,
                      message: "El contacto no puede superar los 255 caracteres.",
                    },
                    setValueAs: (value: string) => value.trim(),
                  })}
                />
                {errors.contact_name ? (
                  <p className="text-sm text-destructive">{errors.contact_name.message}</p>
                ) : null}
              </div>

              <div className="space-y-2">
                <Label htmlFor="contact_phone">Teléfono</Label>
                <Input
                  id="contact_phone"
                  placeholder="+54 11 1234-5678"
                  {...register("contact_phone", {
                    maxLength: {
                      value: 50,
                      message: "El teléfono no puede superar los 50 caracteres.",
                    },
                    setValueAs: (value: string) => value.trim(),
                    validate: (value) => {
                      if (!value) {
                        return true;
                      }

                      return PHONE_PATTERN.test(value)
                        || "Ingresá un teléfono válido (números, espacios, +, -, paréntesis).";
                    },
                  })}
                />
                {errors.contact_phone ? (
                  <p className="text-sm text-destructive">{errors.contact_phone.message}</p>
                ) : null}
              </div>

              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="contact_email">Email de contacto</Label>
                <Input
                  id="contact_email"
                  placeholder="contacto@negocio.com"
                  type="email"
                  {...register("contact_email", {
                    maxLength: {
                      value: 320,
                      message: "El email no puede superar los 320 caracteres.",
                    },
                    setValueAs: (value: string) => value.trim(),
                    validate: (value) => {
                      if (!value) {
                        return true;
                      }

                      const isValidEmail = EMAIL_PATTERN.test(value);
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
