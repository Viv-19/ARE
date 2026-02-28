from typing import TypedDict, List, Dict, Any, Optional

class GraphState(TypedDict, total=False):
    """
    Refined GraphState for the Autonomous Research Engineer (ARE).
    Uses total=False to allow for incremental updates by independent nodes.
    
    LIFECYCLE GROUPS:
    1. INTAKE (Node 0)
    2. ROUTER (Node 1)
    3. EVIDENCE (Node 2)
    4. CONTRACT (Node 3 & 4)
    5. EXECUTION (Node 5)
    6. REVIEW (Node 6)
    7. LOOP (Node 7)
    8. REPORTING (Node 8)
    9. SYSTEM (Cross-cutting)
    """

    # --- 1. INTAKE (Owned by Node 0) ---
    research_question: str  # Original user input [READ-ONLY after Node 0]
    normalized_question: str # Formatted research question
    research_intent: str # exploratory | replication | optimization | comparison
    intent_confidence: float # 0.0 to 1.0 confidence score
    clarification_required: bool # True if we need to halt for user input
    clarification_prompt: List[str] # Questions for the user if confidence is low
    variables: Dict[str, List[str]] # independent, dependent, control vars
    autonomy_level: str # survey_only | experiment_limited | experiment_iterative
    evidence_threshold: str # literature_only | literature_plus_experiments
    researchable: bool # Safety/Scope validation result

    # --- 2. ROUTER (Owned by Node 1) ---
    research_status: str # well-studied | partial | novel
    evidence_required: bool # True if we need to search for more papers
    knowledge_confidence: str # low | medium | high
    citation_summary: Dict[str, Any] # Aggregate citation stats
    reasoning_summary: str # Narrative explanation of the routing decision

    # --- 3. EVIDENCE (Owned by Node 2) ---
    search_queries: List[str] # Generated search terms
    evidence: List[Dict[str, Any]] # List of paper metadata
    knowledge_gaps: List[str] # Identified missing information
    evidence_sufficiency: bool # True if we have enough grounding to proceed

    # --- 4. CONTRACT (Owned by Node 3 & 4) ---
    research_contract: Dict[str, Any] # Formalized research plan/logic [READ-ONLY after Node 4]
    human_decisions: List[Dict[str, Any]] # Audit trail of HITL feedback (Nodes 4 & 7)

    # --- 5. EXECUTION (Owned by Node 5) ---
    execution_status: str # completed | partial | aborted
    execution_logs: List[Dict[str, Any]] # Raw resource/run logs
    artifacts: List[Dict[str, Any]] # Paths/checksums of generated data

    # --- 6. REVIEW (Owned by Node 6) ---
    verdict: str # conclusive | inconclusive | contradictory
    confidence: float # Scientific confidence in the findings
    hypothesis_evaluation: Dict[str, str] # Map of hypothesis ID to alignment status
    proposed_next_actions: List[Dict[str, Any]] # Structural recommendations for Node 7

    # --- 7. LOOP (Owned by Node 7 & Graph) ---
    loop_decision: str # continue | terminate [READ-ONLY after Graph router]
    iteration_count: int # PROTECTED: Incremented by graph logic or Node 7
    remaining_budget: Dict[str, Any] # Remaining GPU/Time units

    # --- 8. REPORTING (Owned by Node 8) ---
    report_markdown: str # Final human-readable report
    report_json: Dict[str, Any] # Machine-readable findings

    # --- 9. SYSTEM (Cross-cutting) ---
    execution_mode: str # dry_run | local_cpu | gpu [MANDATORY]
    random_seed: int # Global seed for reproducibility [MANDATORY]
    constraints: Dict[str, Any] # Initial user constraints [READ-ONLY]
    reasoning: str # Generic field for agent thought trace / internal logic
    errors: List[str] # Global error collection list
