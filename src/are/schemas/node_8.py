from typing import List, Any, Dict, Optional
from pydantic import BaseModel

class ReportTable(BaseModel):
    title: str
    columns: List[str]
    rows: List[List[Any]]

class ResearchReportJSON(BaseModel):
    abstract: str
    methodology: Dict[str, Any]
    results_table: ReportTable
    limitations: List[str]
    future_work: List[str]
    final_verdict: str
    confidence: float

class FinalOutput(BaseModel):
    report_markdown: str
    report_json: ResearchReportJSON
    report_pdf_path: Optional[str] = None
