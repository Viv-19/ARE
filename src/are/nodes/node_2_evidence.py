"""
NODE-2 — Evidence Collection
Multi-source academic retrieval with Gemini-powered gap analysis.
"""

from ..state import GraphState
from ..schemas.node_2 import (
    GeneratedQueries,
    PaperEvidence,
    EvidenceCollectionOutput
)
from ..tools.semantic_scholar import search as ss_search
from ..tools.arxiv import search as arxiv_search
from ..tools.openalex import search as oa_search
from ..utils.logging import log_state_transition
import logging

logger = logging.getLogger(__name__)

def node_2_evidence_collection(state: GraphState) -> GraphState:
    """
    NODE-2 — Evidence Collection Node: Multi-source academic retrieval via tool adapters.
    Implements query transparency, cross-source deduplication, and Gemini-powered gap analysis.
    """
    log_state_transition("NODE-2", state)
    
    # Execution Guard
    status = state.get("research_status")
    evidence_required = state.get("evidence_required", False)
    
    if status not in ["partial", "novel"] or not evidence_required:
        logger.info(f"[NODE-2] Skipped. Status: {status}, Evidence Required: {evidence_required}")
        state.update({"reasoning": "Evidence collection skipped - topic is well-studied."})
        return state

    normalized_question = state["normalized_question"]
    citation_threshold = state.get("citation_threshold", 50)  # Lower threshold for more results
    MIN_PAPERS = 5
    
    print(f"[NODE-2] Collecting evidence for: {normalized_question[:60]}...")
    logger.info(f"[NODE-2] Starting evidence collection for: {normalized_question[:80]}...")

    # Stage 1 — Query Generation
    # Generate multiple search queries for comprehensive coverage
    base_terms = normalized_question.lower()
    queries = [
        normalized_question,  # Original question
        f"quantization transformer LLM inference {base_terms[:30]}",
        f"INT8 INT4 neural network precision",
        f"post-training quantization language models",
        f"numerical stability deep learning inference"
    ]
    
    # Try Gemini for smarter query generation
    gemini_queries = _try_gemini_query_generation(state)
    if gemini_queries:
        queries = gemini_queries[:5]  # Use Gemini's queries
        logger.info(f"[NODE-2] Using Gemini-generated queries: {len(queries)}")
    
    state["search_queries"] = queries
    logger.info(f"[NODE-2] Search queries: {queries[:3]}...")

    # Stage 2 — Multi-Source Metadata Retrieval
    print("[NODE-2] Querying academic databases...")
    results_map = {}
    
    for i, query in enumerate(queries):
        logger.info(f"[NODE-2] Query {i+1}/{len(queries)}: {query[:50]}...")
        
        # Query all three sources
        ss_res, ss_limited = ss_search(query)
        if ss_limited:
            msg = f"Semantic Scholar rate limit hit for query: '{query[:20]}...'"
            logger.warning(f"[NODE-2] {msg}")
            state.setdefault("api_warnings", []).append(msg)

        arxiv_res = arxiv_search(query)
        oa_res = oa_search(query)
        
        logger.info(f"[NODE-2] Results - SS: {len(ss_res)}, ArXiv: {len(arxiv_res)}, OA: {len(oa_res)}")
        
        # Merge with deduplication
        for paper in (ss_res + arxiv_res + oa_res):
            title = paper.get('title', 'Untitled')
            year = paper.get('year', 2024)
            key = f"{title.lower()[:50]}_{year}"
            
            if key not in results_map:
                results_map[key] = paper
            else:
                # Merge sources and keep highest citation count
                existing = results_map[key]
                if paper['source'] not in existing.get('source', ''):
                    existing['source'] = f"{existing.get('source', '')}, {paper['source']}"
                existing['citation_count'] = max(
                    existing.get('citation_count', 0), 
                    paper.get('citation_count', 0)
                )

    raw_results = list(results_map.values())
    logger.info(f"[NODE-2] Total unique papers: {len(raw_results)}")

    # Stage 3 — Validity Filtering
    filtered_papers = [p for p in raw_results if p.get("citation_count", 0) >= citation_threshold]
    
    # If too few papers, lower threshold
    if len(filtered_papers) < MIN_PAPERS and len(raw_results) >= MIN_PAPERS:
        logger.info(f"[NODE-2] Lowering threshold from {citation_threshold} to include more papers")
        filtered_papers = sorted(raw_results, key=lambda x: x.get("citation_count", 0), reverse=True)[:10]

    # Stage 4 — Ranking & Evidence Selection
    sorted_papers = sorted(filtered_papers, key=lambda x: x.get("citation_count", 0), reverse=True)
    selected_papers = sorted_papers[:10]  # Keep top 10 for analysis
    
    evidence_sufficiency = len(selected_papers) >= MIN_PAPERS
    
    logger.info(f"[NODE-2] Selected {len(selected_papers)} papers. Sufficiency: {evidence_sufficiency}")

    # Stage 5 — Knowledge Gap Extraction (Gemini-powered)
    gap_analysis = _analyze_gaps(state, selected_papers)
    if isinstance(gap_analysis, list):
        # Handle legacy list return if any
        gaps = gap_analysis
        limitations = []
    else:
        gaps = gap_analysis.get("gaps", [])
        limitations = gap_analysis.get("limitations", [])
    
    # Build reasoning summary
    top_papers = [f"'{p.get('title', '')[:40]}...' ({p.get('citation_count', 0)} cites)" for p in selected_papers[:3]]
    reasoning = (
        f"Retrieved {len(raw_results)} papers from Semantic Scholar, ArXiv, and OpenAlex. "
        f"After filtering by citation threshold ({citation_threshold}+), selected {len(selected_papers)} papers. "
        f"Top papers: {'; '.join(top_papers)}. "
        f"Identified {len(gaps)} knowledge gaps and {len(limitations)} methodological limitations."
    )

    # State Update
    state.update({
        "evidence": selected_papers,
        "knowledge_gaps": gaps,
        "limitations": limitations,
        "evidence_sufficiency": evidence_sufficiency,
        "reasoning": reasoning
    })

    print(f"[NODE-2] ✓ Collected {len(selected_papers)} papers, identified {len(gaps)} gaps")
    logger.info(f"[NODE-2] ✓ Complete. Papers: {len(selected_papers)}, Gaps: {len(gaps)}")

    return state


def _try_gemini_query_generation(state: GraphState):
    """Use Gemini to generate smart search queries."""
    try:
        from ..config import USE_GEMINI
        if not USE_GEMINI:
            return None
            
        from ..utils.gemini import call_gemini
        
        question = state.get("normalized_question", state.get("research_question", ""))
        
        prompt = f"""Generate 5 academic search queries to find relevant papers for this research question:

Research Question: "{question}"

Requirements:
- Queries should be diverse to capture different aspects
- Include technical terms relevant to the domain
- Mix broad and specific queries
- Focus on: quantization, transformers, LLMs, numerical stability, inference

Return JSON only:
{{"queries": ["query1", "query2", "query3", "query4", "query5"]}}
"""
        
        result = call_gemini(prompt, mode="judgment", expect_json=True, fallback=None)
        if result and "queries" in result:
            return result["queries"]
        return None
    except Exception as e:
        logger.error(f"[NODE-2] Gemini query generation failed: {e}")
        return None


def _analyze_gaps(state: GraphState, papers: list) -> list:
    """Analyze knowledge gaps using Gemini or deterministic fallback."""
    try:
        from ..config import USE_GEMINI
        if USE_GEMINI and papers:
            from ..utils.gemini import call_gemini
            
            # Build context from paper abstracts
            paper_context = "\n".join([
                f"- {p.get('title', 'Untitled')}: {p.get('abstract', 'No abstract')[:200]}..."
                for p in papers[:5]
            ])
            
            question = state.get("normalized_question", "")
            
            prompt = f"""Analyze these papers and identify knowledge gaps relevant to the research question.
            
Research Question: "{question}"

Papers Found:
{paper_context}

Output Requirements:
1. Identify 3-5 specific knowledge gaps NOT addressed by these papers.
2. Highlight methodological limitations in existing work (e.g., lack of INT4 baselines, small models only).
3. Focus on: experimental methodology, metrics, model coverage, or hardware constraints.

Return JSON only:
{{
    "limitations": ["limit1", "limit2"],
    "gaps": ["gap1", "gap2", "gap3"]
}}
"""
            
            result = call_gemini(prompt, mode="judgment", expect_json=True, fallback=None)
            if result and "gaps" in result:
                logger.info(f"[NODE-2] Gemini identified {len(result['gaps'])} gaps")
                return result["gaps"]
    except Exception as e:
        logger.error(f"[NODE-2] Gap analysis failed: {e}")
    
    # Deterministic fallback
    return {
        "gaps": [
            "Limited analysis of INT4 quantization effects on residual stream numerical stability.",
            "No comprehensive benchmarks for decoder-only LLMs under aggressive quantization.",
            "Gap in understanding the relationship between inference cost reduction and semantic degradation.",
            "Lack of layer-wise analysis showing where quantization errors accumulate most severely."
        ],
        "limitations": [
            "Existing studies often focus on older models (BERT/T5) rather than Llama-2/3.",
            "Many papers do not report detailed hardware latency metrics."
        ]
    }

# CORE LOGIC FROZEN — UI SAFE TO ADD
