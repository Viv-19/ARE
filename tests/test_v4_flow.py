import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from are.state import GraphState
from are.nodes.node_1_router import node_1_knowledge_assessment_router
from are.nodes.node_3_contract import node_3_research_contract_orchestration
from are.nodes.node_5_worker import node_5_worker_execution_controller
from are.nodes.node_8_report import node_8_reducer_report_generator

# Mock Gemini Response for Node 3
MOCK_CONTRACT = {
    "problem_statement": "Test problem",
    "hypotheses": {"H1": {"statement": "Test hypothesis"}},
    "variables": {"independent": ["x"], "dependent": ["y"], "control": ["z"]},
    "metrics": {"mae": {"computed_at": "test"}},
    "tasks": [{"id": "T1", "description": "Test task"}],
    "constraints": {"max_experiments": 3},
    "failure_criteria": ["fail"],
    "cost_estimate": {"risk": "low"},
    "requires_human_approval": True
}

# Mock Gemini Response for Node 5
MOCK_CODE = {"code": "print('Hello World')"}

@patch('are.utils.gemini.call_gemini')
def test_node_1_deterministic_routing(mock_gemini):
    """Test Node 1 strictly respects citation thresholds (V4 Spec)."""
    # Case A: Well-Studied (Survey)
    # >3 papers with >100 citations + relevance
    mock_papers = [
        {"title": "Quantization of LLMs", "citation_count": 150, "abstract": "int4 quantization"},
        {"title": "Transformer Inference", "citation_count": 120, "abstract": "transformer inference"},
        {"title": "Efficient Inference", "citation_count": 200, "abstract": "efficient inference"}
    ]
    
    with patch('are.nodes.node_1_router.ss_search', return_value=(mock_papers, False)), \
         patch('are.nodes.node_1_router.arxiv_search', return_value=[]):
        
        # Test case for the bug: "rounding technique" query
        state = {
            "research_question": "effect of rounding technique used in layers of transformer. how does inference of llm gets effected when we change the rounding technique from IEEE format to truncation round to 0",
            "normalized_question": "quantization in transformers" 
        }
        new_state = node_1_knowledge_assessment_router(state)
        
        # Should route to NODE-8 (Survey)
        assert new_state["research_status"] == "well-studied"
        assert new_state["evidence_required"] == False

    # Case B: Novel (Experiments)
    # No papers >100 citations
    mock_papers_weak = [{"title": "New idea", "citation_count": 5}]
    
    with patch('are.nodes.node_1_router.ss_search', return_value=(mock_papers_weak, False)), \
         patch('are.nodes.node_1_router.arxiv_search', return_value=[]):
        
        state = {"normalized_question": "quantization", "research_question": "quantization"}
        new_state = node_1_knowledge_assessment_router(state)
        
        # Should route to NODE-2 (Evidence)
        assert new_state["research_status"] == "novel"
        assert new_state["evidence_required"] == True

@patch('are.utils.gemini.call_gemini')
def test_node_3_contract_structure(mock_gemini):
    """Test Node 3 produces compliant Contract JSON."""
    mock_gemini.return_value = MOCK_CONTRACT
    
    state = {
        "normalized_question": "test",
        "evidence_sufficiency": True,
        "knowledge_gaps": ["gap1"]
    }
    
    new_state = node_3_research_contract_orchestration(state)
    contract = new_state["research_contract"]
    
    assert "problem_statement" in contract
    assert "hypotheses" in contract
    assert "tasks" in contract
    assert contract["requires_human_approval"] is True

@patch('are.utils.gemini.call_gemini')
def test_node_5_code_generation(mock_gemini):
    """Test Node 5 generates code and waits for user."""
    mock_gemini.return_value = MOCK_CODE
    
    state = {
        "research_contract": MOCK_CONTRACT,
        "normalized_question": "test",
        "human_decisions": [{"approval_status": "approved", "action": "approve"}]
    }
    
    new_state = node_5_worker_execution_controller(state)
    
    assert new_state["execution_status"] == "awaiting_user_execution"
    assert "experiment_code" in new_state
    assert "experiment_instructions" in new_state

if __name__ == "__main__":
    # Manual run wrapper
    print("Running V4 Verification Tests...")
    try:
        test_node_1_deterministic_routing()
        print("✓ Node 1 Routing: PASSED")
        test_node_3_contract_structure()
        print("✓ Node 3 Contract: PASSED")
        test_node_5_code_generation()
        print("✓ Node 5 CodeGen: PASSED")
        print("ALL TESTS PASSED")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
