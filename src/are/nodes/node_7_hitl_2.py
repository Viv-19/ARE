from langgraph.types import interrupt
from ..state import GraphState
from ..config import ENABLE_REAL_HITL
from ..audit.logger import log_decision
from ..utils.logging import log_state_transition
from datetime import datetime

def node_7_human_critic_loop_hitl_2(state: GraphState) -> GraphState:
    """
    NODE-7 — Human–Critic Loop (Second HITL): Safety brake and iteration gate.
    Coordinates human oversight after scientific review using LangGraph interrupts.
    """
    log_state_transition("NODE-7", state)
    # 7.1 Trigger Conditions: Skip if conclusive
    verdict = state.get("verdict")
    if verdict == "conclusive":
        state.update({"loop_decision": "terminate", "iteration_count": state.get("iteration_count", 0)})
        return state

    # 7.2 Safety Guards (Max Experiments)
    max_iters = state.get("research_contract", {}).get("constraints", {}).get("max_experiments", 3)
    current_iters = state.get("iteration_count", 0)
    
    if current_iters >= max_iters:
        state.update({
            "loop_decision": "terminate",
            "errors": state.get("errors", []) + ["Max experiments reached. Forcing termination."]
        })
        return state

    # 3.1 & 3.5: Real HITL vs Simulated Logic
    if ENABLE_REAL_HITL:
        # Prepare payload for the interrupt
        # Payload: critic verdict, confidence, proposed next_actions, remaining budget, iteration_count
        interrupt_payload = {
            "node": "NODE-7",
            "verdict": verdict,
            "confidence": state.get("confidence", 0.0),
            "proposed_next_actions": state.get("proposed_next_actions", []),
            "remaining_budget": state.get("remaining_budget", {}),
            "iteration_count": current_iters
        }

        # LANGGRAPH NATIVE INTERRUPT
        print(f"--- [HITL] Interrupting at NODE-7 for continue/stop decision ---")
        human_input = interrupt(f"Awaiting human decision: continue or stop. Payload: {interrupt_payload}")
        
        # 3.2: Resumed Decision
        decision_data = human_input if isinstance(human_input, dict) else {"action": "approve"}
        
        # 3.3: Audit Log Persistence
        log_entry = {
            "node_id": "NODE-7",
            "decision": decision_data,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "context_summary": {
                "iteration": current_iters,
                "verdict": verdict
            }
        }
        log_decision(log_entry)
        
        action = decision_data.get("action", "approve")
        
        if action == "stop":
            state.update({"loop_decision": "terminate"})
            return state

        # 7.6 Exit Conditions (Resumed)
        if action in ["approve", "modify", "continue"]:
            state.update({
                "loop_decision": "continue",
                "iteration_count": current_iters + 1
            })
        else:
            state.update({"loop_decision": "terminate"})
        
        return state

    # --- FALLBACK: Simulated Logic ---
    human_feedback = state.get("human_decisions", [{}])[-1] if state.get("human_decisions") else {"action": "approve"}
    action = human_feedback.get("action", "approve")
    
    if action == "stop":
        state.update({"loop_decision": "terminate"})
        return state

    if action in ["approve", "modify"]:
        state.update({
            "loop_decision": "continue",
            "iteration_count": current_iters + 1
        })
    else:
        state.update({"loop_decision": "terminate"})

    return state

# CORE LOGIC FROZEN — UI SAFE TO ADD

# ====================================================
# VERIFICATION CHECKLIST (NODE-7 HITL)
# - [x] Graph pauses at NODE-7 with interrupt
# - [x] Payload includes verdict, confidence, actions, budget, iters
# - [x] Resumes when decision injected
# - [x] Audit log grows with each HITL decision
# ====================================================
