from langgraph.types import interrupt, Command
from ..state import GraphState
from ..utils.logging import log_state_transition

def node_0_confirm_intake(state: GraphState) -> Command:
    """
    NODE-0-CONFIRM: Human-in-the-loop confirmation of the research plan.
    Pauses execution to allow user to review the normalized question and intent.
    """
    log_state_transition("NODE-0-CONFIRM", state)
    
    # Interrupt execution and wait for human input via Command(resume=...)
    # Pass full context for AROS UI display
    decision = interrupt({
        "type": "confirmation",
        "normalized_question": state.get("normalized_question"),
        "research_intent": state.get("research_intent"),
        "intent_confidence": state.get("intent_confidence"),
        "autonomy_level": state.get("autonomy_level"),
        "evidence_threshold": state.get("evidence_threshold"),
        "variables": state.get("variables", {}),
        "reasoning": state.get("reasoning", "Analysis complete.")
    })
    
    # Decision comes from api.py:approve_hitl -> run_are_graph -> Command(resume=decision)
    action = decision.get("action", "approve")
    feedback = decision.get("feedback", "")
    
    if action == "approve":
        print("[ARE] Plan Confirmed. Proceeding.")
        # Proceed to NODE-1
        return Command(goto="node_1")
    
    elif action == "refine":
        print(f"[ARE] Plan Refinement Requested. Feedback: {feedback}")
        # Append feedback to the request to guide the retry
        original_q = state.get("original_question") or state.get("research_question", "")
        
        # Construct refined prompt
        refined_q = f"ORIGINAL: {original_q}\nUSER FEEDBACK: {feedback}\nPlease refine the research plan based on this feedback."
        
        return Command(
            update={"research_question": refined_q},
            goto="node_0"
        )
    
    # Default fallback
    return Command(goto="node_0")
