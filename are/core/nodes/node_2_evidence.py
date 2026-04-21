"""
NODE-2 — Evidence Collection.

Multi-source academic retrieval with deduplication and gap analysis.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from are.core.logic.deduplication import deduplicate_papers
from are.core.nodes._tracing import traced_node
from are.ports.llm_port import LLMMode

logger = logging.getLogger(__name__)

_DEFAULT_QUERY_SUFFIXES = [
    "",
    " quantization effects",
    " inference latency memory",
    " transformer architecture",
    " residual stream stability",
]


@traced_node("NODE-2")
def node_2_evidence_collection(state: Dict[str, Any]) -> Dict[str, Any]:
    """Collect academic papers from all search adapters, deduplicate, and analyse gaps."""

    question = state.get("normalized_question", state.get("research_question", ""))
    ctx = state.get("_ctx", {})
    search_adapters: List = ctx.get("search_adapters", [])
    llm = ctx.get("llm")

    # ── Generate queries ─────────────────────────────────────────────
    base_query = question[:100]
    queries = [f"{base_query}{suffix}" for suffix in _DEFAULT_QUERY_SUFFIXES]

    # ── Retrieve papers (2 passes max — rate limit friendly) ────────
    all_papers: List[Dict[str, Any]] = []
    for query in queries[:2]:  # 2 queries * N adapters = reasonable API usage
        for adapter in search_adapters:
            try:
                resp = adapter.search(query, max_results=5)
                for p in resp.papers:
                    all_papers.append({
                        "title": p.title,
                        "year": p.year,
                        "authors": list(p.authors),
                        "citation_count": p.citation_count,
                        "venue": p.venue,
                        "abstract": p.abstract,
                        "url": p.url,
                        "source": p.source,
                    })
            except Exception as exc:
                logger.warning("[NODE-2] Search error on '%s' via %s: %s",
                               query[:40], adapter.source_name, exc)

    # ── Deduplicate ──────────────────────────────────────────────────
    unique_papers = deduplicate_papers(all_papers)
    logger.info("[NODE-2] %d papers collected -> %d after dedup", len(all_papers), len(unique_papers))

    # ── Gap analysis ─────────────────────────────────────────────────
    gaps = _analyse_gaps(unique_papers, question, llm)

    evidence_sufficient = len(unique_papers) >= 3 and len(gaps) > 0

    return {
        "search_queries": queries,
        "evidence": unique_papers,
        "knowledge_gaps": gaps,
        "evidence_sufficiency": evidence_sufficient,
    }


def _analyse_gaps(
    papers: List[Dict[str, Any]],
    question: str,
    llm: Any,
) -> List[str]:
    """Identify knowledge gaps via LLM or deterministic fallback.

    Always returns a list of gap strings (fixes B-05 return type inconsistency).
    """
    # ── LLM path ─────────────────────────────────────────────────────
    if llm and llm.is_available():
        titles = "; ".join(p.get("title", "") for p in papers[:10])
        prompt = (
            f"Given these papers:\n{titles}\n\n"
            f"For the question: \"{question}\"\n\n"
            "Identify 2-3 specific knowledge gaps. Return JSON:\n"
            '{"gaps": ["<gap1>", "<gap2>"]}'
        )
        resp = llm.generate(prompt, mode=LLMMode.JUDGMENT, expect_json=True)
        if resp.success and resp.parsed:
            raw_gaps = resp.parsed.get("gaps", [])
            if isinstance(raw_gaps, list):
                return raw_gaps

    # ── Deterministic fallback ────────────────────────────────────────
    gaps = []
    years = [p.get("year", 2024) for p in papers]
    if not any(y >= 2023 for y in years):
        gaps.append("Limited recent work (post-2023) on this specific topic.")
    if not any("residual" in p.get("abstract", "").lower() for p in papers):
        gaps.append("No studies specifically analysing residual stream behaviour under quantisation.")
    if not any("int4" in p.get("title", "").lower() for p in papers):
        gaps.append("No papers focusing on sub-8-bit (INT4) quantisation for this context.")
    if not gaps:
        gaps.append("General gap: limited empirical data for the specific variable configuration.")
    return gaps
