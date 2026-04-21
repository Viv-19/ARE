"""
Metrics Port — Abstract interface for observability.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class MetricsPort(ABC):
    """Abstract interface for recording operational metrics."""

    @abstractmethod
    def record_node_latency(self, node: str, latency_ms: float) -> None: ...

    @abstractmethod
    def record_llm_call(
        self,
        provider: str,
        mode: str,
        success: bool,
        latency_ms: float,
    ) -> None: ...

    @abstractmethod
    def record_search_call(
        self, source: str, papers_found: int, latency_ms: float
    ) -> None: ...

    @abstractmethod
    def increment_error(self, node: str, error_type: str) -> None: ...
