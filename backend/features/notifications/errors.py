class EmailSendError(RuntimeError):
    """Raised when an outbound email cannot be dispatched."""


class NonRetryableNotificationError(RuntimeError):
    """Raised when retrying the notification cannot make it succeed."""
