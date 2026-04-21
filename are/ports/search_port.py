"""
Search Port — Abstract interface for academic paper retrieval.

Every concrete adapter (Semantic Scholar, ArXiv, OpenAlex, Mock) must
implement this interface so the core layer never touches HTTP directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True, slots=True)
class PaperResult:
    """Normalised paper metadata returned by every search adapter."""

    title: str = "Untitled"
    year: int = 2024
    authors: List[str] = field(default_factory=list)
    citation_count: int = 0
    venue: str = "Unknown"
    abstract: str = ""
    url: str = ""
    source: str = "Unknown"


@dataclass(frozen=True, slots=True)
class SearchResponse:
    """Envelope for search adapter results."""

    papers: List[PaperResult] = field(default_factory=list)
    rate_limited: bool = False
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


class SearchPort(ABC):
    """Abstract interface for academic search providers."""

    @abstractmethod
    def search(self, query: str, *, max_results: int = 10) -> SearchResponse:
        """Execute a metadata-only paper search.

        Must never raise — returns SearchResponse with error details on failure.
        """
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable source label (e.g. 'SemanticScholar')."""
        ...
