"""
LLM Provider Factory — single switching point for all LLM backends.
"""

from __future__ import annotations

from are.ports.llm_port import LLMPort


def create_llm_adapter(
    provider: str,
    model: str = "",
    api_key: str = "",
) -> LLMPort:
    """Create an LLM adapter based on provider name.

    Raising ValueError for unknown providers is intentional — fail-fast
    at startup, not at runtime.
    """
    if provider == "gemini":
        from are.adapters.llm.gemini_adapter import GeminiAdapter
        return GeminiAdapter(model=model or "gemini-2.0-flash", api_key=api_key)

    if provider == "mock":
        from are.adapters.llm.mock_adapter import MockLLMAdapter
        return MockLLMAdapter()

    if provider == "groq":
        from are.adapters.llm.groq_adapter import GroqAdapter
        return GroqAdapter(model=model or "llama-3.3-70b-versatile", api_key=api_key)

    # Future: openai, mistral, local, etc.
    raise ValueError(
        f"Unknown LLM provider: '{provider}'. "
        f"Supported: gemini, groq, mock"
    )
