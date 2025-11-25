from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from src.core.db import collection_analyses, collection_claims, collection_sources
from src.core.security import get_current_user
from src.models.schemas import ClaimCreateRequest, ClaimItem, ClaimListResponse, ClaimStatus, CreateClaimResponse, SourceItem
from src.services.fact_check_service import process_claim
from src.api.routes.stream import ws_manager

router = APIRouter(prefix="/api/v1/claims", tags=["claims"])


def _serialize_source(doc: dict) -> SourceItem:
    return SourceItem(
        id=str(doc.get("_id")),
        claim_id=doc.get("claim_id"),
        title=doc.get("title"),
        url=doc.get("url"),
        snippet=doc.get("snippet"),
        reliability_score=float(doc.get("reliability_score", 0)),
        stance=doc.get("stance", "neutral"),
        provider=doc.get("provider", "unknown"),
        fetched_at=doc.get("fetched_at"),
    )


def _serialize_claim(doc: dict, sources: Optional[List[SourceItem]] = None, analysis: Optional[dict] = None) -> ClaimItem:
    return ClaimItem(
        id=str(doc.get("_id")),
        text=doc.get("text"),
        status=doc.get("status"),
        user_id=doc.get("user_id"),
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at", doc.get("created_at")),
        sources=sources or [],
        analysis=analysis,
    )


@router.post(
    "",
    response_model=CreateClaimResponse,
    summary="Create a claim",
    description="Creates a claim, enqueues background processing, and returns job id.",
)
async def create_claim(payload: ClaimCreateRequest, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    """Create a claim and start background processing."""
    claim_id = f"clm_{int(datetime.utcnow().timestamp() * 1000)}"
    doc = {
        "_id": claim_id,
        "text": payload.text,
        "metadata": payload.metadata or {},
        "status": "queued",
        "stage": "queued",
        "progress": 0,
        "user_id": user["id"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await collection_claims().insert_one(doc)
    await ws_manager.broadcast({"type": "claim_created", "claim_id": claim_id})

    # Background processing
    background_tasks.add_task(process_claim, claim_id)
    return CreateClaimResponse(id=claim_id, status="queued", job_id=f"job_{claim_id}")


@router.get(
    "/{claim_id}",
    response_model=ClaimItem,
    summary="Get claim details",
    description="Returns claim with sources and analysis summary.",
)
async def get_claim(claim_id: str, user: dict = Depends(get_current_user)):
    doc = await collection_claims().find_one({"_id": claim_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Load sources and analysis
    sources_docs = collection_sources().find({"claim_id": claim_id})
    sources: List[SourceItem] = [_serialize_source(d) async for d in sources_docs]
    analysis_doc = await collection_analyses().find_one({"claim_id": claim_id})
    analysis = None
    if analysis_doc:
        analysis = {
            "id": str(analysis_doc.get("_id")),
            "claim_id": analysis_doc.get("claim_id"),
            "summary": analysis_doc.get("summary"),
            "score": float(analysis_doc.get("score", 0)),
            "created_at": analysis_doc.get("created_at"),
        }
    return _serialize_claim(doc, sources, analysis)


@router.get(
    "/{claim_id}/status",
    response_model=ClaimStatus,
    summary="Get claim processing status",
    description="Returns the current processing status for a claim.",
)
async def get_claim_status(claim_id: str, user: dict = Depends(get_current_user)):
    doc = await collection_claims().find_one({"_id": claim_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Claim not found")
    return ClaimStatus(status=doc.get("status"), progress=int(doc.get("progress", 0)), stage=doc.get("stage", ""))


@router.get(
    "",
    response_model=ClaimListResponse,
    summary="List claims",
    description="List claims with filters and pagination.",
)
async def list_claims(
    user: dict = Depends(get_current_user),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    q: Optional[str] = Query(default=None, description="Search query"),
    from_ts: Optional[datetime] = Query(default=None, alias="from", description="From timestamp"),
    to_ts: Optional[datetime] = Query(default=None, alias="to", description="To timestamp"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    filt: dict = {"user_id": user["id"]}
    if status:
        filt["status"] = status
    if q:
        filt["text"] = {"$regex": q, "$options": "i"}
    if from_ts or to_ts:
        filt["created_at"] = {}
        if from_ts:
            filt["created_at"]["$gte"] = from_ts
        if to_ts:
            filt["created_at"]["$lte"] = to_ts

    total = await collection_claims().count_documents(filt)
    cursor = (
        collection_claims()
        .find(filt)
        .sort("created_at", -1)
        .skip((page - 1) * size)
        .limit(size)
    )

    items: List[ClaimItem] = []
    async for doc in cursor:
        items.append(_serialize_claim(doc))
    return ClaimListResponse(items=items, total=total, page=page, size=size)
