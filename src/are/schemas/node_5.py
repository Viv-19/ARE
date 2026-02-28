from typing import List, Optional, Literal
from pydantic import BaseModel

class ExperimentLog(BaseModel):
    experiment_id: str
    model: str
    quantization: Literal["INT4", "INT8", "FP16"]
    tokens: int
    latency_ms: float
    gpu_memory_mb: float
    status: Literal["success", "failure", "oom"]

class ExecutionArtifact(BaseModel):
    task_id: str
    output_path: str
    checksum: str

class ExecutionStatus(BaseModel):
    execution_status: Literal["completed", "partial", "aborted"]
    artifacts: List[ExecutionArtifact]
    cost_logs: List[ExperimentLog]
    reason: Optional[str] = None
