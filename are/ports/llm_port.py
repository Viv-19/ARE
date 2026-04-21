"""
LLM Port — Abstract interface for all LLM providers.

Contract:
- generate() is synchronous (blocking).
- JSON parsing is the adapter's responsibility.
- Rate limiting / retry is the adapter's responsibility.
- Returns LLMResponse on every call (never raises on API failure).
- Core nodes depend ONLY on this interface, never on concrete adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class LLMMode(str, Enum):
    """Operating modes controlling temperature / token budget."""

    JUDGMENT = "judgment"  # Low-temp, strict JSON  (NODE-0,1,3,6)
    EXECUTION_SUPPORT = "execution_support"  # Mid-temp, code gen    (NODE-5)
    COMMUNICATION = "communication"  # Higher-temp, prose    (NODE-8)


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Immutable, standardised response envelope from any LLM provider."""

    content: str = ""
    parsed: Optional[Dict[str, Any]] = None
    model: str = ""
    tokens_used: int = 0
    latency_ms: float = 0.0
    success: bool = False
    error: Optional[str] = None

    # Convenience helpers ---------------------------------------------------

    @property
    def failed(self) -> bool:
        return not self.success

    def get(self, key: str, default: Any = None) -> Any:
        """Shorthand to pull a key from *parsed* safely."""
        if self.parsed is None:
            return default
        return self.parsed.get(key, default)


class LLMPort(ABC):
    """Abstract interface every LLM adapter must implement."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        mode: LLMMode = LLMMode.JUDGMENT,
        expect_json: bool = True,
    ) -> LLMResponse:
        """Generate a single response.

        Returns LLMResponse with ``success=False`` on any failure — callers
        must always check ``.success`` before reading ``.parsed``.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the adapter is configured and reachable."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider label (e.g. 'Gemini 1.5 Flash')."""
        ...
