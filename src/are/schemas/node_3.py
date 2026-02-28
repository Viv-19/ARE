from typing import List, Optional, Literal, Dict
from pydantic import BaseModel

class Hypothesis(BaseModel):
    statement: str
    derived_from: str # Knowledge gap ref

class MetricDefinition(BaseModel):
    computed_as: str

class ResearchTask(BaseModel):
    id: str
    description: str
    type: Literal["setup", "execution", "analysis", "reporting"]
    depends_on: List[str] = []

class ContractConstraints(BaseModel):
    max_experiments: int
    max_gpu_hours: float
    max_memory_gb: int

class CostEstimate(BaseModel):
    expected_gpu_hours: float
    expected_memory_gb: float
    risk_level: Literal["low", "medium", "high"]

class ResearchContract(BaseModel):
    problem_statement: str
    hypotheses: Dict[str, Hypothesis]
    variables: Dict[str, List[str]]
    metrics: Dict[str, MetricDefinition]
    tasks: List[ResearchTask]
    constraints: ContractConstraints
    failure_criteria: List[str]
    cost_estimate: CostEstimate
    requires_human_approval: bool = True
