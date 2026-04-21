"""
NODE-3 -- Research Contract Orchestration.

Converts knowledge gaps + evidence into a formal research contract with
hypotheses, metrics, tasks, and cost estimates.

Uses ONE Gemini call when available, with a smart deterministic fallback
that actually uses the evidence and gaps from previous nodes (not hardcoded).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from are.core.nodes._tracing import traced_node
from are.core.priors import get_priors_text
from are.ports.llm_port import LLMMode

logger = logging.getLogger(__name__)


@traced_node("NODE-3")
def node_3_research_contract(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a formal research contract from evidence gaps."""

    # ── Guard: evidence sufficiency ──────────────────────────────────
    if not state.get("evidence_sufficiency"):
        return {
            "errors": state.get("errors", []) + [
                "NODE-3: Cannot generate contract -- evidence insufficient."
            ],
        }

    question = state.get("normalized_question", "")
    gaps = state.get("knowledge_gaps", [])
    variables = state.get("variables", {})
    evidence = state.get("evidence", [])
    constraints = state.get("constraints", {})
    ctx = state.get("_ctx", {})
    llm = ctx.get("llm")

    # ── Try LLM path (single call) ──────────────────────────────────
    if llm and llm.is_available():
        contract = _try_llm_contract(llm, question, gaps, evidence, variables, constraints)
        if contract:
            return {"research_contract": contract}

    # ── Deterministic fallback (context-aware) ───────────────────────
    contract = _build_deterministic_contract(question, gaps, variables, evidence, constraints)
    return {"research_contract": contract}


def _build_deterministic_contract(
    question: str,
    gaps: List[str],
    variables: Dict,
    evidence: List[Dict],
    constraints: Dict,
) -> Dict:
    """Build contract using actual evidence and gaps, not hardcoded values."""

    # Generate hypotheses from actual gaps
    hypotheses = {}
    for i, gap in enumerate(gaps[:3], 1):
        hypotheses[f"H{i}"] = {
            "statement": gap,
            "derived_from": gap,
            "type": "exploratory",
        }

    # If no gaps, generate from variables
    if not hypotheses:
        iv = variables.get("independent", ["the proposed method"])
        dv = variables.get("dependent", ["the target metric"])
        hypotheses["H1"] = {
            "statement": f"Varying {iv[0]} has a measurable effect on {dv[0]}.",
            "derived_from": "Variable analysis",
            "type": "exploratory",
        }

    # Evidence-informed methodology
    recent_papers = [p for p in evidence if p.get("year", 0) >= 2023]
    methods_in_lit = set()
    for p in evidence[:10]:
        abstract_lower = (p.get("abstract", "") + " " + p.get("title", "")).lower()
        for kw in ["gptq", "awq", "gguf", "int4", "int8", "fp16", "bf16", "kv cache",
                    "attention", "flash", "speculative", "pruning"]:
            if kw in abstract_lower:
                methods_in_lit.add(kw.upper())

    contract = {
        "problem_statement": f"Investigate: {question}",
        "hypotheses": hypotheses,
        "variables": variables or {
            "independent": ["Method variant"],
            "dependent": ["Performance metric"],
            "control": ["Model architecture", "Dataset"],
        },
        "methods_identified_in_literature": list(methods_in_lit)[:8],
        "metrics": {
            "primary": "Latency (ms) or Perplexity",
            "secondary": "Memory usage (GB), Throughput (tokens/s)",
            "quality": "Output semantic similarity (cosine)",
        },
        "tasks": [
            {"id": "T1", "description": "Set up baseline model (FP16/FP32)", "type": "setup"},
            {"id": "T2", "description": f"Apply test methods: {', '.join(list(methods_in_lit)[:3]) or 'TBD'}", "type": "execution"},
            {"id": "T3", "description": "Measure metrics across configurations", "type": "analysis"},
            {"id": "T4", "description": "Statistical significance testing", "type": "validation"},
        ],
        "constraints": {
            "max_experiments": constraints.get("max_experiments", 3),
            "max_gpu_hours": constraints.get("max_gpu_hours", 2.0),
            "max_memory_gb": constraints.get("max_vram_gb", 16),
        },
        "evidence_summary": {
            "total_papers": len(evidence),
            "recent_papers": len(recent_papers),
            "knowledge_gaps": len(gaps),
        },
        "failure_criteria": [
            "All experiments fail (OOM/crash)",
            "Results are statistically insignificant",
        ],
        "cost_estimate": {
            "expected_gpu_hours": 1.5,
            "expected_memory_gb": 8.0,
            "risk_level": "medium",
        },
        "requires_human_approval": True,
    }

    return contract


def _try_llm_contract(llm, question, gaps, evidence, variables, constraints) -> Dict | None:
    """Attempt to generate contract via LLM. ONE call."""
    priors = get_priors_text()
    gaps_str = "\n".join(f"- {g}" for g in gaps)
    evidence_str = "\n".join(
        f"- {p.get('title', '?')} ({p.get('year', '?')})" for p in evidence[:5]
    )

    prompt = f"""You are a PhD-level research advisor designing a research contract.

{priors}

Research Question: "{question}"

Key Evidence Found:
{evidence_str}

Identified Knowledge Gaps:
{gaps_str}

Variables: {variables}
Constraints: {constraints}

Generate a research contract as strict JSON with fields:
problem_statement, hypotheses (dict of H1/H2/H3 with statement and derived_from),
variables, metrics, tasks (list with id/description/type),
constraints, failure_criteria, cost_estimate, requires_human_approval.

The hypotheses should be TESTABLE and SPECIFIC to the gaps found.
Return ONLY the JSON object."""

    resp = llm.generate(prompt, mode=LLMMode.JUDGMENT, expect_json=True)
    if resp.success and resp.parsed:
        contract = resp.parsed
        contract.setdefault("requires_human_approval", True)
        return contract
    return None
