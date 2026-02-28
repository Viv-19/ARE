from ..state import GraphState
from ..schemas.node_3 import (
    Hypothesis,
    MetricDefinition,
    ResearchTask,
    ContractConstraints,
    CostEstimate,
    ResearchContract
)
from ..utils.logging import log_state_transition

def node_3_research_contract_orchestration(state: GraphState) -> GraphState:
    """
    NODE-3 — Research Contract / Orchestration Node: Convert gaps into a formal research contract.
    This is the core reasoning and planning node with optional Gemini enhancement.
    """
    log_state_transition("NODE-3", state)
    
    # Execution Guard
    evidence_sufficiency = state.get("evidence_sufficiency", False)
    if not evidence_sufficiency:
        state.update({"errors": state.get("errors", []) + ["Evidence sufficiency failed. Cannot generate contract."]})
        return state

    gaps = state.get("knowledge_gaps", [])
    normalized_question = state["normalized_question"]
    user_constraints = state.get("constraints") or {}

    # Try Gemini for intelligent contract generation
    gemini_result = _try_gemini_contract(state)
    
    if gemini_result and "problem_statement" in gemini_result:
        contract = gemini_result
        # Ensure required fields with defaults
        contract.setdefault("requires_human_approval", True)
        contract.setdefault("constraints", {
            "max_experiments": user_constraints.get("max_experiments", 3),
            "max_gpu_hours": float(user_constraints.get("time_budget_hours", 2)),
            "max_memory_gb": user_constraints.get("max_memory_gb", 16)
        })
    else:
        # Deterministic fallback
        problem_statement = (
            f"This study investigates {normalized_question} by specifically addressing gaps in "
            f"{', '.join(gaps[:2])}. It evaluates the trade-offs between precision and stability."
        )

        hypotheses = {
            "H1": {
                "statement": "INT4 quantization increases logit variance in residual paths compared to INT8 in decoder-only LLMs.",
                "derived_from": gaps[0] if gaps else "General research gap"
            },
            "H2": {
                "statement": "INT8 quantization preserves semantic similarity within 2% relative to FP16 baselines.",
                "derived_from": gaps[1] if len(gaps) > 1 else "General research gap"
            }
        }

        variables = {
            "independent": ["quantization_bitwidth (INT4, INT8)"],
            "dependent": ["residual_logit_variance", "inference_latency", "memory_footprint", "semantic_similarity"],
            "control": ["model_architecture", "dataset", "random_seed"]
        }

        metrics = {
            "residual_logit_variance": {"computed_at": "variance(logits_residual_layerwise)"},
            "inference_latency": {"computed_at": "avg_ms_per_token"},
            "memory_footprint": {"computed_at": "peak_gpu_memory_mb"},
            "semantic_similarity": {"computed_at": "SBERT_cosine_similarity"}
        }

        tasks = [
            {"id": "T1", "description": "Load FP16 baseline model", "type": "setup", "depends_on": []},
            {"id": "T2", "description": "Apply INT8 post-training quantization", "type": "execution", "depends_on": ["T1"]},
            {"id": "T3", "description": "Apply INT4 post-training quantization", "type": "execution", "depends_on": ["T1"]},
            {"id": "T4", "description": "Measure residual logit variance", "type": "execution", "depends_on": ["T2", "T3"]},
            {"id": "T5", "description": "Measure inference latency and memory usage", "type": "execution", "depends_on": ["T2", "T3"]},
            {"id": "T6", "description": "Compute semantic similarity vs FP16", "type": "execution", "depends_on": ["T2", "T3"]}
        ]

        constraints = {
            "max_experiments": user_constraints.get("max_experiments", 3),
            "max_gpu_hours": float(user_constraints.get("time_budget_hours", 2)),
            "max_memory_gb": user_constraints.get("max_memory_gb", 16)
        }

        failure_criteria = [
            "experiment_runtime_exceeds_budget",
            "metrics_variance_unstable",
            "insufficient_statistical_signal"
        ]

        cost_estimate = {
            "expected_gpu_hours": 1.6,
            "expected_memory_gb": 12.0,
            "risk_level": "medium"
        }

        contract = {
            "problem_statement": problem_statement,
            "hypotheses": hypotheses,
            "variables": variables,
            "metrics": metrics,
            "tasks": tasks,
            "constraints": constraints,
            "failure_criteria": failure_criteria,
            "cost_estimate": cost_estimate,
            "requires_human_approval": True
        }

    state.update({"research_contract": contract})
    return state


def _try_gemini_contract(state: GraphState):
    """Attempt Gemini-powered contract generation."""
    try:
        from ..utils.gemini import call_gemini
        from ..prompts.node_3 import get_prompt
        
        prompt = get_prompt(state)
        return call_gemini(prompt, mode="judgment", expect_json=True, fallback=None)
    except Exception:
        return None

# CORE LOGIC FROZEN — UI SAFE TO ADD
