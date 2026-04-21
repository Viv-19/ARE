"""
GraphState — Shared memory for the LangGraph state machine.

Every node receives the full state and returns a **partial dict** of updated
fields.  LangGraph handles the merge.

IMPORTANT: Nodes must NEVER call ``state.update()`` in-place.  Always
``return {"field": value}``.  This fixes bug B-02 from the audit.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class GraphState(TypedDict, total=False):
    """
    Typed shared state flowing through all nodes.

    Organised into lifecycle groups matching the 9-node pipeline.
    ``total=False`` allows incremental partial updates.
    """

    # ── CONTEXT (injected at graph creation, read-only by nodes) ──────────
    _ctx: Dict[str, Any]
    _session_id: str

    # ── 1. INTAKE  (NODE-0) ──────────────────────────────────────────────
    research_question: str
    normalized_question: str
    research_intent: str                # exploratory | replication | optimization | comparison
    intent_confidence: float
    clarification_needed: bool
    clarification_prompt: List[str]      # legacy
    clarification_questions: List[str]   # new: specific clarification Qs
    variables: Dict[str, List[str]]     # {independent, dependent, control}
    autonomy_level: str
    evidence_threshold: str
    researchable: bool
    domain_valid: bool
    reasoning: str

    # ── 2. ROUTER  (NODE-1) ──────────────────────────────────────────────
    research_status: str                # well-studied | partial | novel
    evidence_required: bool
    knowledge_confidence: str
    top_papers: List[Dict[str, Any]]    # top-5 ranked papers with URLs
    api_warnings: List[str]             # search adapter warnings
    reasoning_summary: str

    # ── 3. EVIDENCE  (NODE-2) ────────────────────────────────────────────
    search_queries: List[str]
    evidence: List[Dict[str, Any]]
    knowledge_gaps: List[str]
    evidence_sufficiency: bool

    # ── 4. CONTRACT  (NODE-3 / 4) ────────────────────────────────────────
    research_contract: Dict[str, Any]
    human_decisions: List[Dict[str, Any]]

    # ── 5. EXECUTION  (NODE-5) ───────────────────────────────────────────
    execution_status: str
    execution_logs: List[Dict[str, Any]]
    artifacts: List[Dict[str, Any]]
    experiment_code: str
    experiment_instructions: str

    # ── 6. REVIEW  (NODE-6) ──────────────────────────────────────────────
    verdict: str                        # conclusive | inconclusive | contradictory
    confidence: float
    hypothesis_evaluation: Dict[str, str]
    proposed_next_actions: List[Dict[str, Any]]
    identified_issues: List[str]

    # ── 7. LOOP  (NODE-7) ───────────────────────────────────────────────
    loop_decision: str                  # continue | terminate
    iteration_count: int
    remaining_budget: int

    # ── 8. REPORTING  (NODE-8) ───────────────────────────────────────────
    report_markdown: str
    report_json: Dict[str, Any]

    # ── 9. SYSTEM  (cross-cutting) ──────────────────────────────────────
    execution_mode: str                 # dry_run | local_cpu | gpu
    random_seed: int
    constraints: Dict[str, Any]
    errors: List[str]
