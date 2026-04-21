"""
Integration test: full graph flow in dry-run mode.

Runs the complete pipeline NODE-0 → NODE-8 with mock LLM and mock search,
auto-approving all HITL gates.

Context is injected via the graph factory's ``ctx`` parameter (closure
injection), NOT via state keys — matching the production pattern.
"""

import pytest
from are.core.graph import create_are_graph
from are.adapters.llm.mock_adapter import MockLLMAdapter
from are.adapters.search.mock_search import MockSearchAdapter
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command


_TEST_CTX = {
    "llm": MockLLMAdapter(),
    "search_adapters": [MockSearchAdapter()],
    "enable_real_hitl": True,
    "enable_node_0_confirm": True,
}


class TestFullPipeline:
    """End-to-end graph execution."""

    def _build_initial_state(self):
        return {
            "research_question": "Does INT4 quantization reduce inference latency in decoder-only LLMs?",
            "execution_mode": "dry_run",
            "random_seed": 42,
            "constraints": {"max_vram_gb": 8},
            "errors": [],
            "iteration_count": 0,
            "human_decisions": [],
            "_session_id": "integration-test",
        }

    def test_full_flow_completes(self):
        """Complete pipeline should produce a report."""
        graph = create_are_graph(checkpointer=MemorySaver(), ctx=_TEST_CTX)
        config = {"configurable": {"thread_id": "int-test-1"}}
        state = self._build_initial_state()

        # Run until first interrupt
        for event in graph.stream(state, config, stream_mode="updates"):
            pass

        # Resume through all HITL points
        for _ in range(15):
            gs = graph.get_state(config)
            if not gs.next:
                break

            next_node = gs.next[0]
            if "node_7" in next_node:
                decision = {"action": "stop", "loop_decision": "terminate"}
            elif "node_5" in next_node:
                decision = {"results": []}
            else:
                decision = {"action": "approve", "approval_status": "approved"}

            for event in graph.stream(Command(resume=decision), config, stream_mode="updates"):
                pass

        # Verify final state
        final = graph.get_state(config).values
        assert "report_markdown" in final
        assert final["report_markdown"] != ""
        assert final.get("verdict") in ("conclusive", "inconclusive", "contradictory")
        assert 0.0 <= final.get("confidence", -1) <= 1.0

    def test_node0_rejection_halts(self):
        """Out-of-scope query → graph halts at NODE-0."""
        graph = create_are_graph(checkpointer=MemorySaver(), ctx=_TEST_CTX)
        config = {"configurable": {"thread_id": "int-test-reject"}}
        state = self._build_initial_state()
        state["research_question"] = "What is the meaning of life?"

        for event in graph.stream(state, config, stream_mode="updates"):
            pass

        final = graph.get_state(config)
        # Should halt — no next nodes
        assert not final.next
        assert final.values.get("domain_valid") is False
