"""
NODE-1 — Knowledge Assessment / Router
Epistemic validation and routing based on knowledge state.
"""

from ..state import GraphState
from ..schemas.node_1 import (
    SelfKnowledgeEstimation,
    CitationMetadata,
    CitationEvaluation,
    KnowledgeAssessmentOutput
)
from ..tools.semantic_scholar import search as ss_search
from ..tools.arxiv import search as arxiv_search
from ..utils.logging import log_state_transition
import logging

logger = logging.getLogger(__name__)

def node_1_knowledge_assessment_router(state: GraphState) -> GraphState:
    """
    NODE-1 — Router / Knowledge Assessment Node: Assess whether the question is well-studied, partial, or novel.
    Performs epistemic validation using Gemini's self-knowledge assessment and applies hard citation-quality thresholds.
    """
    log_state_transition("NODE-1", state)
    
    # Immutable constants
    MIN_PAPERS = 3
    MIN_CITATIONS_PER_PAPER = 100

    question = state.get("normalized_question", state.get("research_question", ""))
    print(f"[NODE-1] Assessing knowledge state for: {question[:60]}...")
    logger.info(f"[NODE-1] Starting knowledge assessment for: {question[:80]}...")

    # Stage 1 — Self-Knowledge Estimation via Gemini
    gemini_assessment = _try_gemini_assessment(state)
    
    if gemini_assessment:
        logger.info(f"[NODE-1] ✓ Gemini epistemic assessment: {gemini_assessment.get('research_status', 'unknown')}")
        self_knowledge = {
            "self_assessed_familiarity": 0.75 if gemini_assessment.get("research_status") == "well-studied" else 0.4,
            "known_concepts": gemini_assessment.get("gaps_identified", [])[:3],
            "uncertain_concepts": gemini_assessment.get("gaps_identified", [])[3:] if len(gemini_assessment.get("gaps_identified", [])) > 3 else []
        }
    else:
        logger.info("[NODE-1] Using default self-knowledge estimation")
        self_knowledge = {
            "self_assessed_familiarity": 0.65,
            "known_concepts": ["post-training quantization", "INT8 inference"],
            "uncertain_concepts": ["INT4 residual numerical stability"]
        }

    # Stage 2 — Verifiable Citation Check (Tool-based)
    print("[NODE-1] Fetching academic citations...")
    logger.info("[NODE-1] Querying Semantic Scholar and ArXiv...")
    
    ss_results, ss_rate_limited = ss_search(question)
    if ss_rate_limited:
        logger.warning("[NODE-1] Semantic Scholar rate limit detected - results may be mock data")
        
    arxiv_results = arxiv_search(question)
    retrieved_citations = ss_results + arxiv_results
    
    logger.info(f"[NODE-1] Retrieved {len(retrieved_citations)} citations (SS: {len(ss_results)}, ArXiv: {len(arxiv_results)})")

    # Stage 3 — Minimum Citation Count Threshold (Hard Gate)
    total_found = len(retrieved_citations)
    above_threshold = [c for c in retrieved_citations if c.get("citation_count", 0) >= MIN_CITATIONS_PER_PAPER]
    
    # Check relevance based on title/abstract matching key terms
    key_terms = ["quantization", "int4", "int8", "transformer", "llm", "inference", "residual"]
    directly_relevant = sum(
        1 for c in above_threshold 
        if any(term in (c.get("title", "") + c.get("abstract", "")).lower() for term in key_terms)
    )

    citation_eval = {
        "total_papers_found": total_found,
        "papers_above_citation_threshold": len(above_threshold),
        "directly_relevant_papers": directly_relevant,
        "citation_threshold": MIN_CITATIONS_PER_PAPER,
        "top_cited_papers": [
            {"title": p.get("title", "")[:50], "citations": p.get("citation_count", 0)}
            for p in sorted(above_threshold, key=lambda x: x.get("citation_count", 0), reverse=True)[:3]
        ]
    }
    
    logger.info(f"[NODE-1] Citation analysis: {len(above_threshold)} papers above threshold, {directly_relevant} directly relevant")

    # STRICT DETERMINISTIC LOGIC (V4 Spec)
    # A question is well-studied ONLY IF:
    # 1. ≥ MIN_PAPERS (3) directly relevant papers
    # 2. Each has ≥ MIN_CITATIONS (100)
    
    is_well_studied = (len(above_threshold) >= MIN_PAPERS) and (directly_relevant >= MIN_PAPERS)
    
    if is_well_studied:
        research_status = "well-studied"
        knowledge_confidence = "high"
        evidence_required = False
        path = "Survey Only (NODE-8)"
        reasoning_summary = (
            f"Topic is WELL-STUDIED. Found {directly_relevant} directly relevant papers with >{MIN_CITATIONS_PER_PAPER} citations. "
            "Sufficient evidence exists for a survey report without new experiments."
        )
    elif len(above_threshold) > 0:
        research_status = "partial"
        knowledge_confidence = "medium"
        evidence_required = True
        path = "Evidence Collection + Experiments (NODE-2)"
        reasoning_summary = (
            f"Topic is PARTIALLY explored. Found {len(above_threshold)} cited papers, but only {directly_relevant} match specific terms. "
            "Proceeding to evidence collection and experimental validation."
        )
    else:
        research_status = "novel"
        knowledge_confidence = "low"
        evidence_required = True
        path = "Evidence Collection + Experiments (NODE-2)"
        reasoning_summary = (
            f"Topic appears NOVEL. No papers found above {MIN_CITATIONS_PER_PAPER} citations matching criteria. "
            "Full experimental grounding required."
        )
    
    # Add Gemini assessment as context only, NOT for routing
    if gemini_assessment:
        reasoning_summary += f" [Gemini Concordance: {gemini_assessment.get('research_status', 'N/A')}]"

    # State Update
    state.update({
        "knowledge_confidence": knowledge_confidence,
        "research_status": research_status,
        "evidence_required": evidence_required,
        "citation_summary": citation_eval,
        "reasoning": reasoning_summary,  # Add reasoning for UI
        "reasoning_summary": reasoning_summary
    })

    print(f"[NODE-1] ✓ Assessment complete. Status: {research_status}, Evidence Required: {evidence_required}")
    logger.info(f"[NODE-1] ✓ Complete. Status: {research_status}, Confidence: {knowledge_confidence}")

    return state


def _try_gemini_assessment(state: GraphState):
    """Attempt Gemini-powered epistemic assessment."""
    try:
        from ..config import USE_GEMINI
        if not USE_GEMINI:
            return None
            
        from ..utils.gemini import call_gemini
        from ..prompts.node_1 import get_prompt
        
        prompt = get_prompt(state)
        result = call_gemini(prompt, mode="judgment", expect_json=True, fallback=None)
        
        if result:
            logger.info(f"[NODE-1] Gemini assessment keys: {list(result.keys())}")
        return result
    except Exception as e:
        logger.error(f"[NODE-1] Gemini assessment exception: {e}")
        return None

# CORE LOGIC FROZEN — UI SAFE TO ADD
