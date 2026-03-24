const NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org";
const GOOGLE_GEOCODING_API_URL = "https://maps.googleapis.com/maps/api/geocode/json";
const ARGENTINA_COUNTRY_CODE = "ar";
const GOOGLE_ARGENTINA_COUNTRY_CODE = "AR";
const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY?.trim() ?? "";

interface SearchNominatimItem {
  display_name?: string;
  lat?: string;
  lon?: string;
  address?: NominatimAddress;
}

interface ReverseNominatimItem {
  display_name?: string;
  lat?: string;
  lon?: string;
  address?: NominatimAddress;
}

interface NominatimAddress {
  country_code?: string;
  house_number?: string;
  road?: string;
  pedestrian?: string;
  footway?: string;
  street?: string;
  suburb?: string;
  neighbourhood?: string;
  city_district?: string;
  city?: string;
  town?: string;
  village?: string;
  hamlet?: string;
  municipality?: string;
  county?: string;
  state?: string;
}

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

function buildStreetLabel(address?: NominatimAddress): string | null {
  if (!address) {
    return null;
  }

  const street = firstNonEmpty([
    address.road,
    address.pedestrian,
    address.footway,
    address.street,
  ]);
  const houseNumber = address.house_number?.trim() ?? "";

  if (street && houseNumber) {
    return `${street} ${houseNumber}`;
  }

  if (street) {
    return street;
  }

  if (houseNumber) {
    return houseNumber;
  }

  return null;
}

function buildLocalityLabel(address?: NominatimAddress): string | null {
  if (!address) {
    return null;
  }

  return firstNonEmpty([
    address.city,
    address.town,
    address.village,
    address.hamlet,
    address.municipality,
    address.suburb,
    address.neighbourhood,
    address.city_district,
    address.county,
    address.state,
  ]);
}

function buildCompactAddressLabel(
  displayName: string | undefined,
  address?: NominatimAddress,
): string | null {
  const streetLabel = buildStreetLabel(address);
  const localityLabel = buildLocalityLabel(address);

  if (streetLabel && localityLabel) {
    return `${streetLabel}, ${localityLabel}`;
  }

  if (streetLabel) {
    return streetLabel;
  }

  if (localityLabel) {
    return localityLabel;
  }

  return compactDisplayName(displayName);
}

function isArgentinaAddress(address?: NominatimAddress): boolean {
  const countryCode = address?.country_code?.toLowerCase();
  if (!countryCode) {
    return true;
  }

  return countryCode === ARGENTINA_COUNTRY_CODE;
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

function shouldUseGoogleGeocoding(): boolean {
  return GOOGLE_MAPS_API_KEY.length > 0;
}

async function fetchNominatimJson<T>(
  path: string,
  params: Record<string, string>,
  options: GeocodingRequestOptions = {},
): Promise<T> {
  const query = new URLSearchParams({
    format: "jsonv2",
    ...params,
  });

  const response = await fetch(`${NOMINATIM_BASE_URL}${path}?${query.toString()}`, {
    signal: options.signal,
  });

  if (!response.ok) {
    throw new Error("Nominatim request failed.");
  }

  return (await response.json()) as T;
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
    throw new Error("Google geocoding request failed.");
  }

  const payload = (await response.json()) as GoogleGeocodeResponse;
  if (payload.status !== "OK" && payload.status !== "ZERO_RESULTS") {
    const errorDetail = payload.error_message ? ` (${payload.error_message})` : "";
    throw new Error(`Google geocoding request failed: ${payload.status}${errorDetail}`);
  }

  return payload;
}

function normalizeSearchResultsFromNominatim(results: SearchNominatimItem[]): GeocodingSuggestion[] {
  return results
    .map((item) => {
      const latitude = parseCoordinate(item.lat);
      const longitude = parseCoordinate(item.lon);
      const compactDisplay = buildCompactAddressLabel(item.display_name, item.address);
      const fullAddress = normalizeDisplayName(item.display_name) ?? compactDisplay;

      if (
        !fullAddress ||
        latitude === null ||
        longitude === null ||
        !isArgentinaAddress(item.address)
      ) {
        return null;
      }

      return {
        fullAddress,
        displayName: compactDisplay ?? fullAddress,
        latitude,
        longitude,
        hasHouseNumber: Boolean(item.address?.house_number?.trim()),
      };
    })
    .filter((result): result is GeocodingSuggestion => result !== null);
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

async function searchAddressSuggestionsWithNominatim(
  query: string,
  options: GeocodingRequestOptions & { limit?: number } = {},
): Promise<GeocodingSuggestion[]> {
  const response = await fetchNominatimJson<SearchNominatimItem[]>(
    "/search",
    {
      q: query,
      limit: String(options.limit ?? 5),
      addressdetails: "1",
      countrycodes: ARGENTINA_COUNTRY_CODE,
      "accept-language": "es",
    },
    options,
  );

  return normalizeSearchResultsFromNominatim(response);
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

async function reverseGeocodeCoordinatesWithNominatim(
  latitude: number,
  longitude: number,
  options: GeocodingRequestOptions = {},
): Promise<GeocodingSuggestion | null> {
  const response = await fetchNominatimJson<ReverseNominatimItem>(
    "/reverse",
    {
      lat: String(latitude),
      lon: String(longitude),
      zoom: "18",
      addressdetails: "1",
    },
    options,
  );

  const parsedLatitude = parseCoordinate(response.lat);
  const parsedLongitude = parseCoordinate(response.lon);
  const compactDisplay = buildCompactAddressLabel(response.display_name, response.address);
  const fullAddress = normalizeDisplayName(response.display_name) ?? compactDisplay;

  if (
    !fullAddress ||
    parsedLatitude === null ||
    parsedLongitude === null ||
    !isArgentinaAddress(response.address)
  ) {
    return null;
  }

  return {
    fullAddress,
    displayName: compactDisplay ?? fullAddress,
    latitude: parsedLatitude,
    longitude: parsedLongitude,
    hasHouseNumber: Boolean(response.address?.house_number?.trim()),
  };
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

export async function searchAddressSuggestions(
  query: string,
  options: GeocodingRequestOptions & { limit?: number } = {},
): Promise<GeocodingSuggestion[]> {
  const trimmedQuery = query.trim();
  if (!trimmedQuery) {
    return [];
  }

  if (shouldUseGoogleGeocoding()) {
    try {
      return await searchAddressSuggestionsWithGoogle(trimmedQuery, options);
    } catch {
      return searchAddressSuggestionsWithNominatim(trimmedQuery, options);
    }
  }

  return searchAddressSuggestionsWithNominatim(trimmedQuery, options);
}

export async function reverseGeocodeCoordinates(
  latitude: number,
  longitude: number,
  options: GeocodingRequestOptions = {},
): Promise<GeocodingSuggestion | null> {
  if (shouldUseGoogleGeocoding()) {
    try {
      return await reverseGeocodeCoordinatesWithGoogle(latitude, longitude, options);
    } catch {
      return reverseGeocodeCoordinatesWithNominatim(latitude, longitude, options);
    }
  }

  return reverseGeocodeCoordinatesWithNominatim(latitude, longitude, options);
}
