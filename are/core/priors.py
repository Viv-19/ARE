"""
Immutable Scientific Priors — LLM Quantization & Transformer Internals.

These axioms:
  1. Constrain hypothesis generation  (NODE-3)
  2. Ground Gemini prompt reasoning   (NODE-6, NODE-8)
  3. Act as a critic checklist        (NODE-6)

DO NOT MODIFY without verifiable, peer-reviewed evidence.
"""

from __future__ import annotations

from typing import Dict, Final, List

LLM_QUANTIZATION_PRIORS: Final[Dict[str, List[str]]] = {
    "numerical_error": [
        "Quantization error accumulates across transformer layers, especially in deep networks.",
        "Residual streams amplify rounding noise more than attention weights due to additive updates.",
        "Error propagation is autoregressive in decoder-only models, compounding over token generation.",
        "FP16 to BF16 conversion preserves dynamic range but loses precision, affecting gradient stability.",
    ],
    "quantization_effects": [
        "INT4 quantization introduces non-linear error compared to INT8 due to limited dynamic range.",
        "Post-training quantization (PTQ) affects residual paths disproportionately compared to weights.",
        "LayerNorm parameters are sensitive to quantization and are often kept in higher precision (FP16/FP32).",
        "Activation outliers in larger models (>6B params) make uniform quantization inaccurate "
        "(requires block-wise/group-wise).",
    ],
    "measurement_constraints": [
        "Single-seed experiments are insufficient for stability claims; minimum 3 seeds required.",
        "Latency improvements must be normalized by token count (tokens/sec) to be comparable.",
        "Memory savings (VRAM) do not imply quality preservation; perplexity (PPL) is the standard proxy.",
        "Inference throughput is memory-bandwidth bound for batch size 1 (decoding phase).",
    ],
    "transformer_internals": [
        "Attention mechanisms are robust to some weight noise but sensitive to KV-cache precision.",
        "MLP blocks constitute ~2/3 of parameters and are the primary target for weight quantization savings.",
        "Positional embeddings (RoPE/ALiBi) are highly sensitive to quantization and should remain in FP32.",
    ],
}


def get_priors_text() -> str:
    """Return a prompt-injectable formatted string of all priors."""
    lines = ["SCIENTIFIC PRIORS (AXIOMS):"]
    for category, items in LLM_QUANTIZATION_PRIORS.items():
        lines.append(f"\n[{category.upper()}]")
        for item in items:
            lines.append(f"  - {item}")
    return "\n".join(lines)
