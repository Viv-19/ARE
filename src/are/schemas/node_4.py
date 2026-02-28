from typing import List, Optional, Literal
from pydantic import BaseModel

class HumanSuggestion(BaseModel):
    target: str # e.g., "hypotheses.H1"
    proposed_change: str
    rationale: str

class HumanFeedback(BaseModel):
    action: Literal["approve", "reject", "modify"]
    suggestions: Optional[List[HumanSuggestion]] = None

class SuggestionEvaluation(BaseModel):
    target: str
    decision: Literal["accept", "partially_accept", "reject"]
    justification: str

class ApprovalDecision(BaseModel):
    approval_status: Literal["approved", "rejected"]
    final_contract_version: str
    evaluations: List[SuggestionEvaluation]
    timestamp: str
