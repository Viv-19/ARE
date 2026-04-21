"""
NODE-4 — Human Approval Gate (HITL-1).

Mandatory governance layer before experiment execution.
Uses LangGraph ``interrupt()`` for real HITL, or reads from pre-set
state when HITL is disabled (testing/demo).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from langgraph.types import Command, interrupt

from are.core.nodes._tracing import traced_node

logger = logging.getLogger(__name__)


@traced_node("NODE-4")
def node_4_hitl_approval(state: Dict[str, Any]) -> Any:
    """HITL gate: suspend graph until human approves the research contract."""

    contract = state.get("research_contract", {})
    ctx = state.get("_ctx", {})
    enable_hitl = ctx.get("enable_real_hitl", True)

    if enable_hitl:
        # ── Real HITL: pause for human ───────────────────────────────
        payload = {
            "type": "approval",
            "contract_summary": contract.get("problem_statement", ""),
            "hypotheses_count": len(contract.get("hypotheses", {})),
            "tasks_count": len(contract.get("tasks", [])),
            "cost_estimate": contract.get("cost_estimate", {}),
            "constraints": contract.get("constraints", {}),
        }

        decision = interrupt(payload)
        logger.info("[NODE-4] Resumed with decision: %s", decision)
    else:
        # ── Simulated HITL: auto-approve ─────────────────────────────
        existing = state.get("human_decisions", [])
        if existing and existing[-1].get("approval_status") == "rejected":
            decision = {"action": "reject", "approval_status": "rejected"}
        else:
            decision = {"action": "approve", "approval_status": "approved"}

    # ── Process decision ──────────────────────────────────────────────
    action = decision.get("action", "approve") if isinstance(decision, dict) else "approve"
    timestamp = datetime.now(timezone.utc).isoformat()

    decision_record = {
        "action": action,
        "approval_status": "approved" if action == "approve" else "rejected",
        "node": "NODE-4",
        "timestamp": timestamp,
    }

    new_decisions = state.get("human_decisions", []) + [decision_record]

    if action != "approve":
        logger.info("[NODE-4] Contract REJECTED — looping back to NODE-3.")
        return Command(
            update={"human_decisions": new_decisions},
            goto="node_3",
        )

    logger.info("[NODE-4] Contract APPROVED — proceeding to NODE-5.")
    return Command(
        update={"human_decisions": new_decisions},
        goto="node_5",
    )
