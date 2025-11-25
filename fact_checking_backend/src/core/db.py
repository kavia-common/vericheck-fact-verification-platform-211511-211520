from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import ConfigurationError

from src.core.config import get_env_settings

_motor_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> None:
    """Create global Motor client and database on app startup.

    Validates the effective MONGO_URI before connecting and logs the target host and db
    (without revealing credentials). Provides actionable error messages when configuration
    issues are detected.
    """
    global _motor_client, _db
    settings = get_env_settings()

    uri = settings.MONGO_URI.strip()
    db_name = settings.MONGO_DB.strip()

    if not db_name:
        raise ValueError("MONGO_DB is required but not set. Please define MONGO_DB in environment.")

    # Log effective host/db without secrets
    try:
        # Attempt to reuse helper to sanitize; fallback simple redaction
        from src.core.config import _sanitize_effective_target  # type: ignore
        target = _sanitize_effective_target(uri, db_name)
    except Exception:
        target = f"mongodb://<redacted>/{db_name}"

    print(f"[DB] Initializing Mongo client -> {target}")

    try:
        _motor_client = AsyncIOMotorClient(uri)
        _db = _motor_client[db_name]
        # Trigger a lightweight command to validate connectivity and URI (optional ping)
        await _db.command({"ping": 1})
        print(f"[DB] MongoDB connection established to {target}")
    except ConfigurationError as ce:
        # Common cause: empty host due to trailing comma or malformed URI
        msg = (
            "MongoDB configuration error: "
            f"{str(ce)}. "
            "Please verify MONGO_URI. Ensure there are no trailing commas in host list. "
            "For single host use: mongodb://host:27017. "
            "For replica set, separate hosts by comma without trailing comma, e.g., "
            "mongodb://host1:27017,host2:27017,host3:27017. "
            "Alternatively, set MONGO_HOST, MONGO_PORT, MONGO_USER, MONGO_PASSWORD, MONGO_DB to let the app construct a valid URI."
        )
        print(f"[DB][ERROR] {msg}")
        raise
    except ValueError as ve:
        # Raised by settings validator when host list is empty or format invalid
        print(f"[DB][ERROR] {ve}")
        raise
    except Exception as e:
        print(f"[DB][ERROR] Unexpected error connecting to MongoDB: {e}")
        raise


async def close_mongo_connection() -> None:
    """Close Motor client on app shutdown."""
    global _motor_client, _db
    if _motor_client:
        _motor_client.close()
    _motor_client = None
    _db = None


# PUBLIC_INTERFACE
def get_db() -> AsyncIOMotorDatabase:
    """Get the active Mongo database handle.

    Returns:
        AsyncIOMotorDatabase: The MongoDB database instance.

    Raises:
        RuntimeError: If the database is not initialized yet.
    """
    if _db is None:
        raise RuntimeError("Database not initialized. Ensure startup hook executed.")
    return _db


# PUBLIC_INTERFACE
def collection_users() -> AsyncIOMotorCollection:
    """Users collection accessor."""
    return get_db()["users"]


# PUBLIC_INTERFACE
def collection_claims() -> AsyncIOMotorCollection:
    """Claims collection accessor."""
    return get_db()["claims"]


# PUBLIC_INTERFACE
def collection_sources() -> AsyncIOMotorCollection:
    """Sources collection accessor."""
    return get_db()["sources"]


# PUBLIC_INTERFACE
def collection_analyses() -> AsyncIOMotorCollection:
    """Analyses collection accessor."""
    return get_db()["analyses"]


# PUBLIC_INTERFACE
def collection_metrics_daily() -> AsyncIOMotorCollection:
    """Daily metrics collection accessor."""
    return get_db()["metrics_daily"]
