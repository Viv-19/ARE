"""
Unit tests for NODE-6: Scientific Critic.

Tests penalty-based confidence scoring, verdict derivation,
and edge case handling.
"""

import pytest
from are.core.nodes.node_6_critic import node_6_critic
from are.core.logic.confidence import compute_confidence


class TestNode6Critic:
    """Penalty-based confidence scoring."""

    def test_single_seed_penalty(self, approved_state):
        approved_state["execution_logs"] = [
            {"experiment_id": "E1", "random_seed": 42, "status": "success"},
        ]
        result = node_6_critic(approved_state)
        assert result["confidence"] <= 0.85  # 1.0 - 0.15

    def test_multi_seed_no_penalty(self, approved_state):
        approved_state["execution_logs"] = [
            {"experiment_id": "E1", "random_seed": 42, "status": "success"},
            {"experiment_id": "E2", "random_seed": 43, "status": "success"},
        ]
        result = node_6_critic(approved_state)
        assert result["confidence"] > 0.85

    def test_execution_failure_penalty(self, approved_state):
        approved_state["execution_logs"] = [
            {"experiment_id": "E1", "random_seed": 42, "status": "oom"},
        ]
        result = node_6_critic(approved_state)
        # Single seed (-0.15) + failure (-0.20) = 0.65 max
        assert result["confidence"] <= 0.65

    def test_no_logs_returns_inconclusive(self, approved_state):
        approved_state["execution_logs"] = []
        result = node_6_critic(approved_state)
        assert result["verdict"] == "inconclusive"
        assert result["confidence"] == 0.0

    def test_confidence_never_negative(self, approved_state):
        approved_state["execution_logs"] = [
            {"experiment_id": f"E{i}", "random_seed": 42, "status": "oom"}
            for i in range(10)
        ]
        result = node_6_critic(approved_state)
        assert result["confidence"] >= 0.0

    def test_conclusive_requires_high_confidence(self, approved_state):
        approved_state["execution_logs"] = [
            {"experiment_id": "E1", "random_seed": 42, "status": "success"},
            {"experiment_id": "E2", "random_seed": 43, "status": "success"},
            {"experiment_id": "E3", "random_seed": 44, "status": "success"},
        ]
        result = node_6_critic(approved_state)
        if result["verdict"] == "conclusive":
            assert result["confidence"] >= 0.75


class TestConfidenceEngine:
    """Direct tests of the pure confidence computation."""

    def test_empty_logs(self):
        report = compute_confidence([], {})
        assert report.verdict == "inconclusive"

    def test_all_failures_contradictory(self):
        logs = [{"experiment_id": f"E{i}", "random_seed": 42, "status": "oom"} for i in range(5)]
        report = compute_confidence(logs, {"hypotheses": {"H1": {}}})
        assert report.verdict == "contradictory"

    def test_penalties_listed(self):
        logs = [{"experiment_id": "E1", "random_seed": 42, "status": "success"}]
        report = compute_confidence(logs, {})
        assert len(report.penalties_applied) > 0  # Single-seed penalty
