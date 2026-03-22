const NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org";
const ARGENTINA_COUNTRY_CODE = "ar";

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

interface NominatimRequestOptions {
  signal?: AbortSignal;
}

export interface GeocodingSuggestion {
  displayName: string;
  latitude: number;
  longitude: number;
}

function parseCoordinate(value: string | undefined): number | null {
  if (!value) {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function firstNonEmpty(values: Array<string | undefined>): string | null {
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

async function fetchNominatimJson<T>(
  path: string,
  params: Record<string, string>,
  options: NominatimRequestOptions = {},
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

function normalizeSearchResults(results: SearchNominatimItem[]): GeocodingSuggestion[] {
  return results
    .map((item) => {
      const latitude = parseCoordinate(item.lat);
      const longitude = parseCoordinate(item.lon);
      const displayName = buildCompactAddressLabel(item.display_name, item.address);

      if (
        !displayName ||
        latitude === null ||
        longitude === null ||
        !isArgentinaAddress(item.address)
      ) {
        return null;
      }

      return {
        displayName,
        latitude,
        longitude,
      };
    })
    .filter((result): result is GeocodingSuggestion => result !== null);
}

export async function searchAddressSuggestions(
  query: string,
  options: NominatimRequestOptions & { limit?: number } = {},
): Promise<GeocodingSuggestion[]> {
  const trimmedQuery = query.trim();
  if (!trimmedQuery) {
    return [];
  }

  const response = await fetchNominatimJson<SearchNominatimItem[]>(
    "/search",
    {
      q: trimmedQuery,
      limit: String(options.limit ?? 5),
      addressdetails: "1",
      countrycodes: ARGENTINA_COUNTRY_CODE,
      "accept-language": "es",
    },
    options,
  );

  return normalizeSearchResults(response);
}

export async function reverseGeocodeCoordinates(
  latitude: number,
  longitude: number,
  options: NominatimRequestOptions = {},
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
  const displayName = buildCompactAddressLabel(response.display_name, response.address);

  if (
    !displayName ||
    parsedLatitude === null ||
    parsedLongitude === null ||
    !isArgentinaAddress(response.address)
  ) {
    return null;
  }

  return {
    displayName,
    latitude: parsedLatitude,
    longitude: parsedLongitude,
  };
}
