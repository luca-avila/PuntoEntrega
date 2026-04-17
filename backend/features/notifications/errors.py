class NonRetryableNotificationError(RuntimeError):
    """Raised when retrying the notification cannot make it succeed."""
