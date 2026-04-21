"""
ArXiv Adapter — SearchPort implementation using the ``arxiv`` library.
"""

from __future__ import annotations

import logging
from typing import List

from are.ports.search_port import PaperResult, SearchPort, SearchResponse

logger = logging.getLogger(__name__)


class ArxivAdapter(SearchPort):
    """ArXiv search via the ``arxiv`` Python package."""

    def search(self, query: str, *, max_results: int = 10) -> SearchResponse:
        try:
            import arxiv as arxiv_lib

            client = arxiv_lib.Client()
            search = arxiv_lib.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv_lib.SortCriterion.Relevance,
            )

            papers: List[PaperResult] = []
            for paper in client.results(search):
                papers.append(PaperResult(
                    title=paper.title,
                    year=paper.published.year if paper.published else 2024,
                    authors=[a.name for a in paper.authors][:5],
                    citation_count=0,  # ArXiv doesn't provide citations
                    venue="arXiv",
                    abstract=(paper.summary or "")[:500],
                    url=paper.entry_id or "",
                    source="ArXiv",
                ))
            return SearchResponse(papers=papers)

        except ImportError:
            logger.error("[ArXiv] 'arxiv' library not installed.")
            return SearchResponse(error="arxiv library not installed")
        except Exception as exc:
            logger.error("[ArXiv] Search failed: %s", exc)
            return SearchResponse(error=str(exc))

    @property
    def source_name(self) -> str:
        return "ArXiv"
