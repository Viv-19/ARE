import sys
import os
from unittest.mock import patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from are.state import GraphState
from are.nodes.node_0_intake import node_0_research_question_intake
from are.graph import confidence_gate

def test_rounding_query_confidence():
    """Verify that 'rounding' query gets enough keywords to pass or route to confirm."""
    state = {
        "research_question": "effect of rounding technique used in layers of transformer. how does inference of llm gets effected when we change the rounding technique from IEEE format to truncation round to 0"
    }
    
    # Run deterministic intake
    with patch('are.config.USE_GEMINI', False):
        new_state = node_0_research_question_intake(state)
        
    print(f"Confidence: {new_state.get('intent_confidence')}")
    print(f"Variables: {new_state.get('variables')}")
    
    # In my logic, 'rounding' and 'truncation' should add to independent.
    # 'stability' (from rounding context) or the general keywords should boost it.
    
    # Check graph routing
    route = confidence_gate(new_state)
    print(f"Route: {route}")
    
    # Assertions
    assert "Rounding technique" in new_state["variables"]["independent"]
    assert route == "confirm" # Should always be confirm in the new logic

if __name__ == "__main__":
    try:
        test_rounding_query_confidence()
        print("✓ Node 0 Routing Fix: PASSED")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
