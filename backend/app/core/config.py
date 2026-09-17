"""
Centralized application configuration.

All tunable values (secrets, expiry windows, CORS origins, seed credentials)
are read from environment variables / .env so nothing sensitive or
environment-specific is hard-coded in application logic.
"""
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "SIH26105 Cyber Risk Platform"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    SECRET_KEY: str = "insecure-dev-key-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080

    DATABASE_URL: str = (
        "postgresql+psycopg2://sih_admin:sih_password@localhost:5432/sih_cyber_risk"
    )
    REDIS_URL: str = "redis://localhost:6379/0"

    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    SEED_ADMIN_EMAIL: str = "admin@sih2026.example"
    SEED_ADMIN_PASSWORD: str = "Admin@12345"
    SEED_ORG_NAME: str = "Demo Financial Services Ltd"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
