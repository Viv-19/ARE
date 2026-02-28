from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel

class HumanCriticFeedback(BaseModel):
    action: Literal["approve", "modify", "stop"]
    approved_actions: Optional[List[str]] = None
    constraints_override: Optional[Dict[str, Any]] = None
    comment: str

class LoopDecision(BaseModel):
    loop_decision: Literal["continue", "terminate"]
    reason: str
    updated_constraints: Optional[Dict[str, Any]] = None
    justification: str
