"""
Domain validation — hard-whitelist checker.

Pure function: takes a string, returns a verdict.  Zero I/O.
"""

from __future__ import annotations

from are.core.constants import ALLOWED_DOMAIN_KEYWORDS


def is_domain_valid(question: str) -> bool:
    """Return True if *question* contains at least one allowed keyword."""
    lower = question.lower()
    return any(kw in lower for kw in ALLOWED_DOMAIN_KEYWORDS)


def get_rejection_reason(question: str) -> str:
    """Return a user-facing explanation of why the question was rejected."""
    return (
        f"The query '{question[:80]}...' does not match any allowed research "
        "domain.  AROS is restricted to: LLM Quantization (INT4/INT8/FP16/BF16), "
        "Transformer Architecture, Inference Efficiency, and Transformer Internals."
    )
