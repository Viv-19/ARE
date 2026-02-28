from typing import List, Literal, Dict, Any
from pydantic import BaseModel, Field

class SelfKnowledgeEstimation(BaseModel):
    self_assessed_familiarity: float = Field(ge=0, le=1)
    known_concepts: List[str]
    uncertain_concepts: List[str]

class CitationMetadata(BaseModel):
    title: str
    year: int
    citation_count: int
    venue: str
    high_level_relevance: str

class CitationEvaluation(BaseModel):
    total_papers_found: int
    papers_above_threshold: int
    directly_relevant_papers: int

class KnowledgeAssessmentOutput(BaseModel):
    knowledge_confidence: Literal["low", "medium", "high"]
    research_status: Literal["novel", "partial", "well-studied"]
    evidence_required: bool
    citation_summary: Dict[str, Any]
    reasoning_summary: str
