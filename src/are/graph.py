from langgraph.graph import StateGraph, END

# --- State & Node Imports ---
from .state import GraphState

from .nodes.node_0_intake import node_0_research_question_intake
from .nodes.node_0_confirm import node_0_confirm_intake
from .nodes.node_1_router import node_1_knowledge_assessment_router
from .nodes.node_2_evidence import node_2_evidence_collection
from .nodes.node_3_contract import node_3_research_contract_orchestration
from .nodes.node_4_hitl_1 import node_4_human_approval_hitl_1
from .nodes.node_5_worker import node_5_worker_execution_controller
from .nodes.node_6_critic import node_6_critic_scientific_review
from .nodes.node_7_hitl_2 import node_7_human_critic_loop_hitl_2
from .nodes.node_8_report import node_8_reducer_report_generator

# ====================================================
# CONDITIONAL ROUTERS (Pure Orchestration Logic)
# ====================================================

def confidence_gate(state: GraphState) -> str:
    """
    Evaluates confidence and confirmation requirements.
    """
    from .config import ENABLE_NODE_0_CONFIRM
    
    confidence = state.get("intent_confidence", 1.0)
    
    # Low confidence -> Route to confirmation with clarification flag
    if confidence < 0.7:
        print("[ARE] Low confidence detected. Routing to confirmation for clarification.")
        # Ensure we signal that clarification is needed
        state["clarification_needed"] = True
        return "confirm"
    
    # Skip confirmation if disabled via config
    if not ENABLE_NODE_0_CONFIRM:
        print("[ARE] Node-0 confirmation disabled. Proceeding directly to router.")
        return "proceed"
    
    # Standard flow — always confirm in V4
    return "confirm"

def research_router(state: GraphState) -> str:
    """
    Decides between literature review and experimental execution.
    """
    status = state.get("research_status", "novel")
    if status == "well-studied":
        return "summarize"
    return "research"

def verdict_router(state: GraphState) -> str:
    """
    Validates scientific conclusion vs the necessity of further iteration.
    """
    verdict = state.get("verdict")
    if verdict == "conclusive":
        return "report"
    return "critic"

def next_iteration_router(state: GraphState) -> str:
    """
    Coordinates the loop termination after HITL-2 review.
    """
    decision = state.get("loop_decision", "terminate")
    if decision == "continue":
        return "loop"
    return "finish"

# ====================================================
# GRAPH DEFINITION
# ====================================================

def create_are_graph(checkpointer=None):
    """
    Initializes the ARE LangGraph workflow.
    """
    workflow = StateGraph(GraphState)

    # 1. Register Nodes
    workflow.add_node("node_0", node_0_research_question_intake)
    workflow.add_node("node_0_confirmation", node_0_confirm_intake) # NEW
    workflow.add_node("node_1", node_1_knowledge_assessment_router)
    workflow.add_node("node_2", node_2_evidence_collection)
    workflow.add_node("node_3", node_3_research_contract_orchestration)
    workflow.add_node("node_4", node_4_human_approval_hitl_1)
    workflow.add_node("node_5", node_5_worker_execution_controller)
    workflow.add_node("node_6", node_6_critic_scientific_review)
    workflow.add_node("node_7", node_7_human_critic_loop_hitl_2)
    workflow.add_node("node_8", node_8_reducer_report_generator)

    # 2. Define Orchestration & Transitions
    
    # 2.1 INTAKE -> CONFIRMATION/ROUTER
    workflow.add_conditional_edges(
        "node_0",
        confidence_gate,
        {
            "halt": END, 
            "confirm": "node_0_confirmation", 
            "proceed": "node_1"
        }
    )
    
    # 2.1.1 CONFIRMATION -> ROUTER (Managed by Command, but need edge definition?)
    # Since node_0_confirmation returns Command(goto="node_1"), explicit edge might not be needed strictu sensu
    # but defining it clarifies the graph structure for visualization.
    workflow.add_edge("node_0_confirmation", "node_1") 

    # 2.2 ROUTER -> EVIDENCE vs REPORT (Efficiency Check)
    workflow.add_conditional_edges(
        "node_1",
        research_router,
        {"summarize": "node_8", "research": "node_2"}
    )

    # 2.3 GROUNDING Flow
    workflow.add_edge("node_2", "node_3")
    workflow.add_edge("node_3", "node_4")

    # 2.4 HITL-1 (Governance Check)
    workflow.add_conditional_edges(
        "node_4",
        lambda s: "node_5" if (s.get("human_decisions") and (s["human_decisions"][-1].get("approval_status") == "approved" or s["human_decisions"][-1].get("action") == "approve")) else "node_3",
        {"node_5": "node_5", "node_3": "node_3"}
    )

    # 2.5 EXECUTION Flow
    workflow.add_edge("node_5", "node_6")

    # 2.6 CRITIC -> REPORT vs HITL-2 (Verdict Check)
    workflow.add_conditional_edges(
        "node_6",
        verdict_router,
        {"report": "node_8", "critic": "node_7"}
    )

    # 2.7 HITL-2 -> LOOP vs REPORT (Termination Check)
    workflow.add_conditional_edges(
        "node_7",
        next_iteration_router,
        {"loop": "node_5", "finish": "node_8"}
    )

    # 2.8 EXIT
    workflow.add_edge("node_8", END)

    # 3. Compile Graph
    workflow.set_entry_point("node_0")
    return workflow.compile(checkpointer=checkpointer)
