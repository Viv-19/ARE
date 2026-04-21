"""
Unit tests for the LLM port and adapters.
"""

import pytest
from are.ports.llm_port import LLMMode, LLMResponse
from are.adapters.llm.mock_adapter import MockLLMAdapter
from are.adapters.llm.factory import create_llm_adapter


class TestLLMResponse:
    """LLMResponse dataclass behaviour."""

    def test_success_response(self):
        r = LLMResponse(content="ok", parsed={"k": "v"}, model="test",
                        tokens_used=10, latency_ms=50, success=True)
        assert r.success is True
        assert r.failed is False
        assert r.get("k") == "v"
        assert r.get("missing", 42) == 42

    def test_failed_response(self):
        r = LLMResponse(success=False, error="timeout")
        assert r.failed is True
        assert r.get("anything") is None


class TestMockAdapter:
    """Mock adapter behaviour."""

    def test_default_fails(self):
        adapter = MockLLMAdapter()
        resp = adapter.generate("test prompt")
        assert resp.success is False

    def test_configured_response(self):
        adapter = MockLLMAdapter(responses={
            "judgment": {"domain_valid": True, "research_intent": "exploratory"},
        })
        resp = adapter.generate("test", mode=LLMMode.JUDGMENT)
        assert resp.success is True
        assert resp.parsed["domain_valid"] is True

    def test_is_available(self):
        assert MockLLMAdapter().is_available() is True

    def test_provider_name(self):
        assert MockLLMAdapter().provider_name == "Mock LLM"


class TestFactory:
    """LLM factory dispatching."""

    def test_mock_provider(self):
        adapter = create_llm_adapter("mock")
        assert adapter.provider_name == "Mock LLM"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            create_llm_adapter("nonexistent")
