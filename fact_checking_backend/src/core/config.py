import os
from functools import lru_cache
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    APP_NAME: str = Field(default="VeriCheck Fact Checking API", description="Application display name")
    APP_VERSION: str = Field(default="0.1.0", description="Application version")

    MONGO_URI: str = Field(..., description="MongoDB connection string")
    MONGO_DB: str = Field(..., description="MongoDB database name")

    JWT_SECRET: str = Field(..., description="Secret for signing JWTs")
    JWT_EXPIRES_MIN: int = Field(default=60 * 24, description="JWT expiry in minutes")

    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["*"], description="Allowed CORS origins")
    WS_ALLOWED_ORIGINS: List[str] = Field(default_factory=lambda: ["*"], description="Allowed WebSocket origins")

    GSC_API_KEY: Optional[str] = Field(default=None, description="Google Search Console API key (optional)")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    PROCESSING_POLL_INTERVAL_MS: int = Field(default=300, description="Background processing sleep interval in ms")

    @field_validator("CORS_ORIGINS", "WS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_csv_list(cls, v):
        if v is None:
            return ["*"]
        if isinstance(v, list):
            return v
        # split by comma and strip
        return [item.strip() for item in str(v).split(",") if item.strip()]

    class Config:
        extra = "ignore"


# PUBLIC_INTERFACE
def get_env_settings() -> Settings:
    """Load and cache settings from environment variables.

    Returns:
        Settings: The application settings instance.
    """
    return _get_settings_cached()


@lru_cache
def _get_settings_cached() -> Settings:
    # Map env vars to pydantic model
    data = {
        "APP_NAME": os.getenv("APP_NAME", "VeriCheck Fact Checking API"),
        "APP_VERSION": os.getenv("APP_VERSION", "0.1.0"),
        "MONGO_URI": os.getenv("MONGO_URI", ""),
        "MONGO_DB": os.getenv("MONGO_DB", ""),
        "JWT_SECRET": os.getenv("JWT_SECRET", ""),
        "JWT_EXPIRES_MIN": int(os.getenv("JWT_EXPIRES_MIN", "1440")),
        "CORS_ORIGINS": os.getenv("CORS_ORIGINS", "*"),
        "WS_ALLOWED_ORIGINS": os.getenv("WS_ALLOWED_ORIGINS", "*"),
        "GSC_API_KEY": os.getenv("GSC_API_KEY", None),
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        "PROCESSING_POLL_INTERVAL_MS": int(os.getenv("PROCESSING_POLL_INTERVAL_MS", "300")),
    }
    return Settings(**data)
