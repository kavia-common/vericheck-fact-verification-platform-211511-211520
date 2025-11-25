from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field


# Auth
class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Password")


class UserProfile(BaseModel):
    id: str = Field(..., description="User id")
    email: EmailStr = Field(..., description="User email")
    roles: List[str] = Field(default_factory=list, description="User roles")
    created_at: datetime = Field(..., description="User creation timestamp")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="Password")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")


# Claims
class ClaimCreateRequest(BaseModel):
    text: str = Field(..., min_length=3, description="Claim text")
    metadata: Optional[dict] = Field(default=None, description="Optional additional metadata")


class SourceItem(BaseModel):
    id: Optional[str] = Field(default=None, description="Source id")
    claim_id: str = Field(..., description="Related claim id")
    title: str = Field(..., description="Source title")
    url: str = Field(..., description="Source URL")
    snippet: Optional[str] = Field(default=None, description="Short snippet or summary")
    reliability_score: float = Field(..., ge=0, le=1, description="Source reliability score [0..1]")
    stance: Literal["support", "refute", "neutral"] = Field(..., description="Source stance vs claim")
    provider: str = Field(..., description="Fetcher/provider name")
    fetched_at: datetime = Field(default_factory=datetime.utcnow, description="Fetch time")


class AnalysisSummary(BaseModel):
    id: Optional[str] = Field(default=None, description="Analysis id")
    claim_id: str = Field(..., description="Related claim id")
    summary: str = Field(..., description="Short natural language analysis")
    score: float = Field(..., ge=0, le=1, description="Overall veracity/confidence score [0..1]")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")


class ClaimStatus(BaseModel):
    status: Literal["queued", "processing", "triage", "fetch_sources", "analyze", "score", "complete", "failed"] = Field(
        ..., description="Processing status"
    )
    progress: int = Field(..., ge=0, le=100, description="Percent progress")
    stage: str = Field(..., description="Current pipeline stage")


class ClaimItem(BaseModel):
    id: str = Field(..., description="Claim id")
    text: str = Field(..., description="Claim text")
    status: str = Field(..., description="Status")
    user_id: str = Field(..., description="Creator user id")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update time")
    sources: List[SourceItem] = Field(default_factory=list, description="Related sources")
    analysis: Optional[AnalysisSummary] = Field(default=None, description="Analysis result")


class ClaimListResponse(BaseModel):
    items: List[ClaimItem] = Field(..., description="Items")
    total: int = Field(..., description="Total available")
    page: int = Field(..., description="Page number")
    size: int = Field(..., description="Page size")


class CreateClaimResponse(BaseModel):
    id: str = Field(..., description="Claim id")
    status: str = Field(..., description="Initial status")
    job_id: str = Field(..., description="Background job id")


# Metrics
class MetricsSummaryResponse(BaseModel):
    total_claims_24h: int = Field(..., description="Total number of claims in last 24h")
    avg_score_24h: float = Field(..., description="Average score in last 24h")
    p50_latency_ms: float = Field(..., description="50th percentile processing latency")
    p95_latency_ms: float = Field(..., description="95th percentile processing latency")
    success_rate: float = Field(..., description="Processing success rate in last 24h [0..1]")
