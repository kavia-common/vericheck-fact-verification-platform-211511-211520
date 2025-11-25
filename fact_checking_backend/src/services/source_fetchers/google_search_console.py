from datetime import datetime
from typing import List

from src.core.config import get_env_settings
from src.models.schemas import SourceItem


# PUBLIC_INTERFACE
async def fetch_gsc_sources(claim_id: str, query: str) -> List[SourceItem]:
    """Fetch sources using Google Search Console (stub if no API key).

    If GSC_API_KEY is not set, returns an empty list. Replace with actual GSC integration later.
    """
    settings = get_env_settings()
    if not settings.GSC_API_KEY:
        # Feature flag off; return empty
        return []
    # Placeholder - pretend we fetched something authoritative
    return [
        SourceItem(
            claim_id=claim_id,
            title=f"Authoritative Source: {query}",
            url="https://news.google.com",
            snippet="Stubbed result from GSC integration.",
            reliability_score=0.8,
            stance="support",
            provider="google_search_console",
            fetched_at=datetime.utcnow(),
        )
    ]
