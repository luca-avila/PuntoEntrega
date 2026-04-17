from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    LOG_REQUESTS: bool = True
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    FRONTEND_URL: str = "http://localhost:5173"
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = ""

    NOTIFICATION_WORKER_POLL_INTERVAL_SECONDS: float = 5.0
    NOTIFICATION_WORKER_BATCH_SIZE: int = 10
    NOTIFICATION_OUTBOX_MAX_ATTEMPTS: int = 5
    NOTIFICATION_OUTBOX_RETRY_BASE_DELAY_SECONDS: float = 60.0
    NOTIFICATION_OUTBOX_PROCESSING_TIMEOUT_SECONDS: int = 300

    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    INVITATION_EXPIRATION_HOURS: int = 72


settings = Settings()
