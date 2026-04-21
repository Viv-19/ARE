"""
NODE-0-CONFIRM — HITL confirmation gate with clarification support.

Two modes:
1. CLARIFICATION: NODE-0 detected vague query → present questions to user,
   loop back to NODE-0 with the refined question.
2. CONFIRMATION: NODE-0 produced a clear spec → user approves or refines.

Returns ``Command(goto=...)`` to control the next destination.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from langgraph.types import Command, interrupt

from are.core.nodes._tracing import traced_node

logger = logging.getLogger(__name__)


@traced_node("NODE-0-CONFIRM")
def node_0_confirm(state: Dict[str, Any]) -> Command:
    """HITL gate: handle clarification or confirmation."""

    clarification_needed = state.get("clarification_needed", False)
    clarification_questions = state.get("clarification_questions", [])

    if clarification_needed and clarification_questions:
        # ── CLARIFICATION MODE ───────────────────────────────────────
        payload = {
            "type": "clarification",
            "normalized_question": state.get("normalized_question", ""),
            "research_intent": state.get("research_intent", ""),
            "intent_confidence": state.get("intent_confidence", 0),
            "variables": state.get("variables", {}),
            "reasoning": state.get("reasoning", ""),
            "clarification_questions": clarification_questions,
            "message": "Your query needs more detail. Please answer the questions below.",
        }
    else:
        # ── CONFIRMATION MODE ────────────────────────────────────────
        payload = {
            "type": "confirmation",
            "normalized_question": state.get("normalized_question", ""),
            "research_intent": state.get("research_intent", ""),
            "intent_confidence": state.get("intent_confidence", 0),
            "variables": state.get("variables", {}),
            "reasoning": state.get("reasoning", ""),
            "message": "Please review and approve the research specification.",
        }

    # ── Suspend execution for human input ────────────────────────────
    decision = interrupt(payload)
    logger.info("[NODE-0-CONFIRM] Resumed with decision: %s", decision)

    action = decision.get("action", "approve") if isinstance(decision, dict) else "approve"

    if action in ("refine", "clarify"):
        feedback = decision.get("feedback", "") if isinstance(decision, dict) else ""
        original = state.get("research_question", "")

        # Append user's clarification to the question and re-run NODE-0
        return Command(
            update={
                "research_question": f"{original}\n\nUSER FEEDBACK: {feedback}",
                "clarification_needed": False,  # Reset for next pass
                "clarification_questions": [],
                "human_decisions": state.get("human_decisions", []) + [
                    {"action": action, "node": "NODE-0-CONFIRM", "feedback": feedback}
                ],
            },
            goto="node_0",
        )

    # ── Approved -> proceed to NODE-1 ────────────────────────────────
    return Command(
        update={
            "human_decisions": state.get("human_decisions", []) + [
                {"action": "approve", "node": "NODE-0-CONFIRM"}
            ],
        },
        goto="node_1",
    )
