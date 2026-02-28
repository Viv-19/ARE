from typing import List, Optional
from pydantic import BaseModel, Field

class GeneratedQueries(BaseModel):
    generated_queries: List[str] = Field(min_items=5, max_items=10)

class PaperEvidence(BaseModel):
    title: str
    citations: int
    methods: str
    limitations: str
    doi: Optional[str] = None
    year: int
    venue: str
    source: str

class EvidenceCollectionOutput(BaseModel):
    search_queries: List[str]
    papers: List[PaperEvidence]
    knowledge_gaps: List[str]
    evidence_sufficiency: bool
