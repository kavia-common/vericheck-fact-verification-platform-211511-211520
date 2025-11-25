import os
from functools import lru_cache
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

load_dotenv()


def _build_mongo_uri_from_parts() -> Optional[str]:
    """Construct a MongoDB URI from discrete env vars if possible.

    Uses the following variables:
      - MONGO_HOST (comma-separated allowed)
      - MONGO_PORT (single port applied to all hosts if provided)
      - MONGO_USER (optional)
      - MONGO_PASSWORD (optional)
      - MONGO_DB (database name for default path)
      - MONGO_PARAMS (optional extra query string, without leading '?')

    Returns:
      A constructed URI string or None if not enough information is present.
    """
    host = os.getenv("MONGO_HOST", "") or ""
    port = os.getenv("MONGO_PORT", "") or ""
    user = os.getenv("MONGO_USER", "") or ""
    password = os.getenv("MONGO_PASSWORD", "") or ""
    db = os.getenv("MONGO_DB", "") or ""
    params = os.getenv("MONGO_PARAMS", "") or ""

    # Normalize and filter host list; remove empty entries and trailing commas.
    host_parts = [h.strip() for h in host.split(",") if h.strip()]
    if not host_parts:
        return None

    # attach :port to each host if provided
    if port.strip():
        host_parts = [f"{h}:{port.strip()}" if ":" not in h else h for h in host_parts]

    # auth segment
    auth = ""
    if user.strip():
        # URL-escaping left to Mongo driver; avoid leaking password in logs later
        if password.strip():
            auth = f"{user.strip()}:{password.strip()}@"
        else:
            auth = f"{user.strip()}@"

    # database path
    db_path = f"/{db.strip()}" if db.strip() else ""

    query = f"?{params.strip()}" if params.strip() else ""

    return f"mongodb://{auth}{','.join(host_parts)}{db_path}{query}"


def _sanitize_effective_target(uri: str, db_name: str) -> str:
    """Return a safe-to-log summary like 'mongodb://<auth-redacted>@host1,host2/<db>'."""
    try:
        # Strip protocol
        rest = uri.split("://", 1)[1] if "://" in uri else uri
        # Separate credentials and host/db
        if "@" in rest:
            creds, tail = rest.split("@", 1)
            creds_redacted = "<auth-redacted>@"
        else:
            tail = rest
            creds_redacted = ""
        # Trim query
        tail_no_query = tail.split("?", 1)[0]
        # Remove path db if present; we'll show provided db_name explicitly
        tail_host_only = tail_no_query.split("/", 1)[0]
        return f"mongodb://{creds_redacted}{tail_host_only}/{db_name}"
    except Exception:
        # Fallback minimal
        return f"mongodb://<redacted>/{db_name}"


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    APP_NAME: str = Field(default="VeriCheck Fact Checking API", description="Application display name")
    APP_VERSION: str = Field(default="0.1.0", description="Application version")

    MONGO_URI: str = Field(default="", description="MongoDB connection string")
    MONGO_DB: str = Field(default="", description="MongoDB database name")

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

    @field_validator("MONGO_URI", mode="after")
    @classmethod
    def validate_or_build_mongo_uri(cls, v, info):
        """Build URI from parts if missing or malformed and enforce no empty hosts."""
        raw_uri = (v or "").strip()

        # If provided, sanitize trivial mistakes like trailing comma in host list.
        def _trim_trailing_commas(s: str) -> str:
            if "://" in s:
                proto, rest = s.split("://", 1)
            else:
                proto, rest = "", s
            # Remove query to focus on hosts
            rest_main, sep, query = rest.partition("?")
            # Remove auth to isolate hosts portion
            hosts_part = rest_main.split("@", 1)[-1]
            path_split = hosts_part.split("/", 1)
            hosts_only = path_split[0].strip(", ")
            while hosts_only.endswith(","):
                hosts_only = hosts_only[:-1]
            rest_main_fixed = rest_main.replace(path_split[0], hosts_only, 1)
            fixed = f"{proto+'://' if proto else ''}{rest_main_fixed}{sep}{query}"
            return fixed

        if raw_uri:
            fixed = _trim_trailing_commas(raw_uri)
        else:
            fixed = ""

        # If still missing, try to build from parts
        if not fixed:
            constructed = _build_mongo_uri_from_parts()
            fixed = constructed or ""

        # Validate presence of hosts
        if not fixed:
            # Not enough info, but allow db module to raise clearer error later
            return fixed

        # Preflight host list non-empty
        # Extract hosts segment
        try:
            after_proto = fixed.split("://", 1)[1] if "://" in fixed else fixed
            after_auth = after_proto.split("@", 1)[-1]
            host_segment = after_auth.split("/", 1)[0]
            hosts = [h.strip() for h in host_segment.split(",") if h.strip()]
            if not hosts:
                raise ValueError("Invalid MONGO_URI: empty host list. Check for extra/trailing commas.")
        except ValueError:
            raise
        except Exception:
            raise ValueError("Invalid MONGO_URI format. Please verify host list and syntax.")

        return fixed

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
