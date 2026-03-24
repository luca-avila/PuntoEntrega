const GOOGLE_GEOCODING_API_URL = "https://maps.googleapis.com/maps/api/geocode/json";
const ARGENTINA_COUNTRY_CODE = "ar";
const GOOGLE_ARGENTINA_COUNTRY_CODE = "AR";
const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY?.trim() ?? "";

interface GoogleGeocodeResponse {
  status: string;
  error_message?: string;
  results: GoogleGeocodeResult[];
}

interface GoogleGeocodeResult {
  formatted_address?: string;
  address_components?: GoogleAddressComponent[];
  types?: string[];
  geometry?: {
    location?: {
      lat?: number;
      lng?: number;
    };
    location_type?: string;
  };
}

interface GoogleAddressComponent {
  long_name?: string;
  short_name?: string;
  types?: string[];
}

interface GeocodingRequestOptions {
  signal?: AbortSignal;
}

export interface GeocodingSuggestion {
  fullAddress: string;
  displayName: string;
  latitude: number;
  longitude: number;
  hasHouseNumber: boolean;
}

export class GeocodingError extends Error {
  readonly code: "missing_api_key" | "provider_error";

  constructor(code: "missing_api_key" | "provider_error", message: string) {
    super(message);
    this.name = "GeocodingError";
    this.code = code;
  }
}

function parseCoordinate(value: string | number | undefined): number | null {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }

  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  return null;
}

function firstNonEmpty(values: Array<string | undefined | null>): string | null {
  for (const value of values) {
    const trimmed = value?.trim();
    if (trimmed) {
      return trimmed;
    }
  }

  return null;
}

function compactDisplayName(displayName: string | undefined): string | null {
  if (!displayName) {
    return null;
  }

  const parts = displayName
    .split(",")
    .map((part) => part.trim())
    .filter((part) => part.length > 0);

  if (parts.length === 0) {
    return null;
  }

  return parts.slice(0, 2).join(", ");
}

function normalizeDisplayName(value: string | undefined): string | null {
  const normalized = value?.trim();
  if (!normalized) {
    return null;
  }

  return normalized;
}

function getGoogleAddressComponent(
  result: GoogleGeocodeResult,
  componentType: string,
): GoogleAddressComponent | null {
  const components = result.address_components ?? [];
  for (const component of components) {
    if (component.types?.includes(componentType)) {
      return component;
    }
  }

  return null;
}

function getGoogleComponentLongName(
  result: GoogleGeocodeResult,
  componentType: string,
): string | null {
  const value = getGoogleAddressComponent(result, componentType)?.long_name?.trim();
  return value && value.length > 0 ? value : null;
}

function getGoogleComponentShortName(
  result: GoogleGeocodeResult,
  componentType: string,
): string | null {
  const value = getGoogleAddressComponent(result, componentType)?.short_name?.trim();
  return value && value.length > 0 ? value : null;
}

function googleHasHouseNumber(result: GoogleGeocodeResult): boolean {
  return Boolean(getGoogleComponentLongName(result, "street_number"));
}

function isGoogleResultInArgentina(result: GoogleGeocodeResult): boolean {
  const countryCode = getGoogleComponentShortName(result, "country");
  if (!countryCode) {
    return true;
  }

  return countryCode.toUpperCase() === GOOGLE_ARGENTINA_COUNTRY_CODE;
}

function buildGoogleDisplayName(result: GoogleGeocodeResult): string | null {
  const street = getGoogleComponentLongName(result, "route");
  const streetNumber = getGoogleComponentLongName(result, "street_number");
  const locality = firstNonEmpty([
    getGoogleComponentLongName(result, "locality"),
    getGoogleComponentLongName(result, "sublocality"),
    getGoogleComponentLongName(result, "administrative_area_level_2"),
    getGoogleComponentLongName(result, "administrative_area_level_1"),
  ]);

  if (street && streetNumber && locality) {
    return `${street} ${streetNumber}, ${locality}`;
  }

  if (street && streetNumber) {
    return `${street} ${streetNumber}`;
  }

  if (street && locality) {
    return `${street}, ${locality}`;
  }

  return compactDisplayName(result.formatted_address);
}

function getGoogleLocationTypeScore(locationType: string | undefined): number {
  switch (locationType) {
    case "ROOFTOP":
      return 4;
    case "RANGE_INTERPOLATED":
      return 3;
    case "GEOMETRIC_CENTER":
      return 2;
    case "APPROXIMATE":
      return 1;
    default:
      return 0;
  }
}

function getGoogleResultTypeScore(types: string[] | undefined): number {
  if (!types || types.length === 0) {
    return 0;
  }

  if (types.includes("street_address")) {
    return 4;
  }
  if (types.includes("premise")) {
    return 3;
  }
  if (types.includes("subpremise")) {
    return 2;
  }
  if (types.includes("route")) {
    return 1;
  }

  return 0;
}

function ensureGoogleApiKeyConfigured(): void {
  if (GOOGLE_MAPS_API_KEY.length > 0) {
    return;
  }

  throw new GeocodingError(
    "missing_api_key",
    "Falta configurar VITE_GOOGLE_MAPS_API_KEY para usar el geocodificador de Google.",
  );
}

async function fetchGoogleGeocodingJson(
  params: Record<string, string>,
  options: GeocodingRequestOptions = {},
): Promise<GoogleGeocodeResponse> {
  const query = new URLSearchParams({
    key: GOOGLE_MAPS_API_KEY,
    language: "es",
    ...params,
  });

  const response = await fetch(`${GOOGLE_GEOCODING_API_URL}?${query.toString()}`, {
    signal: options.signal,
  });

  if (!response.ok) {
    throw new GeocodingError("provider_error", "La solicitud a Google Geocoding falló.");
  }

  const payload = (await response.json()) as GoogleGeocodeResponse;
  if (payload.status !== "OK" && payload.status !== "ZERO_RESULTS") {
    const errorDetail = payload.error_message ? ` (${payload.error_message})` : "";
    throw new GeocodingError(
      "provider_error",
      `Google Geocoding devolvió ${payload.status}${errorDetail}`,
    );
  }

  return payload;
}

function normalizeResultsFromGoogle(results: GoogleGeocodeResult[]): GeocodingSuggestion[] {
  const parsedResults = results
    .map((result) => {
      const fullAddress = normalizeDisplayName(result.formatted_address);
      const latitude = parseCoordinate(result.geometry?.location?.lat);
      const longitude = parseCoordinate(result.geometry?.location?.lng);

      if (!fullAddress || latitude === null || longitude === null || !isGoogleResultInArgentina(result)) {
        return null;
      }

      const hasHouseNumber = googleHasHouseNumber(result);
      const displayName = buildGoogleDisplayName(result) ?? fullAddress;
      const qualityScore =
        (hasHouseNumber ? 1000 : 0)
        + getGoogleLocationTypeScore(result.geometry?.location_type) * 100
        + getGoogleResultTypeScore(result.types);

      return {
        suggestion: {
          fullAddress,
          displayName,
          latitude,
          longitude,
          hasHouseNumber,
        },
        qualityScore,
      };
    })
    .filter((result): result is { suggestion: GeocodingSuggestion; qualityScore: number } => result !== null);

  parsedResults.sort((left, right) => right.qualityScore - left.qualityScore);
  return parsedResults.map((result) => result.suggestion);
}

async function searchAddressSuggestionsWithGoogle(
  query: string,
  options: GeocodingRequestOptions & { limit?: number } = {},
): Promise<GeocodingSuggestion[]> {
  const response = await fetchGoogleGeocodingJson(
    {
      address: query,
      region: ARGENTINA_COUNTRY_CODE,
      components: `country:${GOOGLE_ARGENTINA_COUNTRY_CODE}`,
    },
    options,
  );

  if (response.status === "ZERO_RESULTS") {
    return [];
  }

  const suggestions = normalizeResultsFromGoogle(response.results);
  return suggestions.slice(0, options.limit ?? 5);
}

async function reverseGeocodeCoordinatesWithGoogle(
  latitude: number,
  longitude: number,
  options: GeocodingRequestOptions = {},
): Promise<GeocodingSuggestion | null> {
  const response = await fetchGoogleGeocodingJson(
    {
      latlng: `${latitude},${longitude}`,
      region: ARGENTINA_COUNTRY_CODE,
      result_type: "street_address|premise|subpremise|route",
      location_type: "ROOFTOP|RANGE_INTERPOLATED|GEOMETRIC_CENTER|APPROXIMATE",
    },
    options,
  );

  if (response.status === "ZERO_RESULTS") {
    return null;
  }

  const suggestions = normalizeResultsFromGoogle(response.results);
  return suggestions[0] ?? null;
}

export function getGeocodingErrorMessage(error: unknown, fallbackMessage: string): string {
  if (!(error instanceof Error)) {
    return fallbackMessage;
  }

  const message = error.message.toLowerCase();

  if (error instanceof GeocodingError && error.code === "missing_api_key") {
    return error.message;
  }

  if (message.includes("expired")) {
    return "La API key de Google está expirada. Generá una nueva key válida y reiniciá Vite.";
  }

  if (message.includes("request_denied")) {
    return "Google rechazó la API key. Revisá permisos, restricciones y APIs habilitadas.";
  }

  if (message.includes("over_query_limit")) {
    return "Google alcanzó el límite de consultas. Revisá cuota y facturación del proyecto.";
  }

  if (message.includes("invalid_request")) {
    return "Google rechazó la solicitud de geocodificación. Revisá la dirección ingresada.";
  }

  if (message.includes("api key") || message.includes("geocoding")) {
    return error.message;
  }

  return fallbackMessage;
}

export async function searchAddressSuggestions(
  query: string,
  options: GeocodingRequestOptions & { limit?: number } = {},
): Promise<GeocodingSuggestion[]> {
  const trimmedQuery = query.trim();
  if (!trimmedQuery) {
    return [];
  }

  ensureGoogleApiKeyConfigured();
  return searchAddressSuggestionsWithGoogle(trimmedQuery, options);
}

export async function reverseGeocodeCoordinates(
  latitude: number,
  longitude: number,
  options: GeocodingRequestOptions = {},
): Promise<GeocodingSuggestion | null> {
  ensureGoogleApiKeyConfigured();
  return reverseGeocodeCoordinatesWithGoogle(latitude, longitude, options);
}
