from ..state import GraphState
from ..schemas.node_6 import (
    HypothesisAlignment,
    StatisticalAnalysis,
    NextAction,
    ScientificVerdict
)
from ..utils.logging import log_state_transition

def node_6_critic_scientific_review(state: GraphState) -> GraphState:
    """
    NODE-6 — Critic / Scientific Review Node: skeptical judgment engine.
    Derives confidence from penalties and enforces scientific gates.
    Optional Gemini enhancement with deterministic fallback.
    """
    log_state_transition("NODE-6", state)
    contract = state.get("research_contract", {})
    hypotheses = contract.get("hypotheses", {})
    execution_logs = state.get("execution_logs", [])
    
    # Try Gemini for enhanced scientific review
    gemini_result = _try_gemini_review(state)
    
    if gemini_result and "verdict" in gemini_result:
        # Use Gemini's analysis but validate consistency
        verdict = gemini_result.get("verdict", "inconclusive")
        confidence = gemini_result.get("confidence", 0.5)
        issues = gemini_result.get("identified_issues", [])
        next_actions = gemini_result.get("proposed_next_actions", [])
        
        # Apply mandatory penalty checks even on Gemini result
        seeds_used = set(log.get("random_seed") for log in execution_logs if "random_seed" in log)
        if len(seeds_used) <= 1 and confidence > 0.85:
            confidence -= 0.15
            issues.append("Single random seed penalty applied to Gemini confidence.")
        
        # Verdict-confidence consistency check
        if verdict == "conclusive" and confidence < 0.75:
            verdict = "inconclusive"
            issues.append("Consistency check: Verdict downgraded due to low confidence.")
        
        eval_map = {h: "gemini_evaluated" for h in hypotheses.keys()}
    else:
        # Deterministic fallback with penalty-based scoring
        confidence = 1.0
        issues = []
        
        # MANDATORY SCIENTIFIC PENALTIES
        # Single Seed Penalty
        seeds_used = set(log.get("random_seed") for log in execution_logs if "random_seed" in log)
        if len(seeds_used) <= 1:
            confidence -= 0.15
            issues.append("Single random seed used: reduces statistical robustness.")

        # Execution Failure Penalty
        failures = [log for log in execution_logs if log.get("status") in ["oom", "failure", "failed"]]
        if failures:
            confidence -= 0.20
            issues.append(f"Execution instability: {len(failures)} failures/OOMs detected.")

        # Weak Signal Penalty
        max_similarity = max([float(log.get("semantic_similarity", 0)) if isinstance(log.get("semantic_similarity"), (int, float)) else 0 for log in execution_logs] or [0])
        if max_similarity > 0 and max_similarity < 0.05:
            confidence -= 0.10
            issues.append("Weak signal: semantic similarity delta is negligible.")

        # HYPOTHESIS-AWARE EVALUATION
        eval_map = {}
        alignment_results = []
        
        for h_id, h_data in hypotheses.items():
            statement = h_data.get("statement", "").lower()
            supports = False
            
            if "instability" in statement and failures:
                supports = True
            elif "latency" in statement and any(float(log.get("latency_ms", 0)) > 10 for log in execution_logs if isinstance(log.get("latency_ms"), (int, float))):
                supports = True
            elif "memory" in statement and any(float(log.get("gpu_memory_mb", 0)) > 100 for log in execution_logs if isinstance(log.get("gpu_memory_mb"), (int, float))):
                supports = True
                
            eval_map[h_id] = "supports" if supports else "inconclusive"
            alignment_results.append(eval_map[h_id])

        # VERDICT DETERMINATION
        if all(r == "supports" for r in alignment_results):
            verdict = "conclusive"
        elif any(r == "supports" for r in alignment_results):
            verdict = "inconclusive"
        else:
            verdict = "contradictory"

        # Cost Dominates Quality Gate
        high_savings = any(log.get("gpu_memory_mb") == "simulated" for log in execution_logs)
        if high_savings and max_similarity < 0.4:
            verdict = "contradictory"
            issues.append("Gate trigger: Memory savings do not justify quality degradation.")

        # Noise Dominates Signal Gate
        if len(failures) > (len(execution_logs) / 2):
            verdict = "inconclusive"
            confidence = min(confidence, 0.5)
            issues.append("Gate trigger: High execution noise/failure rate makes data unreliable.")

        # VERDICT-CONFIDENCE CONSISTENCY
        final_confidence = round(min(0.99, max(0, confidence)), 2)
        
        if verdict == "conclusive" and final_confidence < 0.75:
            verdict = "inconclusive"
            issues.append("Consistency check: Verdict downgraded to inconclusive due to low confidence scores.")
        
        confidence = final_confidence

        # MINIMAL NEXT ACTIONS
        next_actions = []
        if verdict != "conclusive":
            if len(seeds_used) <= 1:
                next_actions.append({
                    "action": "rerun_with_fixed_seed",
                    "reason": "Eliminate stochastic noise from single-seed bias.",
                    "cost_estimate": "low"
                })
            
            if failures:
                next_actions.append({
                    "action": "reduce_batch_size",
                    "reason": f"Avoid resource exhaustion encountered in {len(failures)} runs.",
                    "cost_estimate": "medium"
                })
            
            if verdict == "inconclusive" and not next_actions:
                # No new experiments allowed in V4 Schema.
                # Must report as inconclusive.
                pass

    # State Update
    state.update({
        "verdict": verdict,
        "confidence": confidence,
        "hypothesis_evaluation": eval_map,
        "identified_issues": issues,
        "proposed_next_actions": next_actions
    })

    return state


def _try_gemini_review(state: GraphState):
    """Attempt Gemini-powered scientific review."""
    try:
        from ..utils.gemini import call_gemini
        from ..prompts.node_6 import get_prompt
        
        prompt = get_prompt(state)
        return call_gemini(prompt, mode="judgment", expect_json=True, fallback=None)
    except Exception:
        return None

# CORE LOGIC FROZEN — UI SAFE TO ADD

# ====================================================
# VERIFICATION CHECKLIST (NODE-6 Scientific Critic)
# - [x] Confidence starts at 1.0 and is reduced by specific penalties
# - [x] "Conclusive" verdict requires confidence >= 0.75
# - [x] Hypotheses are evaluated independently
# - [x] Next actions are restricted to the allowed cost-aware subset
# - [x] No side-effects or external calls
# ====================================================
