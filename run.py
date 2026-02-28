import sys
import json
import os
from src.are.graph import create_are_graph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

def run_demo(question: str):
    """
    Single-command entrypoint for the ARE hackathon demo.
    """
    print(f"\n{'='*60}")
    print(f"ARE: Autonomous Research Engineer")
    print(f"{'='*60}\n")
    print(f"[*] Target Question: {question}")
    print(f"[*] Mode: dry_run (Local Safety First)")
    
    # Initialize checkpointer for HITL interrupts
    checkpointer = MemorySaver()
    
    # Initialize minimal GraphState
    initial_state = {
        "research_question": question,
        "execution_mode": "dry_run",
        "random_seed": 42,
        "constraints": {"max_vram_gb": 8},
        "errors": [],
        "iteration_count": 0,
        "human_decisions": []
    }
    
    # Build Graph with checkpointer
    graph = create_are_graph(checkpointer=checkpointer)
    
    print("\n[ARE] Starting Orchestration Layer...")
    
    config = {"configurable": {"thread_id": "demo_thread"}}
    
    try:
        # First run with initial state
        for event in graph.stream(initial_state, config, stream_mode="updates"):
            pass
        
        # Check for interrupts and resume as needed
        max_resumes = 10  # Safety limit to prevent infinite loops
        resume_count = 0
        
        while resume_count < max_resumes:
            state_snapshot = graph.get_state(config)
            
            # If no next nodes, we're done
            if not state_snapshot.next:
                break
                
            next_node = state_snapshot.next[0]
            resume_count += 1
            print(f"[ARE] INTERRUPT at {next_node} - Simulating human approval... (resume {resume_count}/{max_resumes})")
            
            # Prepare simulated human decision based on which node we're at
            if "node_7" in next_node:
                # HITL-2: Loop decision
                iters = state_snapshot.values.get("iteration_count", 0)
                if "LIMIT" in question and iters < 1:
                    print("[ARE] Simulating CONTINUE to test guard...")
                    decision = {"action": "continue", "loop_decision": "continue"}
                else:
                    decision = {"action": "stop", "loop_decision": "terminate"}
            else:
                # HITL-1: Contract approval at NODE-4
                decision = {"action": "approve", "approval_status": "approved"}
            
            # Resume graph with the interrupt value using Command
            # Pass None as input and use Command.resume() to inject the value
            for event in graph.stream(Command(resume=decision), config, stream_mode="updates"):
                pass
                
        if resume_count >= max_resumes:
            print(f"[!] WARNING: Reached max resumes ({max_resumes}). Possible routing issue.")
                
        # Retrieve final state
        final_state = graph.get_state(config).values
        
        # Save artifacts
        report_md = final_state.get("report_markdown", "# Failure to generate report")
        report_json = final_state.get("report_json", {})
        
        with open("final_report.md", "w", encoding="utf-8") as f:
            f.write(report_md)
            
        with open("final_report.json", "w", encoding="utf-8") as f:
            json.dump(report_json, f, indent=2)
            
        print(f"\n{'='*60}")
        print(f"ARE RESEARCH COMPLETE")
        print(f"{'='*60}")
        print(f"[*] Verdict: {final_state.get('verdict', 'N/A')}")
        print(f"[*] Confidence: {final_state.get('confidence', 'N/A')}")
        print(f"[*] Artifact Location: {os.path.abspath('final_report.md')}")
        print(f"[*] Data Location: {os.path.abspath('final_report.json')}")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\n[!] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run.py \"Your research question here\"")
        sys.exit(1)
    
    research_query = sys.argv[1]
    run_demo(research_query)

