from typing import List, Literal, Dict
from pydantic import BaseModel, Field

class HypothesisAlignment(BaseModel):
    hypothesis_id: str
    alignment: Literal["supports", "weakens", "contradicts", "inconclusive"]
    observed_metric_delta: str

class StatisticalAnalysis(BaseModel):
    statistical_issues: List[str]
    confidence_penalty: float = Field(ge=0, le=1)

class NextAction(BaseModel):
    action: str
    reason: str
    cost_estimate: Literal["low", "medium", "high"]

class ScientificVerdict(BaseModel):
    verdict: Literal["conclusive", "inconclusive", "contradictory"]
    confidence: float = Field(ge=0, le=1)
    hypothesis_evaluation: Dict[str, str]
    identified_issues: List[str]
    next_actions: List[NextAction]
