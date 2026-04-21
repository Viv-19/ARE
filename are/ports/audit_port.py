"""
Audit Port — Abstract interface for immutable decision logging.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class AuditPort(ABC):
    """Abstract interface for audit trail persistence."""

    @abstractmethod
    def log_decision(
        self, decision: Dict[str, Any], *, node: Optional[str] = None
    ) -> None:
        """Append a human decision (HITL) to the audit trail."""
        ...

    @abstractmethod
    def log_llm_usage(
        self,
        *,
        node: str,
        mode: str,
        success: bool,
        fallback_used: bool = False,
    ) -> None:
        """Record an LLM API call for cost tracking."""
        ...

    @abstractmethod
    def log_transition(
        self, from_node: str, to_node: str, *, reason: Optional[str] = None
    ) -> None:
        """Record a graph edge traversal."""
        ...
