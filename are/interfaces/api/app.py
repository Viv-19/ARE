"""
FastAPI Application Factory — creates the server with injected container.

Uses the modern lifespan pattern (fixes B-15) and proper CORS middleware.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from are.application.container import Container
from are.application.services.research_service import ResearchService

logger = logging.getLogger(__name__)


# ── Session model ─────────────────────────────────────────────────────

@dataclass
class Session:
    session_id: str
    status: str = "running"
    current_node: str = ""
    hitl_pending: bool = False
    hitl_decision: Optional[Dict] = None
    events: List[Dict[str, Any]] = field(default_factory=list)
    config: Dict = field(default_factory=dict)
    experiment_code: str = ""
    experiment_results: Optional[Dict] = None


# ── Request / Response models ─────────────────────────────────────────

class ResearchRequest(BaseModel):
    question: str
    execution_mode: str = "dry_run"
    random_seed: int = 42

class ApprovalRequest(BaseModel):
    action: str  # approve | reject | refine | continue | stop
    feedback: Optional[str] = None


# ── App factory ───────────────────────────────────────────────────────

def create_app(container: Container) -> FastAPI:
    """Create and configure the FastAPI application."""

    sessions: Dict[str, Session] = {}
    service = ResearchService(container)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("AROS v2.0 server starting.")
        yield
        logger.info("AROS server shutting down.")

    app = FastAPI(
        title="AROS — Autonomous Research Orchestration System",
        version="2.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Static files ─────────────────────────────────────────────────
    try:
        app.mount("/static", StaticFiles(directory="frontend"), name="static")
    except Exception:
        logger.warning("Frontend directory not found, static files disabled.")

    # ── Routes ───────────────────────────────────────────────────────

    @app.get("/", response_class=HTMLResponse)
    async def serve_frontend():
        try:
            with open("frontend/index.html", "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        except FileNotFoundError:
            return HTMLResponse("<h1>AROS API</h1><p>Frontend not found.</p>")

    @app.post("/api/research")
    async def start_research(req: ResearchRequest, bg: BackgroundTasks):
        session_data = service.start_research(
            req.question,
            execution_mode=req.execution_mode,
            random_seed=req.random_seed,
        )
        sid = session_data["session_id"]

        session = Session(session_id=sid, config=session_data["config"])
        sessions[sid] = session

        bg.add_task(
            _run_graph_background,
            service, session, session_data["initial_state"], session_data["config"],
        )

        return {"session_id": sid, "status": "started"}

    @app.get("/api/status/{session_id}")
    async def get_status(session_id: str):
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(404, "Session not found")
        return {
            "session_id": session_id,
            "status": session.status,
            "current_node": session.current_node,
            "hitl_pending": session.hitl_pending,
        }

    @app.get("/api/events/{session_id}")
    async def stream_events(session_id: str):
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(404, "Session not found")

        async def generate():
            last_idx = 0
            while True:
                if last_idx < len(session.events):
                    for event in session.events[last_idx:]:
                        yield f"data: {json.dumps(event)}\n\n"
                    last_idx = len(session.events)

                if session.status in ("completed", "error"):
                    break
                await asyncio.sleep(0.3)

        return StreamingResponse(generate(), media_type="text/event-stream")

    @app.post("/api/approve/{session_id}")
    async def approve(session_id: str, req: ApprovalRequest):
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(404, "Session not found")
        if not session.hitl_pending:
            raise HTTPException(400, "No HITL decision pending")

        # Build decision dict — include feedback (fixes B-08)
        decision = {"action": req.action}
        if req.action == "approve":
            decision["approval_status"] = "approved"
        elif req.action == "reject":
            decision["approval_status"] = "rejected"
        if req.feedback:
            decision["feedback"] = req.feedback

        session.hitl_decision = decision
        session.events.append({"type": "hitl_resolved", "node": session.current_node})
        return {"status": "decision_submitted"}

    @app.get("/api/report/{session_id}")
    async def get_report(session_id: str):
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(404, "Session not found")

        state = service.get_state(session_id)
        values = state.get("values", {})
        return {
            "verdict": values.get("verdict", "N/A"),
            "confidence": values.get("confidence", 0),
            "markdown": values.get("report_markdown", ""),
            "json": values.get("report_json", {}),
        }

    @app.get("/api/health")
    async def health():
        return {
            "status": "healthy",
            "llm": container.llm.provider_name,
            "search_adapters": [a.source_name for a in container.search_adapters],
        }

    return app


# ── Background graph runner ──────────────────────────────────────────

async def _run_graph_background(
    service: ResearchService,
    session: Session,
    initial_state: Dict,
    config: Dict,
) -> None:
    """Run the graph in a background task, handling HITL interrupts."""
    sid = session.session_id
    timeout = 1800  # 30 min HITL timeout (fixes B-07)

    try:
        session.events.append({"type": "start", "message": f"Research started: {sid}"})

        # Run initial execution (in thread to not block event loop)
        events = await asyncio.to_thread(
            lambda: list(service.run_graph(initial_state, config))
        )
        for event in events:
            _process_event(session, event)

        # Handle HITL interrupt loop
        for _ in range(20):  # Safety limit
            state = service.get_state(sid)
            next_nodes = state.get("next", [])
            if not next_nodes:
                break

            next_node = next_nodes[0]
            session.current_node = next_node
            session.hitl_pending = True

            # Emit HITL event
            values = state.get("values", {})
            session.events.append({
                "type": "hitl_required",
                "node": next_node,
                "payload": _build_hitl_payload(next_node, values),
            })

            # Wait for human decision with timeout (fixes B-07)
            elapsed = 0
            while session.hitl_decision is None:
                await asyncio.sleep(0.5)
                elapsed += 0.5
                if elapsed > timeout:
                    session.hitl_decision = {"action": "approve", "approval_status": "approved"}
                    logger.warning("[%s] HITL timeout -- auto-approved.", sid)
                    break

            decision = session.hitl_decision
            session.hitl_pending = False
            session.hitl_decision = None

            # Resume graph (in thread to not block event loop)
            events = await asyncio.to_thread(
                lambda d=decision: list(service.resume_graph(sid, d))
            )
            for event in events:
                _process_event(session, event)

        # Complete
        state = service.get_state(sid)
        values = state.get("values", {})
        session.status = "completed"
        session.events.append({
            "type": "complete",
            "verdict": values.get("verdict", "N/A"),
            "confidence": values.get("confidence", 0),
            "message": "Research complete.",
        })

    except Exception as exc:
        logger.error("[%s] Graph execution error: %s", sid, exc, exc_info=True)
        session.status = "error"
        session.events.append({"type": "error", "message": str(exc)})


def _process_event(session: Session, event: Dict) -> None:
    """Extract meaningful data from graph stream events and emit
    per-node reasoning so the frontend can show the LLM's thinking."""

    _NODE_DESCRIPTIONS = {
        "node_0": "Research Question Intake -- Analyzing your research question, classifying intent, extracting variables, and framing it as a formal scientific investigation.",
        "node_0_confirmation": "Scope Confirmation -- Waiting for human approval of the framed research question.",
        "node_1": "Knowledge Router -- Searching academic databases and evaluating existing literature to determine research novelty.",
        "node_2": "Evidence Collection -- Querying Semantic Scholar and ArXiv for relevant papers, deduplicating results, and identifying knowledge gaps.",
        "node_3": "Research Contract -- Generating a structured research contract with hypotheses, methodology, and execution plan.",
        "node_4": "Human Approval Gate -- Presenting the research contract for human review and approval.",
        "node_5": "Experiment Worker -- Generating experiment code and executing simulated experiments with controlled variables.",
        "node_6": "Scientific Critic -- Evaluating experiment results, computing confidence scores, and identifying methodological issues.",
        "node_7": "Iteration Gate -- Presenting results for human decision: continue experimenting or finalize.",
        "node_8": "Report Generator -- Synthesizing all evidence, experiments, and evaluations into a final scientific report.",
    }

    if isinstance(event, dict):
        for node_name, update in event.items():
            session.current_node = node_name

            # ── Emit reasoning about what this node is doing ─────────
            node_desc = _NODE_DESCRIPTIONS.get(node_name, node_name)
            session.events.append({
                "type": "node_reasoning",
                "node": node_name,
                "reasoning": f"[{node_name.upper()}] {node_desc}",
            })

            if isinstance(update, dict):
                # ── Extract LLM's actual reasoning from node output ──
                reasoning = update.get("reasoning", "")
                if reasoning:
                    session.events.append({
                        "type": "node_reasoning",
                        "node": node_name,
                        "reasoning": f"LLM output: {reasoning}",
                    })

                # ── Emit key findings per node ───────────────────────
                _emit_node_insights(session, node_name, update)

                # ── Capture experiment code if generated ─────────────
                if "experiment_code" in update:
                    session.experiment_code = update["experiment_code"]
                    session.events.append({
                        "type": "experiment_code_generated",
                        "payload": {
                            "code": update.get("experiment_code", ""),
                            "instructions": update.get("experiment_instructions", ""),
                        },
                    })

                session.events.append({
                    "type": "node_complete",
                    "node": node_name,
                    "payload": {
                        k: v for k, v in update.items()
                        if not k.startswith("_") and k not in ("experiment_code",)
                    },
                })


def _emit_node_insights(session: Session, node: str, update: Dict) -> None:
    """Emit domain-specific reasoning per node so the user sees real progress."""

    if node == "node_0":
        q = update.get("normalized_question", "")
        intent = update.get("research_intent", "")
        conf = update.get("intent_confidence", 0)
        domain = update.get("domain_valid", None)
        if q:
            session.events.append({
                "type": "node_reasoning",
                "node": node,
                "reasoning": (
                    f"Framed question: \"{q}\" | "
                    f"Intent: {intent} ({conf:.0%}) | "
                    f"Domain valid: {domain}"
                ),
            })
        variables = update.get("variables", {})
        if variables:
            iv = ", ".join(variables.get("independent", []))
            dv = ", ".join(variables.get("dependent", []))
            cv = ", ".join(variables.get("control", []))
            session.events.append({
                "type": "node_reasoning",
                "node": node,
                "reasoning": f"Variables extracted -- IV: [{iv}] | DV: [{dv}] | CV: [{cv}]",
            })

    elif node == "node_1":
        status = update.get("research_status", "")
        if status:
            session.events.append({
                "type": "node_reasoning",
                "node": node,
                "reasoning": f"Literature assessment: Topic is '{status}'. Proceeding to {'report' if status == 'well-studied' else 'evidence collection'}.",
            })

    elif node == "node_2":
        evidence = update.get("evidence", [])
        gaps = update.get("knowledge_gaps", [])
        if evidence:
            titles = [p.get("title", "?")[:60] for p in evidence[:5]]
            session.events.append({
                "type": "node_reasoning",
                "node": node,
                "reasoning": f"Found {len(evidence)} papers. Top results: {'; '.join(titles)}",
            })
        if gaps:
            session.events.append({
                "type": "node_reasoning",
                "node": node,
                "reasoning": f"Knowledge gaps identified: {'; '.join(gaps[:3])}",
            })

    elif node == "node_3":
        contract = update.get("research_contract", {})
        if contract:
            hyps = contract.get("hypotheses", {})
            hyp_strs = [str(v)[:80] for v in (hyps.values() if isinstance(hyps, dict) else hyps)]
            session.events.append({
                "type": "node_reasoning",
                "node": node,
                "reasoning": f"Contract generated with {len(hyp_strs)} hypotheses: {'; '.join(hyp_strs[:3])}",
            })

    elif node == "node_5":
        logs = update.get("execution_logs", [])
        if logs:
            for log in logs:
                session.events.append({
                    "type": "node_reasoning",
                    "node": node,
                    "reasoning": (
                        f"Experiment {log.get('experiment_id', '?')}: "
                        f"method={log.get('quantization', '?')}, "
                        f"latency={log.get('latency_ms', '?')}ms, "
                        f"status={log.get('status', '?')}"
                    ),
                })

    elif node == "node_6":
        verdict = update.get("verdict", "")
        confidence = update.get("confidence", 0)
        issues = update.get("identified_issues", [])
        if verdict:
            session.events.append({
                "type": "node_reasoning",
                "node": node,
                "reasoning": f"Scientific verdict: {verdict.upper()} at {confidence:.0%} confidence. Issues: {'; '.join(issues) if issues else 'None'}",
            })

    elif node == "node_8":
        md = update.get("report_markdown", "")
        if md:
            session.events.append({
                "type": "node_reasoning",
                "node": node,
                "reasoning": f"Final report generated ({len(md)} characters). Research pipeline complete.",
            })


def _build_hitl_payload(node: str, values: Dict) -> Dict:
    """Build a context-rich payload for the HITL modal."""
    if "node_0" in node:
        clarification_needed = values.get("clarification_needed", False)
        clarification_qs = values.get("clarification_questions", [])

        if clarification_needed and clarification_qs:
            return {
                "type": "clarification",
                "normalized_question": values.get("normalized_question", ""),
                "research_intent": values.get("research_intent", ""),
                "intent_confidence": values.get("intent_confidence", 0),
                "variables": values.get("variables", {}),
                "reasoning": values.get("reasoning", ""),
                "clarification_questions": clarification_qs,
                "message": "Your query needs more detail to produce useful research.",
            }
        return {
            "type": "confirmation",
            "normalized_question": values.get("normalized_question", ""),
            "research_intent": values.get("research_intent", ""),
            "intent_confidence": values.get("intent_confidence", 0),
            "variables": values.get("variables", {}),
            "reasoning": values.get("reasoning", ""),
        }
    if "node_4" in node:
        contract = values.get("research_contract", {})
        return {
            "type": "approval",
            "contract_summary": contract.get("problem_statement", ""),
            "tasks_count": len(contract.get("tasks", [])),
            "cost_estimate": contract.get("cost_estimate", {}),
        }
    if "node_7" in node:
        return {
            "type": "loop_decision",
            "verdict": values.get("verdict", ""),
            "confidence": values.get("confidence", 0),
            "iteration": values.get("iteration_count", 0),
        }
    return {"type": "unknown"}
