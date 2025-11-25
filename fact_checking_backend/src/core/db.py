from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection

from src.core.config import get_env_settings

_motor_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> None:
    """Create global Motor client and database on app startup."""
    global _motor_client, _db
    settings = get_env_settings()
    _motor_client = AsyncIOMotorClient(settings.MONGO_URI)
    _db = _motor_client[settings.MONGO_DB]


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
