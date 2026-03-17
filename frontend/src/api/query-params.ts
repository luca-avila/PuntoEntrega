type QueryPrimitive = string | number | boolean;
type QueryValue = QueryPrimitive | null | undefined;

export type QueryParams = Record<string, QueryValue>;

export function buildQueryParams(params: QueryParams): string {
  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) {
      continue;
    }

    searchParams.set(key, String(value));
  }

  const query = searchParams.toString();
  return query ? `?${query}` : "";
}
