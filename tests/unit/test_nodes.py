"""
Unit tests for remaining nodes: NODE-2, 3, 5, 8.
"""

import pytest
from are.core.nodes.node_2_evidence import node_2_evidence_collection
from are.core.nodes.node_3_contract import node_3_research_contract
from are.core.nodes.node_5_worker import node_5_worker
from are.core.nodes.node_8_report import node_8_report


class TestNode2Evidence:
    """NODE-2: Evidence collection and gap analysis."""

    def test_collects_papers(self, post_node1_state):
        result = node_2_evidence_collection(post_node1_state)
        assert len(result["evidence"]) > 0
        assert len(result["search_queries"]) > 0
        assert isinstance(result["knowledge_gaps"], list)

    def test_deduplicates(self, post_node1_state):
        result = node_2_evidence_collection(post_node1_state)
        titles = [p["title"] for p in result["evidence"]]
        assert len(titles) == len(set(titles))

    def test_returns_partial_dict(self, post_node1_state):
        result = node_2_evidence_collection(post_node1_state)
        assert "_ctx" not in result
        assert "evidence_sufficiency" in result


class TestNode3Contract:
    """NODE-3: Research contract generation."""

    def test_generates_contract(self, post_node2_state):
        result = node_3_research_contract(post_node2_state)
        contract = result["research_contract"]
        assert "problem_statement" in contract
        assert "hypotheses" in contract
        assert "tasks" in contract
        assert contract["requires_human_approval"] is True

    def test_insufficient_evidence_errors(self, post_node2_state):
        post_node2_state["evidence_sufficiency"] = False
        result = node_3_research_contract(post_node2_state)
        assert len(result.get("errors", [])) > 0


class TestNode5Worker:
    """NODE-5: Experiment code generation (dry_run mode)."""

    def test_dry_run_generates_mock_logs(self, approved_state):
        result = node_5_worker(approved_state)
        assert result["execution_status"] == "completed"
        assert len(result["execution_logs"]) > 0
        assert result["experiment_code"] != ""

    def test_unapproved_aborts(self, approved_state):
        approved_state["human_decisions"] = [{"approval_status": "rejected"}]
        result = node_5_worker(approved_state)
        assert result["execution_status"] == "aborted"


class TestNode8Report:
    """NODE-8: Report generation."""

    def test_generates_markdown(self, executed_state):
        result = node_8_report(executed_state)
        assert "report_markdown" in result
        assert "# Research Report" in result["report_markdown"]

    def test_generates_json(self, executed_state):
        result = node_8_report(executed_state)
        rj = result["report_json"]
        assert "final_verdict" in rj
        assert "confidence" in rj

    def test_handles_empty_state(self, base_state):
        base_state["verdict"] = "inconclusive"
        base_state["confidence"] = 0.0
        result = node_8_report(base_state)
        assert "report_markdown" in result
