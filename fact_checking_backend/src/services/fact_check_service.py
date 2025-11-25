import asyncio
from datetime import datetime
from typing import List, Optional

from src.core.config import get_env_settings
from src.core.db import collection_analyses, collection_claims, collection_sources
from src.models.schemas import AnalysisSummary, SourceItem
from src.services.source_fetchers.google_search_console import fetch_gsc_sources
from src.services.source_fetchers.wikipedia import fetch_wikipedia_sources
from src.api.routes.stream import ws_manager


async def _update_claim(claim_id: str, updates: dict, event_type: Optional[str] = None) -> None:
    """Update claim document and optionally push WS event."""
    await collection_claims().update_one({"_id": claim_id}, {"$set": updates})
    if event_type:
        await ws_manager.broadcast({"type": event_type, "claim_id": claim_id, "payload": updates})


def _score_sources(sources: List[SourceItem]) -> float:
    """Naive scoring heuristic combining reliability_score with stance weighting."""
    if not sources:
        return 0.5
    total = 0.0
    weight_sum = 0.0
    for s in sources:
        stance_weight = 1.0 if s.stance == "support" else (0.8 if s.stance == "neutral" else 0.6)
        total += s.reliability_score * stance_weight
        weight_sum += 1.0
    return max(0.0, min(1.0, total / max(weight_sum, 1.0)))


# PUBLIC_INTERFACE
async def process_claim(claim_id: str) -> None:
    """Run the fact-checking pipeline for a claim.

    Stages: triage -> fetch_sources -> analyze -> score -> complete
    Updates DB and broadcasts WebSocket events.
    """
    settings = get_env_settings()
    sleep_ms = settings.PROCESSING_POLL_INTERVAL_MS

    try:
        await _update_claim(claim_id, {"status": "processing", "stage": "triage", "progress": 10}, "claim_updated")
        await asyncio.sleep(sleep_ms / 1000)

        # Fetch sources
        await _update_claim(claim_id, {"stage": "fetch_sources", "progress": 30}, "claim_updated")
        claim = await collection_claims().find_one({"_id": claim_id})
        text = claim.get("text", "")

        wikipedia = await fetch_wikipedia_sources(claim_id, text[:80])
        gsc = await fetch_gsc_sources(claim_id, text[:80])
        sources = wikipedia + gsc
        # persist sources
        if sources:
            await collection_sources().insert_many([s.model_dump(exclude={"id"}) for s in sources])
        await ws_manager.broadcast({"type": "sources_fetched", "claim_id": claim_id, "count": len(sources)})

        await _update_claim(claim_id, {"stage": "analyze", "progress": 60}, "claim_updated")
        await asyncio.sleep(sleep_ms / 1000)

        # Analysis summary
        score = _score_sources(sources)
        summary_text = (
            "Based on retrieved sources, the claim appears "
            f"{'likely true' if score >= 0.6 else ('uncertain' if score >= 0.4 else 'likely false')}."
        )
        analysis = AnalysisSummary(claim_id=claim_id, summary=summary_text, score=score)
        await collection_analyses().insert_one(analysis.model_dump(exclude={"id"}))

        await ws_manager.broadcast({"type": "score_updated", "claim_id": claim_id, "score": score})

        await _update_claim(
            claim_id,
            {
                "stage": "score",
                "progress": 85,
                "score": score,
            },
            "claim_updated",
        )
        await asyncio.sleep(sleep_ms / 1000)

        completed_at = datetime.utcnow()
        latency_ms = int((completed_at - claim.get("created_at", completed_at)).total_seconds() * 1000)
        await _update_claim(
            claim_id,
            {"status": "complete", "stage": "complete", "progress": 100, "completed_at": completed_at, "latency_ms": latency_ms},
            "job_completed",
        )
    except Exception as e:
        await _update_claim(claim_id, {"status": "failed", "stage": "failed", "progress": 100, "error": str(e)}, "job_failed")
