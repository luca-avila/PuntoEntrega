from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Deployment-provided values.
    DATABASE_URL: str = Field(min_length=1)
    SECRET_KEY: str = Field(min_length=32)
    RESEND_API_KEY: str = Field(min_length=1)
    EMAIL_FROM: str = Field(min_length=1)

    # Application runtime.
    ENVIRONMENT: str = Field(min_length=1)
    LOG_LEVEL: str = Field(min_length=1)
    LOG_REQUESTS: bool
    CORS_ORIGINS: list[str] = Field(min_length=1)
    FRONTEND_URL: str = Field(min_length=1)

    # Notification outbox and worker tuning.
    NOTIFICATION_WORKER_POLL_INTERVAL_SECONDS: float = 5.0
    NOTIFICATION_WORKER_BATCH_SIZE: int = 10
    NOTIFICATION_OUTBOX_MAX_ATTEMPTS: int = 5
    NOTIFICATION_OUTBOX_RETRY_BASE_DELAY_SECONDS: float = 60.0
    NOTIFICATION_OUTBOX_PROCESSING_TIMEOUT_SECONDS: int = 300

    # Authentication and invitation policy.
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    INVITATION_EXPIRATION_HOURS: int = 72


settings = Settings()
