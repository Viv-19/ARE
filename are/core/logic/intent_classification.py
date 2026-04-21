"""
Intent classification — deterministic keyword-based classifier.

Pure function.  Used as fallback when the LLM is unavailable.
"""

from __future__ import annotations

from typing import Tuple


_INTENT_KEYWORDS = {
    "comparison": {"compare", "versus", "vs", "differ", "benchmark", "contrast"},
    "optimization": {"optimize", "improve", "reduce", "minimiz", "maximiz", "enhance", "speed up"},
    "replication": {"replicate", "reproduce", "verify", "confirm", "baseline"},
}


def classify_intent(question: str) -> Tuple[str, float]:
    """Classify research intent from keywords.

    Returns:
        (intent, confidence) where intent ∈ VALID_INTENTS.
    """
    lower = question.lower()

    for intent, keywords in _INTENT_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return intent, 0.75

    return "exploratory", 0.65
