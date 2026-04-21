"""
Shared test fixtures for the ARE test suite.

Every node test imports from here for consistent, pre-built states.
"""

from __future__ import annotations

import pytest

from are.adapters.llm.mock_adapter import MockLLMAdapter
from are.adapters.search.mock_search import MockSearchAdapter


# ── LLM fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def mock_llm():
    """LLM that always fails → forces deterministic fallback."""
    return MockLLMAdapter()


@pytest.fixture
def mock_search():
    """Mock search adapter with realistic quantization papers."""
    return MockSearchAdapter()


# ── State fixtures ───────────────────────────────────────────────────

@pytest.fixture
def ctx(mock_llm, mock_search):
    """Standard _ctx dict injected into state."""
    return {
        "llm": mock_llm,
        "search_adapters": [mock_search],
        "enable_real_hitl": False,
        "enable_node_0_confirm": False,
    }


@pytest.fixture
def base_state(ctx):
    """Minimal valid GraphState for NODE-0."""
    return {
        "research_question": "Does INT4 quantization reduce inference latency in decoder-only LLMs?",
        "execution_mode": "dry_run",
        "random_seed": 42,
        "constraints": {"max_vram_gb": 8},
        "errors": [],
        "iteration_count": 0,
        "human_decisions": [],
        "_session_id": "test-001",
        "_ctx": ctx,
    }


@pytest.fixture
def post_node0_state(base_state):
    """State after NODE-0 completes successfully."""
    return {
        **base_state,
        "normalized_question": "Formal investigation: Does INT4 quantization reduce inference latency in decoder-only LLMs?",
        "research_intent": "exploratory",
        "intent_confidence": 0.85,
        "autonomy_level": "experiment_limited",
        "evidence_threshold": "literature_plus_experiments",
        "domain_valid": True,
        "researchable": True,
        "variables": {
            "independent": ["INT4 Quantization"],
            "dependent": ["Computational Efficiency (Latency)"],
            "control": ["Model architecture (Decoder-only)", "Base precision (FP32 reference)", "Evaluation dataset"],
        },
    }


@pytest.fixture
def post_node1_state(post_node0_state):
    """State after NODE-1 routes to 'partial'."""
    return {
        **post_node0_state,
        "research_status": "partial",
        "evidence_required": True,
        "knowledge_confidence": "medium",
    }


@pytest.fixture
def post_node2_state(post_node1_state):
    """State after NODE-2 collects evidence."""
    return {
        **post_node1_state,
        "search_queries": ["INT4 quantization transformer"],
        "evidence": [
            {"title": "GPTQ", "year": 2023, "citation_count": 850, "source": "Mock"},
            {"title": "AWQ", "year": 2024, "citation_count": 420, "source": "Mock"},
        ],
        "knowledge_gaps": ["Limited INT4 residual stream analysis"],
        "evidence_sufficiency": True,
    }


@pytest.fixture
def approved_state(post_node2_state):
    """State after NODE-3 contract + NODE-4 approval."""
    return {
        **post_node2_state,
        "research_contract": {
            "problem_statement": "Investigate INT4 quantization effects on decoder-only LLMs",
            "hypotheses": {
                "H1": {"statement": "INT4 increases logit variance", "derived_from": "Gap 1"},
                "H2": {"statement": "INT8 preserves similarity", "derived_from": "Gap 2"},
            },
            "tasks": [
                {"id": "T1", "description": "Load model", "type": "setup", "depends_on": []},
                {"id": "T2", "description": "Apply quantization", "type": "execution", "depends_on": ["T1"]},
            ],
            "constraints": {"max_experiments": 3, "max_gpu_hours": 2.0, "max_memory_gb": 16},
            "cost_estimate": {"expected_gpu_hours": 1.6, "risk_level": "medium"},
            "requires_human_approval": True,
        },
        "human_decisions": [{"approval_status": "approved", "action": "approve"}],
    }


@pytest.fixture
def executed_state(approved_state):
    """State after NODE-5 execution in dry-run mode."""
    return {
        **approved_state,
        "execution_status": "completed",
        "execution_logs": [
            {
                "experiment_id": "EXP_FP16", "model": "distilgpt2",
                "quantization": "FP16", "latency_ms": 145.2,
                "random_seed": 42, "status": "success",
                "semantic_similarity": 1.0,
            },
            {
                "experiment_id": "EXP_INT8", "model": "distilgpt2",
                "quantization": "INT8", "latency_ms": 98.7,
                "random_seed": 42, "status": "success",
                "semantic_similarity": 0.87,
            },
        ],
    }
