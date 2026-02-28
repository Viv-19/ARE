from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

class QuestionNormalization(BaseModel):
    normalized_question: str = Field(description="The formalized, research-grade version of the input question.")

class IntentClassification(BaseModel):
    research_intent: Literal["exploratory", "replication", "optimization", "comparison"]
    intent_confidence: float = Field(ge=0, le=1)

class VariableExtraction(BaseModel):
    independent_vars: List[str]
    dependent_vars: List[str]
    control_vars: List[str]

class SafetyValidation(BaseModel):
    researchable: bool
    risk_flags: List[str]
    requires_external_data: bool

class ClarificationOutput(BaseModel):
    clarification_required: bool
    clarification_prompt: List[str]

class AutonomyInference(BaseModel):
    autonomy_level: Literal["survey_only", "experiment_limited", "experiment_iterative"]
    evidence_threshold: Literal["literature_only", "literature_plus_experiments"]

class Node0Reasoning(BaseModel):
    """Captures the internal chain-of-thought from Gemini."""
    thought_trace: str = Field(description="Step-by-step reasoning for the decision.")
    domain_check: str = Field(description="Explicit check against the LLM Quantization whitelist.")

class RouterContract(BaseModel):
    original_question: str
    normalized_question: str
    research_intent: Literal["exploratory", "replication", "optimization", "comparison"]
    intent_confidence: float = Field(ge=0, le=1)
    autonomy_level: Literal["survey_only", "experiment_limited", "experiment_iterative"]
    evidence_threshold: Literal["literature_only", "literature_plus_experiments"]
    variables: Dict[str, List[str]]
    constraints: Dict[str, Any]
    researchable: bool
    clarification_required: bool
    reasoning: Optional[str] = Field(description="Agent's internal reasoning summary")
    confirmation_required: bool = Field(default=True, description="Always true for production safety")
