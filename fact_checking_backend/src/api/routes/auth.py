from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from src.core.db import collection_users
from src.core.security import create_access_token, get_current_user, hash_password, verify_password
from src.core.config import get_env_settings
from src.models.schemas import LoginRequest, RegisterRequest, TokenResponse, UserProfile

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _normalize_user_doc(doc: dict) -> UserProfile:
    return UserProfile(
        id=doc["_id"],
        email=doc["email"],
        roles=doc.get("roles", []),
        created_at=doc.get("created_at", datetime.utcnow()),
    )


@router.post(
    "/register",
    response_model=UserProfile,
    status_code=201,
    summary="Register a new user",
    description="Creates a new user with email and password and returns its profile.",
)
async def register(payload: RegisterRequest):
    """Register a new user.

    Body:
        email: Email address
        password: String (min 6 chars)

    Returns:
        UserProfile: Created user profile
    """
    existing = await collection_users().find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_doc = {
        "_id": payload.email.lower(),  # using email as id for simplicity
        "email": payload.email.lower(),
        "password_hash": hash_password(payload.password),
        "roles": ["user"],
        "created_at": datetime.utcnow(),
    }
    await collection_users().insert_one(user_doc)
    return _normalize_user_doc(user_doc)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Authenticate with email and password to obtain a JWT access token.",
)
async def login(payload: LoginRequest):
    """Authenticate user and return JWT token."""
    user = await collection_users().find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    settings = get_env_settings()
    expires_in = settings.JWT_EXPIRES_MIN * 60
    token = create_access_token({"sub": user["_id"], "email": user["email"], "roles": user.get("roles", [])})
    return TokenResponse(access_token=token, expires_in=expires_in, token_type="bearer")


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get current user profile",
    description="Returns the profile information for the currently authenticated user.",
)
async def me(user: dict = Depends(get_current_user)):
    """Get the profile for the current user."""
    user_doc = await collection_users().find_one({"_id": user["id"]})
    return _normalize_user_doc(user_doc)
