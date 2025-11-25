from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends

from src.core.db import collection_claims
from src.core.security import require_roles
from src.models.schemas import MetricsSummaryResponse

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get(
    "/summary",
    response_model=MetricsSummaryResponse,
    summary="Get metrics summary",
    description="Returns metrics summary for the last 24 hours.",
)
async def get_metrics_summary(user=Depends(require_roles(["admin", "moderator"]))):
    now = datetime.utcnow()
    since = now - timedelta(hours=24)
    filt = {"created_at": {"$gte": since}}

    cursor = collection_claims().find(filt)
    scores: List[float] = []
    latencies: List[int] = []
    total = 0
    success = 0

    async for doc in cursor:
        total += 1
        if doc.get("status") == "complete":
            success += 1
            if "score" in doc:
                try:
                    scores.append(float(doc["score"]))
                except Exception:
                    pass
        if "latency_ms" in doc:
            try:
                latencies.append(int(doc["latency_ms"]))
            except Exception:
                pass

    avg_score = sum(scores) / len(scores) if scores else 0.0
    if latencies:
        latencies_sorted = sorted(latencies)
        p50 = latencies_sorted[len(latencies_sorted) // 2]
        p95_index = max(0, int(round(0.95 * (len(latencies_sorted) - 1))))
        p95 = latencies_sorted[p95_index]
    else:
        p50 = 0.0
        p95 = 0.0

    success_rate = (success / total) if total else 0.0
    return MetricsSummaryResponse(
        total_claims_24h=total,
        avg_score_24h=avg_score,
        p50_latency_ms=float(p50),
        p95_latency_ms=float(p95),
        success_rate=success_rate,
    )
