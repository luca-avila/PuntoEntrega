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

    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True


settings = Settings()
