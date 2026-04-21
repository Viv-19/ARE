"""
Variable extraction — keyword-to-variable mapping.

Pure function.  Maps domain-specific terms to IV/DV/CV categories.
"""

from __future__ import annotations

from typing import Dict, List

# Mapping of keywords → variable role
_IV_KEYWORDS = {
    "int4": "INT4 Quantization",
    "int8": "INT8 Quantization",
    "fp16": "FP16 Precision",
    "bf16": "BF16 Precision",
    "quantiz": "Quantization Method",
    "bit width": "Quantization Bit Width",
    "rounding": "Rounding technique",
    "truncat": "Truncation method",
    "pruning": "Pruning strategy",
    "block size": "Block size",
    "group size": "Group size",
}

_DV_KEYWORDS = {
    "latency": "Computational Efficiency (Latency)",
    "throughput": "Inference Throughput (tokens/sec)",
    "perplexity": "Model Quality (Perplexity)",
    "ppl": "Model Quality (Perplexity)",
    "accuracy": "Prediction Accuracy",
    "memory": "GPU Memory Usage",
    "vram": "GPU Memory Usage",
    "quality": "Output Quality",
    "loss": "Training/Eval Loss",
    "similarity": "Semantic Similarity",
}

_CV_DEFAULTS = [
    "Model architecture (Decoder-only)",
    "Base precision (FP32 reference)",
    "Evaluation dataset",
]


def extract_variables(question: str) -> Dict[str, List[str]]:
    """Extract independent, dependent, and control variables from a question."""
    lower = question.lower()

    independent = []
    for kw, var in _IV_KEYWORDS.items():
        if kw in lower and var not in independent:
            independent.append(var)

    dependent = []
    for kw, var in _DV_KEYWORDS.items():
        if kw in lower and var not in dependent:
            dependent.append(var)

    # Defaults when extraction yields nothing
    if not independent:
        independent = ["Quantization Method"]
    if not dependent:
        dependent = ["Computational Efficiency (Latency)"]

    return {
        "independent": independent,
        "dependent": dependent,
        "control": list(_CV_DEFAULTS),
    }
