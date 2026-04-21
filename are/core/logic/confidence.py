"""
Confidence scoring — penalty-based scientific confidence engine.

Pure computation used by NODE-6.  Takes execution logs + contract,
returns verdict + calibrated confidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from are.core.constants import (
    CONCLUSIVE_MIN_CONFIDENCE,
    CONFIDENCE_FLOOR,
    NOISE_CONFIDENCE_CAP,
    NOISE_FAILURE_RATIO,
    PENALTY_EXECUTION_FAILURE,
    PENALTY_SINGLE_SEED,
    PENALTY_WEAK_SIGNAL,
)


@dataclass
class ConfidenceReport:
    """Structured output of the confidence engine."""

    verdict: str  # conclusive | inconclusive | contradictory
    confidence: float
    penalties_applied: List[str] = field(default_factory=list)
    identified_issues: List[str] = field(default_factory=list)
    hypothesis_evaluation: Dict[str, str] = field(default_factory=dict)


def compute_confidence(
    execution_logs: List[Dict[str, Any]],
    contract: Dict[str, Any],
) -> ConfidenceReport:
    """Score confidence via penalty subtraction.

    Starts at 1.0, subtracts for each detected weakness.
    Enforces verdict-confidence consistency at the end.
    """
    # ── Guard: no data at all ────────────────────────────────────────
    if not execution_logs:
        return ConfidenceReport(
            verdict="inconclusive",
            confidence=0.0,
            penalties_applied=["No execution data"],
            identified_issues=["No execution logs to evaluate."],
            hypothesis_evaluation={
                k: "insufficient_data" for k in contract.get("hypotheses", {})
            },
        )

    confidence = 1.0
    penalties: List[str] = []
    issues: List[str] = []

    # ── Penalty: single seed ─────────────────────────────────────────
    seeds_used = {log.get("random_seed") for log in execution_logs if log.get("random_seed")}
    if len(seeds_used) <= 1:
        confidence -= PENALTY_SINGLE_SEED
        confidence = max(CONFIDENCE_FLOOR, confidence)
        penalties.append(f"Single-seed penalty: -{PENALTY_SINGLE_SEED}")
        issues.append("Only one random seed used — insufficient for stability claims.")

    # ── Penalty: execution failures ──────────────────────────────────
    failure_statuses = {"failure", "oom", "error", "failed"}
    failures = [
        log for log in execution_logs
        if log.get("status", "").lower() in failure_statuses
    ]
    if failures:
        confidence -= PENALTY_EXECUTION_FAILURE
        confidence = max(CONFIDENCE_FLOOR, confidence)
        penalties.append(f"Execution-failure penalty: -{PENALTY_EXECUTION_FAILURE}")
        issues.append(f"{len(failures)}/{len(execution_logs)} experiments failed or OOM.")

    # ── Penalty: weak signal ─────────────────────────────────────────
    similarities = [
        log.get("semantic_similarity", 0.0)
        for log in execution_logs
        if "semantic_similarity" in log
    ]
    if similarities and max(similarities) < 0.05:
        confidence -= PENALTY_WEAK_SIGNAL
        confidence = max(CONFIDENCE_FLOOR, confidence)
        penalties.append(f"Weak-signal penalty: -{PENALTY_WEAK_SIGNAL}")
        issues.append("Semantic similarity below sensitivity threshold.")

    # ── Gate: noise dominates ────────────────────────────────────────
    if execution_logs and len(failures) / max(len(execution_logs), 1) > NOISE_FAILURE_RATIO:
        confidence = min(confidence, NOISE_CONFIDENCE_CAP)
        issues.append("Majority of experiments failed — noise dominates signal.")

    # ── Floor ────────────────────────────────────────────────────────
    confidence = max(CONFIDENCE_FLOOR, confidence)

    # ── Hypothesis evaluation ────────────────────────────────────────
    hypotheses = contract.get("hypotheses", {})
    hyp_eval: Dict[str, str] = {}
    for hid in hypotheses:
        if confidence >= CONCLUSIVE_MIN_CONFIDENCE and not failures:
            hyp_eval[hid] = "supports"
        else:
            hyp_eval[hid] = "inconclusive"

    # ── Verdict derivation ───────────────────────────────────────────
    if execution_logs and len(failures) > len(execution_logs) // 2:
        verdict = "contradictory"
    elif confidence >= CONCLUSIVE_MIN_CONFIDENCE:
        verdict = "conclusive"
    else:
        verdict = "inconclusive"

    # ── Verdict-confidence consistency  (B-11 fix) ───────────────────
    if verdict == "conclusive" and confidence < CONCLUSIVE_MIN_CONFIDENCE:
        verdict = "inconclusive"

    return ConfidenceReport(
        verdict=verdict,
        confidence=round(confidence, 4),
        penalties_applied=penalties,
        identified_issues=issues,
        hypothesis_evaluation=hyp_eval,
    )
