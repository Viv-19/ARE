"""
Mock LLM Adapter — deterministic, zero-latency LLM for testing.

Always returns ``success=False`` by default, forcing every node to
exercise its deterministic fallback path.  Pre-configured responses
can be injected for specific test scenarios.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from are.ports.llm_port import LLMMode, LLMPort, LLMResponse


class MockLLMAdapter(LLMPort):
    """Deterministic mock that forces fallback paths unless explicitly configured."""

    def __init__(self, responses: Optional[Dict[str, Any]] = None):
        self._responses = responses or {}

    def generate(
        self,
        prompt: str,
        *,
        mode: LLMMode = LLMMode.JUDGMENT,
        expect_json: bool = True,
    ) -> LLMResponse:
        key = mode.value
        if key in self._responses:
            data = self._responses[key]
            return LLMResponse(
                content=str(data),
                parsed=data if expect_json and isinstance(data, dict) else None,
                model="mock",
                tokens_used=0,
                latency_ms=0.01,
                success=True,
            )

        return LLMResponse(
            content="",
            parsed=None,
            model="mock",
            tokens_used=0,
            latency_ms=0.01,
            success=False,
            error="Mock: no response configured for this mode.",
        )

    def is_available(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "Mock LLM"
