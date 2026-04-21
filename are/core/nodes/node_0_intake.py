"""
NODE-0 — Research Question Intake & Framing.

Converts natural-language questions into formal research specifications.
Uses LLM (via port) when available, deterministic fallback otherwise.

KEY BEHAVIOUR:
- Detects vague/ambiguous queries and sets clarification_needed=True
  with specific questions for the user to answer.
- Only calls Gemini ONCE (rate-limit friendly).

IMPORTANT: Returns a partial dict — never mutates ``state`` in-place.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from are.core.constants import CONFIDENCE_GATE_THRESHOLD
from are.core.logic.domain_validation import get_rejection_reason, is_domain_valid
from are.core.logic.intent_classification import classify_intent
from are.core.logic.variable_extraction import extract_variables
from are.core.nodes._tracing import traced_node
from are.ports.llm_port import LLMMode

logger = logging.getLogger(__name__)


# ── Prompt template ─────────────────────────────────────────────────────

_PROMPT_TEMPLATE = """You are AROS NODE-0 — a senior AI research advisor.

Your role: Analyze a user's research question, assess its clarity and
feasibility, and produce a formal research specification.

=== DOMAIN SCOPE (HARD WHITELIST) ===
Allowed topics:
- LLM Quantization (INT4, INT8, FP16, BF16, GPTQ, AWQ, GGUF)
- Transformer Architecture (attention, MHA/MQA/GQA, decoder-only, encoder-decoder)
- Inference Optimization (KV cache, speculative decoding, flash attention, batching)
- Transformer Internals (residual streams, layer norms, MLP blocks, embeddings)
- Training Efficiency (LoRA, QLoRA, mixed precision, gradient checkpointing)

If the question is OUT OF SCOPE, return: {{"domain_valid": false, "rejection_reason": "<reason>"}}

=== CRITICAL RULES ===
1. If the question is VAGUE or AMBIGUOUS (e.g., just a topic like "KV cache"
   without specifying what to investigate), you MUST set clarification_needed=true
   and provide 2-3 specific clarifying questions.
2. If the question is SPECIFIC and CLEAR (e.g., "Does INT4 quantization reduce
   inference latency without degrading quality in 7B parameter LLMs?"),
   set clarification_needed=false and frame it directly.
3. Extract independent, dependent, and control variables when possible.
4. Be honest about confidence — vague queries should have LOW confidence.

=== USER INPUT ===
"{question}"

=== OUTPUT (strict JSON) ===
{{
  "domain_valid": true,
  "original_question": "<exact input>",
  "normalized_question": "<formal research phrasing, be specific>",
  "research_intent": "<exploratory|replication|optimization|comparison|survey>",
  "reasoning": "<your step-by-step analysis of the user's intent>",
  "intent_confidence": <0.0-1.0>,
  "autonomy_level": "<survey_only|experiment_limited|experiment_iterative>",
  "evidence_threshold": "<literature_only|literature_plus_experiments>",
  "variables": {{
    "independent": ["<var>"],
    "dependent": ["<var>"],
    "control": ["<var>"]
  }},
  "scope_check": {{"is_feasible": true, "is_safe": true}},
  "clarification_needed": <true|false>,
  "clarification_questions": [
    "<specific question 1>",
    "<specific question 2>"
  ]
}}

Return ONLY the JSON object."""


@traced_node("NODE-0")
def node_0_research_question_intake(state: Dict[str, Any]) -> Dict[str, Any]:
    """Intake node: frame the research question."""
    question = state.get("research_question", "").strip()

    # ── Guard: empty input ────────────────────────────────────────────
    if not question:
        return {
            "errors": state.get("errors", []) + ["No research question provided."],
            "domain_valid": False,
        }

    # ── Guard: domain whitelist ───────────────────────────────────────
    if not is_domain_valid(question):
        return {
            "domain_valid": False,
            "errors": state.get("errors", []) + [get_rejection_reason(question)],
            "reasoning": f"Rejected: {get_rejection_reason(question)}",
        }

    # ── Try LLM path (single call — rate limit friendly) ─────────────
    ctx = state.get("_ctx", {})
    llm = ctx.get("llm")

    if llm and llm.is_available():
        prompt = _PROMPT_TEMPLATE.format(question=question)
        resp = llm.generate(prompt, mode=LLMMode.JUDGMENT, expect_json=True)

        if resp.success and resp.parsed:
            p = resp.parsed
            # LLM says out of scope
            if p.get("domain_valid") is False:
                return {
                    "domain_valid": False,
                    "errors": state.get("errors", []) + [
                        p.get("rejection_reason", "Out of scope")
                    ],
                    "reasoning": p.get("rejection_reason", "Out of scope"),
                }

            clarification_needed = bool(p.get("clarification_needed", False))
            clarification_qs = p.get("clarification_questions", [])
            # Also treat very low confidence as needing clarification
            confidence = float(p.get("intent_confidence", 0.5))
            if confidence < 0.5 and not clarification_needed:
                clarification_needed = True
                if not clarification_qs:
                    clarification_qs = [
                        "What specific aspect of this topic do you want to investigate?",
                        "What outcome or metric are you most interested in measuring?",
                    ]

            return {
                "normalized_question": p.get("normalized_question", question),
                "research_intent": p.get("research_intent", "exploratory"),
                "intent_confidence": confidence,
                "autonomy_level": p.get("autonomy_level", "experiment_limited"),
                "evidence_threshold": p.get("evidence_threshold", "literature_plus_experiments"),
                "variables": p.get("variables", extract_variables(question)),
                "clarification_needed": clarification_needed,
                "clarification_questions": clarification_qs,
                "researchable": True,
                "domain_valid": True,
                "reasoning": p.get("reasoning", "LLM-powered framing."),
            }
        logger.warning("[NODE-0] LLM failed (%.0fms), using deterministic.", resp.latency_ms)

    # ── Deterministic fallback ────────────────────────────────────────
    return _deterministic_framing(question, state)


def _deterministic_framing(question: str, state: Dict) -> Dict[str, Any]:
    """Pure-logic fallback when Gemini is unavailable."""
    intent, base_conf = classify_intent(question)
    variables = extract_variables(question)

    # Confidence heuristic: +0.1 per variable category with entries
    conf = base_conf
    if len(variables["independent"]) > 1:
        conf += 0.10
    if len(variables["dependent"]) > 1:
        conf += 0.10
    conf = min(conf, 0.95)

    # Vagueness detection: short queries or missing variables
    word_count = len(question.split())
    has_variables = any(variables[k] for k in ("independent", "dependent"))

    clarification_needed = False
    clarification_questions = []

    if word_count < 8 or not has_variables:
        clarification_needed = True
        conf = min(conf, 0.40)
        clarification_questions = _generate_clarification_questions(question, variables)

    normalized = f"Formal investigation: {question}"
    if "USER FEEDBACK:" in question:
        normalized = f"Refinement of previous query: {question}"
        # User already provided feedback, reduce clarification threshold
        clarification_needed = False
        conf = max(conf, 0.65)

    return {
        "normalized_question": normalized,
        "research_intent": intent,
        "intent_confidence": round(conf, 2),
        "autonomy_level": "experiment_limited",
        "evidence_threshold": "literature_plus_experiments",
        "variables": variables,
        "clarification_needed": clarification_needed,
        "clarification_questions": clarification_questions,
        "researchable": True,
        "domain_valid": True,
        "reasoning": f"Deterministic framing: intent={intent}, confidence={conf:.2f}, "
                     f"clarification={'needed' if clarification_needed else 'not needed'}",
    }


def _generate_clarification_questions(question: str, variables: Dict) -> list:
    """Generate specific clarification questions based on what's missing."""
    questions = []
    q_lower = question.lower()

    if not variables.get("independent"):
        questions.append(
            "What specific technique or method do you want to study? "
            "(e.g., INT4 quantization, KV cache eviction, flash attention)"
        )

    if not variables.get("dependent"):
        questions.append(
            "What outcome are you interested in measuring? "
            "(e.g., inference latency, memory usage, perplexity, output quality)"
        )

    if "compare" not in q_lower and "vs" not in q_lower:
        questions.append(
            "Do you want to compare specific approaches, or survey the current state of research?"
        )

    if not questions:
        questions.append(
            "Could you be more specific? For example: 'Does [method X] improve [metric Y] "
            "for [model type Z]?'"
        )

    return questions[:3]  # Max 3 questions
