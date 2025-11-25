from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_env_settings
from src.core.db import close_mongo_connection, connect_to_mongo
from src.api.routes.auth import router as auth_router
from src.api.routes.claims import router as claims_router
from src.api.routes.metrics import router as metrics_router
from src.api.routes.stream import router as stream_router


openapi_tags = [
    {"name": "auth", "description": "Authentication endpoints"},
    {"name": "claims", "description": "Claims submission and retrieval"},
    {"name": "stream", "description": "WebSocket live event stream"},
    {"name": "metrics", "description": "Analytics and operational metrics"},
]

settings = get_env_settings()
app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for the VeriCheck fact verification platform.",
    version=settings.APP_VERSION,
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    await connect_to_mongo()


@app.on_event("shutdown")
async def on_shutdown():
    await close_mongo_connection()


@app.get("/", tags=["auth"], summary="Health Check", description="Liveness check endpoint")
async def health_check():
    return {"message": "Healthy"}


# Routers
app.include_router(auth_router)
app.include_router(claims_router)
app.include_router(metrics_router)
app.include_router(stream_router)
