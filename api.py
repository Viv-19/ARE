"""
ARE FastAPI Backend
Provides REST API and SSE endpoints for the frontend.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.are.graph import create_are_graph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command


# ============================================================
# App Initialization
# ============================================================

from contextlib import asynccontextmanager
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="ARE - Autonomous Research Engine", lifespan=lifespan)

# ============================================================
# Session Management
# ============================================================

class Session:
    def __init__(self, session_id: str, question: str):
        self.id = session_id
        self.question = question
        self.status = "pending"
        self.current_node = None
        self.nodes_completed = []
        self.hitl_pending = False
        self.hitl_node = None
        self.hitl_payload = None
        self.hitl_decision = None  # Store decision here
        self.report_md = None
        self.report_json = None
        self.verdict = None
        self.confidence = None
        self.reasoning = None # Store latest reasoning
        self.error = None
        self.events = []  # SSE event queue
        # New fields for NODE-5 code generation workflow
        self.experiment_code = None
        self.experiment_instructions = None
        self.experiment_results = None


sessions: Dict[str, Session] = {}


# ============================================================
# Pydantic Models
# ============================================================

class ResearchRequest(BaseModel):
    question: str


class ApprovalRequest(BaseModel):
    action: str  # "approve", "reject", "refine"
    feedback: Optional[str] = None


# ============================================================
# ARE Graph Runner
# ============================================================

async def run_are_graph(session: Session):
    """Run the ARE graph asynchronously with event streaming."""
    try:
        checkpointer = MemorySaver()
        graph = create_are_graph(checkpointer=checkpointer)
        
        initial_state = {
            "research_question": session.question,
            "execution_mode": "dry_run",
            "random_seed": 42,
            "constraints": {"max_vram_gb": 8},
            "errors": [],
            "iteration_count": 0,
            "human_decisions": []
        }
        
        config = {"configurable": {"thread_id": session.id}}
        session.status = "running"
        
        # Push start events
        session.events.append({
            "type": "start",
            "message": "Research initiated"
        })
        session.events.append({
            "type": "node_reasoning",
            "node": "system",
            "reasoning": "🚀 Initializing Autonomous Research Engine..."
        })
        session.events.append({
            "type": "node_reasoning",
            "node": "node_0",
            "reasoning": "🧠 Analyzing research question and identifying core intent..."
        })
        
        # First run
        print(f"[API] Starting graph stream for session: {session.id}")
        for event in graph.stream(initial_state, config, stream_mode="updates"):
            for node_name, node_state in event.items():
                print(f"[API] Node completed: {node_name}")
                session.current_node = node_name
                session.nodes_completed.append(node_name)
                
                # Check for reasoning
                if "reasoning" in node_state:
                    session.reasoning = node_state["reasoning"]
                    session.events.append({
                        "type": "node_reasoning",
                        "node": node_name,
                        "reasoning": node_state["reasoning"]
                    })
                
                session.events.append({
                    "type": "node_complete",
                    "node": node_name,
                    "payload": node_state
                })
        
        # Handle interrupts
        max_resumes = 10
        resume_count = 0
        
        while resume_count < max_resumes:
            state_snapshot = graph.get_state(config)
            
            if not state_snapshot.next:
                break
            
            next_node = state_snapshot.next[0]
            resume_count += 1
            
            # Signal HITL required
            print(f"[API] HITL Required at node: {next_node}")
            session.hitl_pending = True
            session.hitl_node = next_node
            session.current_node = next_node
            
            # Prepare Payload based on context
            state_values = state_snapshot.values
            if "node_0" in (state_values.get("nodes_completed", []) or session.nodes_completed):
                 # Node-0 Confirmation Payload
                 session.hitl_payload = {
                     "type": "confirmation",
                     "normalized_question": state_values.get("normalized_question"),
                     "research_intent": state_values.get("research_intent"),
                     "variables": state_values.get("variables"),
                     "reasoning": state_values.get("reasoning")
                 }
            else:
                 # Default HITL (Contract or Review)
                 contract = state_values.get("research_contract", {})
                 session.hitl_payload = {
                     "type": "approval",
                     "node": next_node,
                     "contract_summary": contract.get("problem_statement", "Review required"),
                     "cost_estimate": contract.get("cost_estimate", {}),
                     "tasks_count": len(contract.get("tasks", []))
                 }
            
            session.events.append({
                "type": "hitl_required",
                "node": next_node,
                "payload": session.hitl_payload
            })
            
            # Wait for approval (poll every 500ms)
            print(f"[API] Waiting for HITL decision on {session.id}...")
            while session.hitl_pending:
                await asyncio.sleep(0.5)
            print(f"[API] HITL Decision received: {session.hitl_decision}")
            
            # Get the decision that was set
            decision = session.hitl_decision
            
            # Resume graph
            session.events.append({
                "type": "hitl_resolved",
                "node": next_node,
                "decision": decision.get("action", "approve")
            })
            
            for event in graph.stream(Command(resume=decision), config, stream_mode="updates"):
                for node_name, node_state in event.items():
                    session.current_node = node_name
                    session.nodes_completed.append(node_name)
                    
                    # Check for reasoning
                    if "reasoning" in node_state:
                         session.events.append({
                             "type": "node_reasoning",
                             "node": node_name,
                             "reasoning": node_state["reasoning"]
                         })

                    session.events.append({
                        "type": "node_complete",
                        "node": node_name,
                        "payload": node_state
                    })
        
        # Get final state
        final_state = graph.get_state(config).values
        
        session.report_md = final_state.get("report_markdown", "")
        session.report_json = final_state.get("report_json", {})
        session.verdict = final_state.get("verdict", "unknown")
        session.confidence = final_state.get("confidence", 0)
        session.status = "completed"
        
        session.events.append({
            "type": "complete",
            "verdict": session.verdict,
            "confidence": session.confidence
        })
        
    except Exception as e:
        session.status = "error"
        session.error = str(e)
        session.events.append({
            "type": "error",
            "message": str(e)
        })


# ============================================================
# FastAPI App
# ============================================================

@app.on_event("startup")
async def startup_event():
    """Verify system health on startup."""
    print(f"\n{'*'*60}")
    print("AROS SERVER STARTING...")
    print(f"{'*'*60}")
    
    # 1. Check Gemini Connectivity
    from src.are.config import USE_GEMINI, GEMINI_MODEL
    from src.are.utils.gemini import call_gemini
    
    if USE_GEMINI:
        print(f"[HEALTH] Testing Gemini ({GEMINI_MODEL})...")
        test_res = call_gemini("Say 'AROS ONLINE'", expect_json=False)
        if test_res:
            print(f"[HEALTH] ✓ Gemini Connected: {test_res.get('content', '')}")
        else:
            print("[HEALTH] ✗ Gemini Connection FAILED. Falling back to deterministic mode.")
    else:
        print("[HEALTH] ! Gemini Disabled via config.")
    
    print(f"{'*'*60}\n")

# app = FastAPI reference was here, removed as it is now at the top

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the frontend."""
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.post("/api/research")
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    """Start a new research session."""
    session_id = str(uuid.uuid4())[:8]
    session = Session(session_id, request.question)
    sessions[session_id] = session
    
    # Run graph in background
    background_tasks.add_task(run_are_graph, session)
    
    return {"session_id": session_id, "status": "started"}


@app.get("/api/status/{session_id}")
async def get_status(session_id: str):
    """Get current session status."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    return {
        "status": session.status,
        "current_node": session.current_node,
        "nodes_completed": session.nodes_completed,
        "hitl_pending": session.hitl_pending,
        "hitl_node": session.hitl_node,
        "hitl_payload": session.hitl_payload,
        "verdict": session.verdict,
        "confidence": session.confidence,
        "error": session.error
    }


@app.get("/api/events/{session_id}")
async def stream_events(session_id: str):
    """SSE endpoint for real-time updates."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    async def event_generator():
        last_index = 0
        while True:
            # Send any new events
            while last_index < len(session.events):
                event = session.events[last_index]
                yield f"data: {json.dumps(event)}\n\n"
                last_index += 1
            
            # Check if done
            if session.status in ["completed", "error"]:
                break
            
            await asyncio.sleep(0.3)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/api/approve/{session_id}")
async def approve_hitl(session_id: str, request: ApprovalRequest):
    """Submit HITL approval decision."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    if not session.hitl_pending:
        raise HTTPException(status_code=400, detail="No HITL approval pending")
    
    # Set the decision
    if "node_7" in (session.hitl_node or ""):
        session.hitl_decision = {
            "action": request.action,
            "loop_decision": "continue" if request.action == "approve" else "terminate"
        }
    else:
        session.hitl_decision = {
            "action": request.action,
            "approval_status": "approved" if request.action == "approve" else "rejected"
        }
    
    session.hitl_pending = False
    
    return {"status": "decision_recorded", "action": request.action}


@app.get("/api/report/{session_id}")
async def get_report(session_id: str):
    """Get the final research report."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    if session.status != "completed":
        raise HTTPException(status_code=400, detail="Research not yet completed")
    
    return {
        "markdown": session.report_md,
        "json": session.report_json,
        "verdict": session.verdict,
        "confidence": session.confidence
    }


class ExperimentResultsRequest(BaseModel):
    """Request model for experiment result submission."""
    results: Dict[str, Any]
    notes: Optional[str] = None


@app.get("/api/experiment-code/{session_id}")
async def get_experiment_code(session_id: str):
    """Get the generated experiment code for a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    if not session.experiment_code:
        raise HTTPException(status_code=400, detail="Experiment code not yet generated")
    
    return {
        "code": session.experiment_code,
        "instructions": session.experiment_instructions,
        "status": session.status
    }


@app.post("/api/submit-results/{session_id}")
async def submit_experiment_results(session_id: str, request: ExperimentResultsRequest):
    """Submit experiment results from user execution."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    # Store results
    session.experiment_results = request.results
    
    # Update execution logs with submitted results
    session.events.append({
        "type": "node_reasoning",
        "node": "node_5",
        "reasoning": "📊 Experiment results received. Processing for analysis..."
    })
    
    session.events.append({
        "type": "results_submitted",
        "message": "Experiment results submitted successfully",
        "notes": request.notes
    })
    
    return {
        "status": "results_received",
        "message": "Experiment results submitted. Proceeding to critic analysis (NODE-6)."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
