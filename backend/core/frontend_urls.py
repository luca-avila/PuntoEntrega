from urllib.parse import urlencode, urlsplit, urlunsplit

from core.config import settings


def normalize_frontend_base_url(raw_url: str) -> str:
    """Return a validated base frontend URL without query/fragment."""
    value = raw_url.strip()

    # Common misconfiguration: protocol accidentally repeated.
    for scheme in ("https://", "http://"):
        duplicated = f"{scheme}{scheme}"
        if value.startswith(duplicated):
            value = value[len(scheme) :]

    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError(
            "FRONTEND_URL must be an absolute http/https URL "
            f"(got: {raw_url!r})"
        )

    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def build_frontend_action_url(path: str, token: str) -> str:
    base = normalize_frontend_base_url(settings.FRONTEND_URL)
    route = path if path.startswith("/") else f"/{path}"
    return f"{base}{route}?{urlencode({'token': token})}"
