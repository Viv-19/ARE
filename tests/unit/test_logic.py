"""
Unit tests for core logic modules.

Tests pure functions in isolation: domain validation, intent classification,
variable extraction, and paper deduplication.
"""

import pytest
from are.core.logic.domain_validation import is_domain_valid
from are.core.logic.intent_classification import classify_intent
from are.core.logic.variable_extraction import extract_variables
from are.core.logic.deduplication import deduplicate_papers


class TestDomainValidation:

    def test_quantization_valid(self):
        assert is_domain_valid("INT4 quantization effects") is True

    def test_transformer_valid(self):
        assert is_domain_valid("transformer attention mechanism") is True

    def test_pizza_invalid(self):
        assert is_domain_valid("best pizza recipe") is False

    def test_empty_invalid(self):
        assert is_domain_valid("") is False

    def test_case_insensitive(self):
        assert is_domain_valid("QUANTIZATION OF LLMS") is True


class TestIntentClassification:

    def test_comparison(self):
        intent, conf = classify_intent("compare INT4 vs INT8")
        assert intent == "comparison"

    def test_optimization(self):
        intent, conf = classify_intent("optimize inference latency")
        assert intent == "optimization"

    def test_replication(self):
        intent, conf = classify_intent("replicate the GPTQ results")
        assert intent == "replication"

    def test_default_exploratory(self):
        intent, conf = classify_intent("what happens to residual streams")
        assert intent == "exploratory"


class TestVariableExtraction:

    def test_int4_extracted(self):
        vars = extract_variables("INT4 quantization effect on latency")
        assert "INT4 Quantization" in vars["independent"]
        assert any("Latency" in v for v in vars["dependent"])

    def test_defaults_when_no_keywords(self):
        vars = extract_variables("some generic question")
        assert len(vars["independent"]) >= 1
        assert len(vars["dependent"]) >= 1
        assert len(vars["control"]) >= 1


class TestDeduplication:

    def test_removes_exact_duplicates(self):
        papers = [
            {"title": "Paper A", "year": 2023, "citation_count": 100, "source": "S2"},
            {"title": "Paper A", "year": 2023, "citation_count": 50, "source": "OA"},
        ]
        deduped = deduplicate_papers(papers)
        assert len(deduped) == 1
        assert deduped[0]["citation_count"] == 100  # Keeps higher

    def test_different_papers_preserved(self):
        papers = [
            {"title": "Paper A", "year": 2023, "citation_count": 100, "source": "S2"},
            {"title": "Paper B", "year": 2024, "citation_count": 50, "source": "OA"},
        ]
        deduped = deduplicate_papers(papers)
        assert len(deduped) == 2

    def test_merges_sources(self):
        papers = [
            {"title": "Paper A", "year": 2023, "citation_count": 100, "source": "S2"},
            {"title": "Paper A", "year": 2023, "citation_count": 50, "source": "OA"},
        ]
        deduped = deduplicate_papers(papers)
        assert "OA" in deduped[0]["source"]
        assert "S2" in deduped[0]["source"]

    def test_empty_input(self):
        assert deduplicate_papers([]) == []
