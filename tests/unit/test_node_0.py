"""
Unit tests for NODE-0: Research Question Intake.

Tests domain validation, intent classification, variable extraction,
confidence scoring, and LLM fallback behaviour.
"""

import pytest
from are.core.nodes.node_0_intake import node_0_research_question_intake


class TestNode0HappyPath:
    """Valid queries produce correctly structured output."""

    def test_valid_quantization_query(self, base_state):
        result = node_0_research_question_intake(base_state)

        assert result["domain_valid"] is True
        assert result["normalized_question"] != ""
        assert result["research_intent"] in ("exploratory", "replication", "optimization", "comparison")
        assert 0.0 <= result["intent_confidence"] <= 1.0
        assert "independent" in result["variables"]
        assert "dependent" in result["variables"]
        assert "control" in result["variables"]

    def test_comparison_intent(self, base_state):
        base_state["research_question"] = "Compare INT4 vs INT8 quantization on transformer inference latency"
        result = node_0_research_question_intake(base_state)
        assert result["research_intent"] == "comparison"

    def test_optimization_intent(self, base_state):
        base_state["research_question"] = "Optimize inference latency through INT8 quantization of LLMs"
        result = node_0_research_question_intake(base_state)
        assert result["research_intent"] == "optimization"

    def test_replication_intent(self, base_state):
        base_state["research_question"] = "Replicate GPTQ quantization results on transformer models"
        result = node_0_research_question_intake(base_state)
        assert result["research_intent"] == "replication"

    def test_variables_extracted_for_rich_query(self, base_state):
        base_state["research_question"] = (
            "How does INT4 quantization affect latency and perplexity "
            "in decoder-only transformers?"
        )
        result = node_0_research_question_intake(base_state)
        assert "INT4 Quantization" in result["variables"]["independent"]
        assert any("Latency" in v for v in result["variables"]["dependent"])


class TestNode0DomainValidation:
    """Out-of-scope queries are rejected at the gate."""

    def test_off_topic_rejected(self, base_state):
        base_state["research_question"] = "What is the best pizza recipe?"
        result = node_0_research_question_intake(base_state)
        assert result["domain_valid"] is False
        assert len(result.get("errors", [])) > 0

    def test_biology_rejected(self, base_state):
        base_state["research_question"] = "How does CRISPR gene editing work?"
        result = node_0_research_question_intake(base_state)
        assert result["domain_valid"] is False


class TestNode0EdgeCases:
    """Edge cases and error conditions."""

    def test_empty_question(self, base_state):
        base_state["research_question"] = ""
        result = node_0_research_question_intake(base_state)
        assert result["domain_valid"] is False
        assert any("No research question" in e for e in result.get("errors", []))

    def test_whitespace_only(self, base_state):
        base_state["research_question"] = "   \n\t  "
        result = node_0_research_question_intake(base_state)
        assert result["domain_valid"] is False

    def test_returns_partial_dict_not_full_state(self, base_state):
        """B-02 fix: node must NOT return the full state object."""
        result = node_0_research_question_intake(base_state)
        # Result should not contain internal keys from input state
        assert "_session_id" not in result
        assert "_ctx" not in result
        assert "execution_mode" not in result


class TestNode0RefinementMode:
    """USER FEEDBACK injection triggers refinement awareness."""

    def test_feedback_in_question(self, base_state):
        base_state["research_question"] = (
            "INT4 quantization effects\n\n"
            "USER FEEDBACK: Focus on residual stream stability in transformers"
        )
        result = node_0_research_question_intake(base_state)
        assert "Refinement" in result.get("normalized_question", "")
