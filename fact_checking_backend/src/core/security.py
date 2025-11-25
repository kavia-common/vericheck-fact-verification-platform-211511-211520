from datetime import datetime, timedelta, timezone
from typing import List, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from src.core.config import get_env_settings
from src.core.db import collection_users

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


class TokenData(BaseModel):
    """Represents data embedded in the JWT token."""

    sub: str = Field(..., description="User id")
    email: str = Field(..., description="User email")
    roles: List[str] = Field(default_factory=list, description="User roles")
    exp: int | None = Field(default=None, description="Expiry timestamp")


# PUBLIC_INTERFACE
def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


# PUBLIC_INTERFACE
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# PUBLIC_INTERFACE
def create_access_token(subject: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token.

    Args:
        subject: dict containing at least sub, email, roles.
        expires_delta: optional timedelta for expiry override.

    Returns:
        Encoded JWT string.
    """
    settings = get_env_settings()
    to_encode = subject.copy()
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_EXPIRES_MIN)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")
    return encoded_jwt


# PUBLIC_INTERFACE
def decode_token(token: str) -> TokenData:
    """Decode and validate JWT token."""
    settings = get_env_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return TokenData(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# PUBLIC_INTERFACE
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    """FastAPI dependency to resolve current user from Authorization: Bearer token."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token_data = decode_token(credentials.credentials)
    # Fetch user to ensure still exists
    user = await collection_users().find_one({"_id": token_data.sub})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    # Normalize fields returned
    return {
        "id": user["_id"],
        "email": user["email"],
        "roles": user.get("roles", []),
        "created_at": user.get("created_at"),
    }


# PUBLIC_INTERFACE
def require_roles(allowed_roles: list[str]):
    """Dependency factory to require that current user has one of allowed roles."""

    async def _checker(user: dict = Depends(get_current_user)) -> dict:
        roles = user.get("roles", [])
        if not any(role in roles for role in allowed_roles):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return _checker
