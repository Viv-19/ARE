"""
CLI Runner — interactive terminal interface for ARE.

Runs the graph synchronously, handling HITL interrupts via stdin prompts.
"""

from __future__ import annotations

import json
import logging

from langgraph.types import Command

from are.application.container import Container
from are.application.services.research_service import ResearchService

logger = logging.getLogger(__name__)


def run_cli(container: Container, question: str) -> None:
    """Run a complete research session in the terminal."""

    service = ResearchService(container)
    session = service.start_research(question)
    sid = session["session_id"]
    config = session["config"]

    print(f"\n{'='*70}")
    print(f"  AROS v2.0 — Research Session: {sid}")
    print(f"  Question: {question}")
    print(f"{'='*70}\n")

    # ── Run initial graph execution ──────────────────────────────────
    _run_until_interrupt(service, session["initial_state"], config)

    # ── Handle HITL interrupts ───────────────────────────────────────
    max_resumes = 15
    for i in range(max_resumes):
        state_info = service.get_state(sid)
        next_nodes = state_info.get("next", [])

        if not next_nodes:
            break

        next_node = next_nodes[0] if next_nodes else ""
        print(f"\n⏸  HITL interrupt at: {next_node}")

        if "node_7" in next_node:
            decision = _prompt_loop_decision()
        elif "node_5" in next_node:
            decision = _prompt_experiment_results()
        else:
            decision = _prompt_approval()

        print(f"  → Resuming with: {decision}")
        _resume_until_interrupt(service, sid, decision)

    # ── Print final results ──────────────────────────────────────────
    final = service.get_state(sid)
    values = final.get("values", {})

    print(f"\n{'='*70}")
    print("  RESEARCH COMPLETE")
    print(f"{'='*70}")
    print(f"  Verdict:    {values.get('verdict', 'N/A')}")
    print(f"  Confidence: {values.get('confidence', 'N/A')}")

    report = values.get("report_markdown", "")
    if report:
        print(f"\n{'─'*70}")
        print(report[:2000])
        if len(report) > 2000:
            print(f"\n  ... (report truncated, full version saved to final_report.md)")
    print()


def _run_until_interrupt(service, initial_state, config):
    """Run graph from initial state, printing events."""
    for event in service.run_graph(initial_state, config):
        _print_event(event)


def _resume_until_interrupt(service, sid, decision):
    """Resume graph with decision, printing events."""
    for event in service.resume_graph(sid, decision):
        _print_event(event)


def _print_event(event):
    """Pretty-print a graph stream event."""
    if isinstance(event, dict):
        for node_name, update in event.items():
            if isinstance(update, dict):
                keys = list(update.keys())
                filtered = [k for k in keys if not k.startswith("_")]
                print(f"  ✓ {node_name} → updated: {filtered}")


def _prompt_approval() -> dict:
    """Prompt for HITL approval."""
    print("  Options: [a]pprove / [r]efine / re[j]ect")
    choice = input("  > ").strip().lower()[:1]
    if choice == "r":
        feedback = input("  Feedback: ").strip()
        return {"action": "refine", "feedback": feedback}
    if choice == "j":
        return {"action": "reject", "approval_status": "rejected"}
    return {"action": "approve", "approval_status": "approved"}


def _prompt_loop_decision() -> dict:
    """Prompt for NODE-7 loop decision."""
    print("  Options: [c]ontinue experiments / [s]top and report")
    choice = input("  > ").strip().lower()[:1]
    if choice == "c":
        return {"action": "continue"}
    return {"action": "stop"}


def _prompt_experiment_results() -> dict:
    """Prompt for experiment results JSON."""
    print("  Paste experiment results JSON (or press Enter for mock):")
    raw = input("  > ").strip()
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            print("  ⚠ Invalid JSON, using mock results.")
    return {"results": []}
