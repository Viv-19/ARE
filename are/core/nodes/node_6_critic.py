"""
NODE-6 — Critic / Scientific Review Engine.

Evaluates execution logs against hypotheses using a penalty-based
confidence scoring system.  Delegates pure computation to
``core.logic.confidence``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from are.core.logic.confidence import compute_confidence
from are.core.nodes._tracing import traced_node
from are.ports.llm_port import LLMMode

logger = logging.getLogger(__name__)


@traced_node("NODE-6")
def node_6_critic(state: Dict[str, Any]) -> Dict[str, Any]:
    """Scientific review: score confidence and assign verdict."""

    execution_logs = state.get("execution_logs", [])
    contract = state.get("research_contract", {})
    ctx = state.get("_ctx", {})
    llm = ctx.get("llm")

    # ── Guard: no logs ───────────────────────────────────────────────
    if not execution_logs:
        return {
            "verdict": "inconclusive",
            "confidence": 0.0,
            "hypothesis_evaluation": {},
            "identified_issues": ["No execution logs available for review."],
            "proposed_next_actions": [{"action": "Re-run experiments", "reason": "No data"}],
        }

    # ── Try LLM-enhanced review ──────────────────────────────────────
    if llm and llm.is_available():
        llm_result = _try_llm_review(llm, execution_logs, contract)
        if llm_result:
            # Still validate with deterministic engine
            report = compute_confidence(execution_logs, contract)
            # Use LLM issues + deterministic confidence
            return {
                "verdict": report.verdict,
                "confidence": report.confidence,
                "hypothesis_evaluation": report.hypothesis_evaluation,
                "identified_issues": report.identified_issues + llm_result.get("identified_issues", []),
                "proposed_next_actions": llm_result.get("proposed_next_actions", []),
            }

    # ── Pure deterministic path ──────────────────────────────────────
    report = compute_confidence(execution_logs, contract)

    return {
        "verdict": report.verdict,
        "confidence": report.confidence,
        "hypothesis_evaluation": report.hypothesis_evaluation,
        "identified_issues": report.identified_issues,
        "proposed_next_actions": [
            {"action": "Run with additional seeds", "reason": "improve statistical power"}
        ] if report.verdict != "conclusive" else [],
    }


def _try_llm_review(llm, logs, contract) -> Dict | None:
    """LLM-enhanced review for richer issue identification."""
    from are.core.priors import get_priors_text

    priors = get_priors_text()
    hypotheses = contract.get("hypotheses", {})
    hyp_str = "\n".join(
        f"- {k}: {v.get('statement', '')}" for k, v in hypotheses.items()
    )
    prompt = f"""You are a scientific review agent for LLM Quantization.

{priors}

Hypotheses Under Review:
{hyp_str}

Execution Summary: {len(logs)} experiment logs.

Evaluate, identify issues, and suggest next actions.

Return JSON:
{{"identified_issues": ["..."], "proposed_next_actions": [{{"action": "...", "reason": "..."}}]}}"""

    resp = llm.generate(prompt, mode=LLMMode.JUDGMENT, expect_json=True)
    if resp.success and resp.parsed:
        return resp.parsed
    return None
