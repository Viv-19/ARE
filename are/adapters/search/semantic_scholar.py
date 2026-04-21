"""
Semantic Scholar Adapter — SearchPort implementation for S2 Graph API.

Includes retry with backoff for 429 rate limits (the free S2 API is
limited to ~100 requests/5 minutes without an API key).
"""

from __future__ import annotations

import logging
import time
from typing import List

import requests

from are.ports.search_port import PaperResult, SearchPort, SearchResponse

logger = logging.getLogger(__name__)

_API_BASE = "https://api.semanticscholar.org/graph/v1"


class SemanticScholarAdapter(SearchPort):
    """Semantic Scholar search via the public Graph API."""

    def __init__(self, api_key: str = ""):
        self._api_key = api_key

    def search(self, query: str, *, max_results: int = 10) -> SearchResponse:
        headers = {}
        if self._api_key:
            headers["x-api-key"] = self._api_key

        for attempt in range(3):
            try:
                resp = requests.get(
                    f"{_API_BASE}/paper/search",
                    params={
                        "query": query,
                        "limit": max_results,
                        "fields": "title,year,authors,citationCount,venue,abstract,url",
                    },
                    headers=headers,
                    timeout=15,
                )

                if resp.status_code == 429:
                    wait = 3 * (attempt + 1)
                    logger.warning("[S2] Rate-limited, retry in %ds (%d/3)", wait, attempt + 1)
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                data = resp.json()

                papers: List[PaperResult] = []
                for p in data.get("data", []):
                    authors = [a.get("name", "?") for a in p.get("authors", [])][:5]
                    # Build a proper URL
                    paper_url = p.get("url", "")
                    if not paper_url:
                        pid = p.get("paperId", "")
                        if pid:
                            paper_url = f"https://www.semanticscholar.org/paper/{pid}"

                    papers.append(PaperResult(
                        title=p.get("title", "Untitled"),
                        year=p.get("year", 2024) or 2024,
                        authors=authors,
                        citation_count=p.get("citationCount", 0) or 0,
                        venue=p.get("venue", "Unknown") or "Unknown",
                        abstract=(p.get("abstract") or "")[:500],
                        url=paper_url,
                        source="SemanticScholar",
                    ))
                return SearchResponse(papers=papers)

            except requests.exceptions.Timeout:
                return SearchResponse(error="Timeout")
            except requests.exceptions.RequestException as exc:
                return SearchResponse(error=str(exc))

        # All retries exhausted
        return SearchResponse(rate_limited=True, error="S2 rate limit after 3 retries")

    @property
    def source_name(self) -> str:
        return "SemanticScholar"
