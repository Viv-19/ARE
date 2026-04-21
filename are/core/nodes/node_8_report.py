"""
NODE-8 -- Reducer & Report Generator.

TWO MODES:
1. LITERATURE REVIEW (well-studied path):
   - Generates a literature review from top papers with links.
   - Uses ONE LLM call to write a synthesis abstract.

2. EXPERIMENT REPORT (novel/partial path):
   - Full scientific report from evidence + experiments + evaluation.
   - Uses ONE LLM call for the narrative abstract.

Both modes produce Markdown + JSON outputs.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from are.core.nodes._tracing import traced_node
from are.core.priors import get_priors_text
from are.ports.llm_port import LLMMode

logger = logging.getLogger(__name__)


@traced_node("NODE-8")
def node_8_report(state: Dict[str, Any]) -> Dict[str, Any]:
    """Synthesise final report from accumulated state."""

    ctx = state.get("_ctx", {})
    llm = ctx.get("llm")
    research_status = state.get("research_status", "novel")

    # ── Route to the appropriate report mode ─────────────────────────
    if research_status == "well-studied":
        md, report_json = _build_literature_review(state, llm)
    else:
        md, report_json = _build_experiment_report(state, llm)

    # ── Persist to disk ──────────────────────────────────────────────
    try:
        os.makedirs("reports", exist_ok=True)
        ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        with open(f"reports/report_{ts_str}.md", "w", encoding="utf-8") as f:
            f.write(md)
        with open(f"reports/report_{ts_str}.json", "w", encoding="utf-8") as f:
            json.dump(report_json, f, indent=2, default=str)
        logger.info("[NODE-8] Reports saved to reports/")
    except OSError as exc:
        logger.warning("[NODE-8] Could not persist reports: %s", exc)

    return {
        "report_markdown": md,
        "report_json": report_json,
    }


# ── LITERATURE REVIEW MODE ───────────────────────────────────────────────

def _build_literature_review(state: Dict, llm) -> tuple:
    """Generate a literature review for well-studied topics."""

    question = state.get("research_question", "")
    normalized = state.get("normalized_question", question)
    top_papers = state.get("top_papers", [])
    evidence = state.get("evidence", top_papers)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # ── Try LLM synthesis (single call) ─────────────────────────────
    llm_synthesis = ""
    if llm and llm.is_available() and evidence:
        llm_synthesis = _try_llm_synthesis(llm, question, evidence)

    # ── Paper table ─────────────────────────────────────────────────
    paper_rows = ""
    for i, p in enumerate(evidence[:10], 1):
        title = p.get("title", "N/A")[:70]
        url = p.get("url", "")
        year = p.get("year", "-")
        cites = p.get("citation_count", 0)
        source = p.get("source", "-")
        # Make title a clickable link if URL exists
        title_cell = f"[{title}]({url})" if url else title
        paper_rows += f"| {i} | {title_cell} | {year} | {cites} | {source} |\n"

    # ── Top 5 recommended papers ────────────────────────────────────
    top5_list = ""
    for i, p in enumerate(evidence[:5], 1):
        title = p.get("title", "N/A")
        url = p.get("url", "")
        year = p.get("year", "")
        authors = p.get("authors", [])
        author_str = ", ".join(authors[:3])
        if len(authors) > 3:
            author_str += " et al."
        abstract = p.get("abstract", "")[:200]
        link = f"  **Link**: [{url}]({url})" if url else "  *No URL available*"

        top5_list += f"""
### {i}. {title}
- **Authors**: {author_str}
- **Year**: {year}
{link}
- **Abstract**: {abstract}{'...' if len(p.get('abstract', '')) > 200 else ''}

"""

    md = f"""# Literature Review: {question}

> Generated: {ts} | Mode: Literature Review (Well-Studied Topic)

---

## Executive Summary

{llm_synthesis or f"This is an automated literature review for the topic: **{normalized}**. The system identified that this topic is **well-studied** in the current literature, with {len(evidence)} relevant papers found across academic databases. Below are the top recommended papers and a comprehensive overview."}

## Status: Well-Studied Topic

This research area has sufficient existing literature. Rather than conducting new experiments, this report provides a curated literature review with the most relevant papers.

---

## Top 5 Recommended Papers

{top5_list}

---

## Full Evidence Table

| # | Title | Year | Citations | Source |
|---|-------|------|-----------|--------|
{paper_rows or '| - | No papers found | - | - | - |'}

---

## Research Landscape

- **Total papers surveyed**: {len(evidence)}
- **Knowledge maturity**: High
- **Recommendation**: This topic has extensive coverage. Consider narrowing your scope to a specific sub-problem for original research contributions.

## Suggested Narrower Research Questions

Based on the literature, consider investigating:
1. Specific quantitative comparisons between techniques
2. Under-explored edge cases or model architectures
3. Novel combinations of existing approaches

---
*Report generated by AROS v2.0 -- Autonomous Research Orchestration System*
"""

    report_json = {
        "type": "literature_review",
        "question": question,
        "research_status": "well-studied",
        "papers_surveyed": len(evidence),
        "top_papers": [
            {
                "title": p.get("title"),
                "url": p.get("url"),
                "year": p.get("year"),
                "citations": p.get("citation_count", 0),
                "source": p.get("source"),
            }
            for p in evidence[:5]
        ],
        "synthesis": llm_synthesis,
    }

    return md, report_json


# ── EXPERIMENT REPORT MODE ───────────────────────────────────────────────

def _build_experiment_report(state: Dict, llm) -> tuple:
    """Generate a full experiment report for novel/partial topics."""

    question = state.get("research_question", "")
    normalized = state.get("normalized_question", question)
    verdict = state.get("verdict", "inconclusive")
    confidence = state.get("confidence", 0.0)
    evidence = state.get("evidence", [])
    gaps = state.get("knowledge_gaps", [])
    contract = state.get("research_contract", {})
    exec_logs = state.get("execution_logs", [])
    hyp_eval = state.get("hypothesis_evaluation", {})
    issues = state.get("identified_issues", [])
    variables = state.get("variables", {})
    mode = state.get("execution_mode", "dry_run")
    seed = state.get("random_seed", 42)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # ── Try LLM narrative (single call) ──────────────────────────────
    llm_narrative = ""
    if llm and llm.is_available():
        try:
            llm_narrative = _try_llm_narrative(llm, state)
        except Exception as exc:
            logger.warning("[NODE-8] LLM narrative failed: %s", exc)

    # ── Evidence table ──────────────────────────────────────────────
    ev_rows = ""
    for p in evidence[:10]:
        title = p.get("title", "N/A")[:50]
        url = p.get("url", "")
        title_cell = f"[{title}]({url})" if url else title
        ev_rows += (
            f"| {title_cell} | {p.get('year', '-')} | "
            f"{p.get('citation_count', 0)} | {p.get('source', '-')} |\n"
        )

    exec_rows = ""
    for log in exec_logs:
        exec_rows += (
            f"| {log.get('experiment_id', '-')} | {log.get('quantization', '-')} | "
            f"{log.get('latency_ms', '-')} | {log.get('status', '-')} |\n"
        )

    hyp_lines = "\n".join(f"- **{k}**: {v}" for k, v in hyp_eval.items()) or "- No hypotheses evaluated."
    gap_lines = "\n".join(f"- {g}" for g in gaps) or "- None identified."
    issue_lines = "\n".join(f"- {i}" for i in issues) or "- None."

    md = f"""# Research Report: {question}

> Generated: {ts} | Mode: {mode} | Seed: {seed}

---

## 1. Abstract

{llm_narrative or f"This report presents the findings of an automated research investigation into: {normalized}. The system collected {len(evidence)} academic papers, identified {len(gaps)} knowledge gaps, and executed {len(exec_logs)} experiments. The final verdict is **{verdict.upper()}** with {confidence:.0%} confidence."}

## 2. Methodology

| Parameter | Value |
|-----------|-------|
| Execution Mode | {mode} |
| Random Seed | {seed} |
| Max Experiments | {contract.get('constraints', {}).get('max_experiments', 'N/A')} |
| Independent Vars | {', '.join(variables.get('independent', []))} |
| Dependent Vars | {', '.join(variables.get('dependent', []))} |
| Control Vars | {', '.join(variables.get('control', []))} |

## 3. Evidence Base

| Title | Year | Citations | Source |
|-------|------|-----------|--------|
{ev_rows or '| No papers collected | - | - | - |'}

### Knowledge Gaps
{gap_lines}

## 4. Experiment Results

| ID | Method | Latency (ms) | Status |
|----|--------|--------------|--------|
{exec_rows or '| No experiments | - | - | - |'}

## 5. Hypothesis Evaluation

{hyp_lines}

## 6. Scientific Verdict

- **Verdict**: {verdict.upper()}
- **Confidence**: {confidence:.2%}

## 7. Identified Issues

{issue_lines}

## 8. Scientific Assumptions

{get_priors_text()}

## 9. Limitations

- Hardware constraints limited experiment scope.
- Single-seed runs reduce statistical power.
- Dry-run mode produces simulated metrics, not empirical measurements.

## 10. Future Work

- Expand seed diversity for statistical robustness.
- Test on larger models (7B+) to assess scale-dependent effects.
- Measure KV-cache precision sensitivity independently.

---
*Report generated by AROS v2.0 -- Autonomous Research Orchestration System*
"""

    report_json = {
        "type": "experiment_report",
        "abstract": f"Investigation into: {question}",
        "methodology": {"contract": contract, "papers_collected": len(evidence)},
        "results_table": {
            "columns": ["experiment_id", "quantization", "latency_ms", "status"],
            "rows": [
                [log.get("experiment_id"), log.get("quantization"),
                 log.get("latency_ms"), log.get("status")]
                for log in exec_logs
            ],
        },
        "hypothesis_evaluation": hyp_eval,
        "final_verdict": verdict,
        "confidence": confidence,
        "identified_issues": issues,
    }

    return md, report_json


# ── LLM helpers (each is exactly ONE LLM call) ────────────────────────────

def _try_llm_synthesis(llm, question: str, papers: list) -> str:
    """Generate an LLM-powered literature synthesis abstract. ONE call."""
    paper_summaries = "\n".join(
        f"- {p.get('title', '?')} ({p.get('year', '?')}): {p.get('abstract', 'N/A')[:150]}"
        for p in papers[:5]
    )
    prompt = (
        f"You are a research synthesis expert. Write a 4-5 sentence executive summary "
        f"for a literature review on: \"{question}\".\n\n"
        f"Key papers found:\n{paper_summaries}\n\n"
        f"Synthesize the current state of research. Be specific about findings, not generic. "
        f"Write in a scholarly but accessible tone."
    )
    resp = llm.generate(prompt, mode=LLMMode.COMMUNICATION, expect_json=False)
    if resp.success and resp.content:
        return resp.content
    return ""


def _try_llm_narrative(llm, state: Dict) -> str:
    """Generate an LLM-written experiment abstract. ONE call."""
    prompt = (
        f"Write a 3-4 sentence scientific abstract for a study on: "
        f"\"{state.get('research_question', '')}\". "
        f"Verdict: {state.get('verdict', 'inconclusive')}. "
        f"Confidence: {state.get('confidence', 0.0):.2f}. "
        f"Experiments: {len(state.get('execution_logs', []))}. "
        f"Papers reviewed: {len(state.get('evidence', []))}. "
        f"Be empirical and neutral."
    )
    resp = llm.generate(prompt, mode=LLMMode.COMMUNICATION, expect_json=False)
    if resp.success and resp.content:
        return resp.content
    return ""
