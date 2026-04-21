"""
LangGraph Workflow — State machine definition.

Defines the complete research pipeline graph:
  NODE-0 → Confirm → NODE-1 → NODE-2 → NODE-3 → NODE-4 → NODE-5 →
  NODE-6 → NODE-7 → NODE-8

Conditional edges are PURE FUNCTIONS — they read state but never mutate
it (fixes B-03).

Context (adapters, configuration) is injected via closures at graph
creation time — NOT via state.  This avoids LangGraph's serialisation
constraint on state values while keeping nodes testable.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from are.core.constants import CONFIDENCE_GATE_THRESHOLD
from are.core.nodes.node_0_confirm import node_0_confirm
from are.core.nodes.node_0_intake import node_0_research_question_intake
from are.core.nodes.node_1_router import node_1_knowledge_assessment_router
from are.core.nodes.node_2_evidence import node_2_evidence_collection
from are.core.nodes.node_3_contract import node_3_research_contract
from are.core.nodes.node_4_hitl_1 import node_4_hitl_approval
from are.core.nodes.node_5_worker import node_5_worker
from are.core.nodes.node_6_critic import node_6_critic
from are.core.nodes.node_7_hitl_2 import node_7_hitl_loop
from are.core.nodes.node_8_report import node_8_report
from are.core.state import GraphState

logger = logging.getLogger(__name__)


# ── Conditional edge functions (PURE — read only) ──────────────────────

def _confidence_gate(state: Dict[str, Any]) -> str:
    """Route after NODE-0 based on confidence and domain validity."""
    if state.get("domain_valid") is False:
        return "halt"
    # Always go to confirm unless explicitly disabled via state flag
    if state.get("_skip_confirm"):
        return "proceed"
    return "confirm"


def _research_router(state: Dict[str, Any]) -> str:
    """Route after NODE-1 based on research status."""
    if state.get("research_status") == "well-studied":
        return "summarize"
    return "research"


def _verdict_router(state: Dict[str, Any]) -> str:
    """Route after NODE-6 based on verdict."""
    if state.get("verdict") == "conclusive":
        return "report"
    return "critic_loop"


# ── Context-injecting wrapper ────────────────────────────────────────

def _with_context(node_fn: Callable, ctx: Dict[str, Any]) -> Callable:
    """Wrap a node function so that it receives ``_ctx`` in state
    without persisting adapter objects to the checkpoint.

    The wrapper injects ``_ctx`` before the call and strips it from the
    output dict to prevent LangGraph from serialising it.
    """
    def wrapped(state: Dict[str, Any]) -> Any:
        # Inject context (overwrite on every call — idempotent)
        state_with_ctx = dict(state)
        state_with_ctx["_ctx"] = ctx
        result = node_fn(state_with_ctx)
        # Strip _ctx from output to prevent serialisation failure
        if isinstance(result, dict):
            result.pop("_ctx", None)
        return result
    wrapped.__name__ = node_fn.__name__
    return wrapped


# ── Graph factory ────────────────────────────────────────────────────────

def create_are_graph(
    checkpointer: Optional[MemorySaver] = None,
    ctx: Optional[Dict[str, Any]] = None,
) -> Any:
    """Build and compile the ARE state-machine graph.

    Args:
        checkpointer: LangGraph checkpointer for state persistence + HITL.
                       Defaults to a MemorySaver if not provided.
        ctx: Injected context dict containing adapter instances (llm,
             search_adapters, etc.).  This is NOT stored in state —
             it is captured by closures around each node function.

    Returns:
        Compiled LangGraph runnable.
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    _ctx = ctx or {}

    workflow = StateGraph(GraphState)

    # ── Register nodes (wrapped with context) ────────────────────────
    workflow.add_node("node_0", _with_context(node_0_research_question_intake, _ctx))
    workflow.add_node("node_0_confirmation", _with_context(node_0_confirm, _ctx))
    workflow.add_node("node_1", _with_context(node_1_knowledge_assessment_router, _ctx))
    workflow.add_node("node_2", _with_context(node_2_evidence_collection, _ctx))
    workflow.add_node("node_3", _with_context(node_3_research_contract, _ctx))
    workflow.add_node("node_4", _with_context(node_4_hitl_approval, _ctx))
    workflow.add_node("node_5", _with_context(node_5_worker, _ctx))
    workflow.add_node("node_6", _with_context(node_6_critic, _ctx))
    workflow.add_node("node_7", _with_context(node_7_hitl_loop, _ctx))
    workflow.add_node("node_8", _with_context(node_8_report, _ctx))

    # ── Entry point ──────────────────────────────────────────────────
    workflow.set_entry_point("node_0")

    # ── Conditional edges ────────────────────────────────────────────
    workflow.add_conditional_edges(
        "node_0",
        _confidence_gate,
        {
            "halt": END,
            "confirm": "node_0_confirmation",
            "proceed": "node_1",
        },
    )

    # node_0_confirmation → navigation handled by Command(goto=...)

    workflow.add_conditional_edges(
        "node_1",
        _research_router,
        {
            "summarize": "node_8",
            "research": "node_2",
        },
    )

    # ── Linear edges ─────────────────────────────────────────────────
    workflow.add_edge("node_2", "node_3")
    workflow.add_edge("node_3", "node_4")

    # node_4 → navigation handled by Command(goto=...)
    # node_5 → node_6 (linear)
    workflow.add_edge("node_5", "node_6")

    workflow.add_conditional_edges(
        "node_6",
        _verdict_router,
        {
            "report": "node_8",
            "critic_loop": "node_7",
        },
    )

    # node_7 → navigation handled by Command(goto=...)

    # ── Terminal ─────────────────────────────────────────────────────
    workflow.add_edge("node_8", END)

    # ── Compile ──────────────────────────────────────────────────────
    compiled = workflow.compile(checkpointer=checkpointer)
    logger.info("[OK] ARE graph compiled (%d nodes)", len(workflow.nodes))

    return compiled
