import uuid
from typing import Any

from features.notifications.errors import NonRetryableNotificationError


def require_payload_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise NonRetryableNotificationError(f"Missing notification payload field: {key}")
    return value.strip()


def require_payload_uuid(payload: dict[str, Any], key: str) -> uuid.UUID:
    try:
        return uuid.UUID(require_payload_str(payload, key))
    except ValueError as exc:
        raise NonRetryableNotificationError(
            f"Invalid notification payload UUID field: {key}"
        ) from exc
