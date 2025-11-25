from datetime import datetime
from typing import List

import httpx

from src.models.schemas import SourceItem


API_BASE = "https://en.wikipedia.org/api/rest_v1/page/summary"


# PUBLIC_INTERFACE
async def fetch_wikipedia_sources(claim_id: str, query: str) -> List[SourceItem]:
    """Fetch sources from Wikipedia REST API.

    Args:
        claim_id: Related claim id
        query: Search term; for simplicity using summary endpoint on a title-like query.

    Returns:
        List[SourceItem]: At most one result from summary endpoint.
    """
    # Try fetching page summary. In real world, use search; here we simplify.
    url = f"{API_BASE}/{httpx.utils.quote(query.replace(' ', '_'))}"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(url, headers={"accept": "application/json"})
            if r.status_code != 200:
                return []
            data = r.json()
            title = data.get("title", query)
            extract = data.get("extract")
            page_url = data.get("content_urls", {}).get("desktop", {}).get("page", f"https://en.wikipedia.org/wiki/{query}")
            return [
                SourceItem(
                    claim_id=claim_id,
                    title=title,
                    url=page_url,
                    snippet=extract,
                    reliability_score=0.9,  # Wikipedia generally reliable
                    stance="neutral",
                    provider="wikipedia",
                    fetched_at=datetime.utcnow(),
                )
            ]
        except Exception:
            return []
