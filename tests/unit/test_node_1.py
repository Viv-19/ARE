"""
Unit tests for NODE-1: Knowledge Assessment Router.

Tests citation threshold logic and routing decisions.
"""

import pytest
from are.core.nodes.node_1_router import node_1_knowledge_assessment_router
from are.adapters.search.mock_search import MockSearchAdapter
from are.ports.search_port import PaperResult, SearchPort, SearchResponse


class _HighCiteSearch(SearchPort):
    """Returns papers above citation threshold."""
    def search(self, query, *, max_results=10):
        return SearchResponse(papers=[
            PaperResult(title="Quantization of LLM inference", year=2023,
                        citation_count=200, abstract="int4 quantization transformer inference", source="Test"),
            PaperResult(title="Transformer latency optimization", year=2023,
                        citation_count=150, abstract="transformer inference latency", source="Test"),
            PaperResult(title="Efficient LLM quantization survey", year=2024,
                        citation_count=300, abstract="efficient llm quantization inference", source="Test"),
        ])

    @property
    def source_name(self): return "TestHigh"


class _LowCiteSearch(SearchPort):
    """Returns papers below citation threshold."""
    def search(self, query, *, max_results=10):
        return SearchResponse(papers=[
            PaperResult(title="New idea about something", year=2024,
                        citation_count=5, abstract="novel approach", source="Test"),
        ])

    @property
    def source_name(self): return "TestLow"


class TestNode1Routing:
    """Core routing logic based on citation analysis."""

    def test_well_studied_skips_to_report(self, post_node0_state):
        post_node0_state["_ctx"]["search_adapters"] = [_HighCiteSearch()]
        result = node_1_knowledge_assessment_router(post_node0_state)
        assert result["research_status"] == "well-studied"
        assert result["evidence_required"] is False

    def test_novel_proceeds_to_evidence(self, post_node0_state):
        post_node0_state["_ctx"]["search_adapters"] = [_LowCiteSearch()]
        result = node_1_knowledge_assessment_router(post_node0_state)
        assert result["research_status"] == "novel"
        assert result["evidence_required"] is True

    def test_no_search_adapters_returns_novel(self, post_node0_state):
        post_node0_state["_ctx"]["search_adapters"] = []
        result = node_1_knowledge_assessment_router(post_node0_state)
        assert result["research_status"] == "novel"

    def test_returns_partial_dict(self, post_node0_state):
        post_node0_state["_ctx"]["search_adapters"] = [MockSearchAdapter()]
        result = node_1_knowledge_assessment_router(post_node0_state)
        assert "research_status" in result
        assert "reasoning_summary" in result
        assert "_ctx" not in result
