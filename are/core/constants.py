"""
Domain constants — thresholds, enums, and invariants.

All numeric thresholds that control graph routing live here so they are
trivially discoverable and testable.  No magic numbers in node code.
"""

from __future__ import annotations

from typing import Final, FrozenSet

# ---------------------------------------------------------------------------
# NODE-0  Domain Whitelist
# ---------------------------------------------------------------------------
ALLOWED_DOMAIN_KEYWORDS: Final[FrozenSet[str]] = frozenset(
    {
        "quantization", "quantize", "quantized", "int4", "int8",
        "fp16", "bf16", "fp32", "mixed precision",
        "transformer", "attention", "decoder", "encoder",
        "llm", "large language model", "gpt", "llama",
        "inference", "latency", "throughput", "tokens per second",
        "efficiency", "compression", "pruning",
        "residual", "mlp", "layer norm", "kv cache",
        "rounding", "truncation", "precision", "bit width",
        "perplexity", "ppl",
    }
)

VALID_INTENTS: Final = ("exploratory", "replication", "optimization", "comparison")
VALID_AUTONOMY_LEVELS: Final = ("survey_only", "experiment_limited", "experiment_iterative")
VALID_EVIDENCE_THRESHOLDS: Final = ("literature_only", "literature_plus_experiments")

# ---------------------------------------------------------------------------
# NODE-0  Confidence gate
# ---------------------------------------------------------------------------
CONFIDENCE_GATE_THRESHOLD: Final[float] = 0.70

# ---------------------------------------------------------------------------
# NODE-1  Knowledge router
# ---------------------------------------------------------------------------
MIN_RELEVANT_PAPERS: Final[int] = 3
MIN_CITATIONS_PER_PAPER: Final[int] = 100

# ---------------------------------------------------------------------------
# NODE-6  Critic penalties
# ---------------------------------------------------------------------------
PENALTY_SINGLE_SEED: Final[float] = 0.15
PENALTY_EXECUTION_FAILURE: Final[float] = 0.20
PENALTY_WEAK_SIGNAL: Final[float] = 0.10
PENALTY_PRIOR_VIOLATION: Final[float] = 0.40
CONFIDENCE_FLOOR: Final[float] = 0.0
CONCLUSIVE_MIN_CONFIDENCE: Final[float] = 0.75
NOISE_FAILURE_RATIO: Final[float] = 0.50
NOISE_CONFIDENCE_CAP: Final[float] = 0.50
