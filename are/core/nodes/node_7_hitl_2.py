"""
NODE-7 — Human-Critic Loop (HITL-2).

Post-execution human oversight.  Allows the user to iterate (loop back
to NODE-5) or terminate early (proceed to NODE-8).
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from langgraph.types import Command, interrupt

from are.core.nodes._tracing import traced_node

logger = logging.getLogger(__name__)


@traced_node("NODE-7")
def node_7_hitl_loop(state: Dict[str, Any]) -> Any:
    """HITL loop gate: continue or terminate the experiment cycle."""

    verdict = state.get("verdict", "")
    confidence = state.get("confidence", 0.0)
    iteration = state.get("iteration_count", 0)
    contract = state.get("research_contract", {})
    max_experiments = contract.get("constraints", {}).get("max_experiments", 3)
    ctx = state.get("_ctx", {})
    enable_hitl = ctx.get("enable_real_hitl", True)

    # ── Guard: skip if conclusive ────────────────────────────────────
    if verdict == "conclusive":
        logger.info("[NODE-7] Verdict is conclusive — skipping to report.")
        return Command(
            update={"loop_decision": "terminate"},
            goto="node_8",
        )

    # ── Guard: max iterations ────────────────────────────────────────
    if iteration >= max_experiments:
        logger.info("[NODE-7] Max iterations reached (%d) — forced termination.", max_experiments)
        return Command(
            update={"loop_decision": "terminate", "remaining_budget": 0},
            goto="node_8",
        )

    # ── HITL decision ────────────────────────────────────────────────
    if enable_hitl:
        payload = {
            "type": "loop_decision",
            "verdict": verdict,
            "confidence": confidence,
            "iteration": iteration,
            "max_iterations": max_experiments,
            "proposed_actions": state.get("proposed_next_actions", []),
        }
        decision = interrupt(payload)
        logger.info("[NODE-7] Resumed with: %s", decision)
    else:
        decision = {"action": "stop"}

    action = decision.get("action", "stop") if isinstance(decision, dict) else "stop"
    new_decisions = state.get("human_decisions", []) + [
        {"action": action, "node": "NODE-7"}
    ]

    if action in ("continue", "approve"):
        logger.info("[NODE-7] User chose CONTINUE -> looping to NODE-5.")
        return Command(
            update={
                "loop_decision": "continue",
                "iteration_count": iteration + 1,
                "remaining_budget": max_experiments - iteration - 1,
                "human_decisions": new_decisions,
            },
            goto="node_5",
        )

    logger.info("[NODE-7] User chose STOP -> proceeding to NODE-8.")
    return Command(
        update={
            "loop_decision": "terminate",
            "human_decisions": new_decisions,
        },
        goto="node_8",
    )
