const NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org";

interface SearchNominatimItem {
  display_name?: string;
  lat?: string;
  lon?: string;
}

interface ReverseNominatimItem {
  display_name?: string;
  lat?: string;
  lon?: string;
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

      if (!item.display_name || latitude === null || longitude === null) {
        return null;
      }

      return {
        displayName: item.display_name,
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
      addressdetails: "0",
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

  if (!response.display_name || parsedLatitude === null || parsedLongitude === null) {
    return null;
  }

  return {
    displayName: response.display_name,
    latitude: parsedLatitude,
    longitude: parsedLongitude,
  };
}
