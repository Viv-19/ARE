"""
NODE-1 — Knowledge Assessment / Epistemic Router.

Queries academic APIs to determine whether the topic is well-studied,
partial, or novel.

KEY BEHAVIOR:
- well-studied: Collects top-5 papers with URLs, stores them as
  `top_papers` for later use by NODE-8 (literature review mode).
  Does NOT call Gemini (saves quota).
- partial/novel: Marks evidence_required=True, proceeds to NODE-2.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from are.core.constants import MIN_CITATIONS_PER_PAPER, MIN_RELEVANT_PAPERS
from are.core.nodes._tracing import traced_node

logger = logging.getLogger(__name__)


def _relevance_score(paper: Dict[str, Any], question: str) -> float:
    """Cheap heuristic relevance: keyword overlap between abstract/title and question."""
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    q_tokens = set(question.lower().split())
    # Only count meaningful words (>3 chars, not stop words)
    stop_words = {"the", "and", "for", "are", "with", "that", "this", "from", "does", "what", "how"}
    q_tokens = {t for t in q_tokens if len(t) > 3 and t not in stop_words}
    overlap = sum(1 for t in q_tokens if t in text)
    return overlap / max(len(q_tokens), 1)


@traced_node("NODE-1")
def node_1_knowledge_assessment_router(state: Dict[str, Any]) -> Dict[str, Any]:
    """Router node: assess existing knowledge via citation analysis.

    NO GEMINI CALL — pure search + heuristic (saves API quota).
    """

    question = state.get("normalized_question", state.get("research_question", ""))
    ctx = state.get("_ctx", {})

    # ── Collect papers from search adapters ───────────────────────────
    search_adapters: List = ctx.get("search_adapters", [])
    all_papers: List[Dict[str, Any]] = []
    api_warnings: List[str] = []

    for adapter in search_adapters:
        try:
            resp = adapter.search(question, max_results=10)
            if resp.rate_limited:
                api_warnings.append(f"{adapter.source_name}: rate-limited, results may be incomplete")
            if resp.error:
                api_warnings.append(f"{adapter.source_name}: {resp.error}")
            for p in resp.papers:
                all_papers.append({
                    "title": p.title,
                    "year": p.year,
                    "authors": list(p.authors),
                    "citation_count": p.citation_count,
                    "venue": p.venue,
                    "abstract": p.abstract[:500],
                    "url": p.url,
                    "source": p.source,
                })
        except Exception as exc:
            logger.warning("[NODE-1] Search %s failed: %s", adapter.source_name, exc)
            api_warnings.append(f"{adapter.source_name}: connection failed")

    # ── Evaluate citations ───────────────────────────────────────────
    above_threshold = [
        p for p in all_papers
        if p.get("citation_count", 0) >= MIN_CITATIONS_PER_PAPER
    ]

    # Score relevance
    for p in all_papers:
        p["_relevance"] = _relevance_score(p, question)

    relevant_above = [p for p in above_threshold if p["_relevance"] > 0.15]

    # ── Sort ALL papers by relevance + citations for the top-5 list ──
    # For well-studied topics, we want the TOP 5 papers with URLs
    all_sorted = sorted(
        all_papers,
        key=lambda p: (p["_relevance"] * 0.4 + min(p["citation_count"], 1000) / 1000 * 0.6),
        reverse=True,
    )
    top_5 = all_sorted[:5]

    # Strip internal scoring field before storing in state
    for p in all_papers:
        p.pop("_relevance", None)

    # ── Determine research status ────────────────────────────────────
    if len(relevant_above) >= MIN_RELEVANT_PAPERS:
        status = "well-studied"
        evidence_req = False
        knowledge_conf = "high"
    elif relevant_above or len(all_papers) >= 5:
        status = "partial"
        evidence_req = True
        knowledge_conf = "medium"
    else:
        status = "novel"
        evidence_req = True
        knowledge_conf = "low"

    reasoning = (
        f"Found {len(all_papers)} papers total, {len(above_threshold)} above "
        f"citation threshold ({MIN_CITATIONS_PER_PAPER}), "
        f"{len(relevant_above)} directly relevant. -> Status: {status}"
    )
    logger.info("[NODE-1] %s", reasoning)

    result = {
        "research_status": status,
        "evidence_required": evidence_req,
        "knowledge_confidence": knowledge_conf,
        "reasoning_summary": reasoning,
        "top_papers": top_5,
        "api_warnings": api_warnings,
    }

    # For well-studied: also store the evidence directly (skip NODE-2)
    if status == "well-studied":
        result["evidence"] = all_sorted[:10]
        result["evidence_sufficiency"] = True
        result["knowledge_gaps"] = []

    return result
