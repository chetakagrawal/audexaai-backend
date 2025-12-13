"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    ENV: str = "dev"

    # API Configuration
    API_PREFIX: str = "/api"

    # Database Configuration
    DATABASE_URL: str = "postgresql+psycopg://user:password@localhost:5432/audexa"

    # JWT Configuration
    JWT_SECRET: str = "dev-secret"
    JWT_ALGORITHM: str = "HS256"
    
    # Application Environment
    APP_ENV: str = "dev"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Global settings instance
settings = Settings()

# Validate production JWT secret
if settings.APP_ENV == "production" and settings.JWT_SECRET == "dev-secret":
    raise ValueError(
        "JWT_SECRET must be changed from default 'dev-secret' in production environment"
    )

