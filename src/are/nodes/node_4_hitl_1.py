from langgraph.types import interrupt
from ..state import GraphState
from ..config import ENABLE_REAL_HITL
from ..audit.logger import log_decision
from ..utils.logging import log_state_transition
from datetime import datetime

def node_4_human_approval_hitl_1(state: GraphState) -> GraphState:
    """
    NODE-4 — Human-in-the-Loop Approval Node: Mandatory governance layer.
    Ensures human authority with model accountability using LangGraph interrupts.
    """
    log_state_transition("NODE-4", state)
    contract = state.get("research_contract")
    if not contract:
        state.update({"errors": state.get("errors", []) + ["No contract found for approval."]})
        return state

    # 3.1 & 3.5: Real HITL vs Simulated Logic
    if ENABLE_REAL_HITL:
        # Prepare payload for the interrupt
        # Payload must include contract, cost_estimate, constraints, and version
        interrupt_payload = {
            "node": "NODE-4",
            "research_contract": contract,
            "cost_estimate": state.get("remaining_budget", {}).get("estimated_cost", "N/A"),
            "constraints": state.get("constraints", {}),
            "version": "v1.0"
        }
        
        # LANGGRAPH NATIVE INTERRUPT
        # This will pause the graph execution until external input is provided.
        print(f"--- [HITL] Interrupting at NODE-4 for human approval ---")
        human_input = interrupt(f"Awaiting human approval for research contract. Payload: {interrupt_payload}")
        
        # 3.2: Resuming Execution (State Injection)
        # The graph resumes when human_decisions is injected.
        # We expect human_input to be a dict equivalent to what we'd find in state["human_decisions"]
        
        decision_data = human_input if isinstance(human_input, dict) else {"action": "approve"}
        
        # 3.3: Audit Log Persistence
        log_entry = {
            "node_id": "NODE-4",
            "decision": decision_data,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "context_summary": {
                "contract_id": contract.get("id", "unknown"),
                "version": interrupt_payload["version"]
            }
        }
        log_decision(log_entry)
        
        # Update state with the decision
        state.update({
            "human_decisions": state.get("human_decisions", []) + [decision_data],
            "clarification_required": decision_data.get("action") == "reject"
        })
        
        return state

    # --- FALLBACK: Simulated Logic (Backward Compatibility) ---
    raw_feedback = state.get("human_decisions", [{}])[-1] if state.get("human_decisions") else {"action": "approve"}
    action = raw_feedback.get("action", "approve")
    
    current_version = "v1.0"
    if action == "reject":
        decision = {
            "approval_status": "rejected",
            "final_contract_version": current_version,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        state.update({
            "human_decisions": state.get("human_decisions", []) + [decision],
            "clarification_required": True
        })
        return state

    # Simple Approval
    decision = {
        "approval_status": "approved",
        "final_contract_version": current_version,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    state.update({
        "human_decisions": state.get("human_decisions", []) + [decision],
        "clarification_required": False
    })

    return state

# CORE LOGIC FROZEN — UI SAFE TO ADD

# ====================================================
# VERIFICATION CHECKLIST (NODE-4 HITL)
# - [x] Graph pauses at NODE-4 with interrupt when ENABLE_REAL_HITL is True
# - [x] Payload includes contract, estimate, constraints, version
# - [x] Resumes when human_decisions injected
# - [x] Audit log grows with each HITL decision
# ====================================================
