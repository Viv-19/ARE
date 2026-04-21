"""
NODE-5 — Worker / Experiment Code Generator.

Generates experiment code for user execution.  Does NOT execute locally.
Uses interrupt() to pause for user experiment results (fixes B-09).
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from langgraph.types import Command, interrupt

from are.core.nodes._tracing import traced_node
from are.ports.llm_port import LLMMode

logger = logging.getLogger(__name__)


_EXPERIMENT_TEMPLATE = '''"""
ARE Auto-Generated Experiment Script
Question: {question}
Seed: {seed}
Mode: {mode}
"""
import torch
import json
import time
from transformers import AutoModelForCausalLM, AutoTokenizer

SEED = {seed}
MODEL_ID = "distilgpt2"
PROMPT = "The effect of quantization on transformer inference is"
MAX_TOKENS = 50

torch.manual_seed(SEED)

def run_experiment():
    results = []
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    inputs = tokenizer(PROMPT, return_tensors="pt")

    for method, dtype in [("FP16", torch.float16), ("INT8", None)]:
        if method == "INT8":
            model = AutoModelForCausalLM.from_pretrained(MODEL_ID, load_in_8bit=True, device_map="auto")
        else:
            model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=dtype)

        start = time.perf_counter()
        with torch.no_grad():
            output = model.generate(**inputs, max_new_tokens=MAX_TOKENS)
        latency_ms = (time.perf_counter() - start) * 1000

        text = tokenizer.decode(output[0], skip_special_tokens=True)
        results.append({{
            "experiment_id": f"EXP_{{method}}",
            "model": MODEL_ID,
            "quantization": method,
            "latency_ms": round(latency_ms, 2),
            "output_preview": text[:100],
            "random_seed": SEED,
            "status": "success",
        }})
        del model

    print(json.dumps(results, indent=2))
    return results

if __name__ == "__main__":
    run_experiment()
'''


@traced_node("NODE-5")
def node_5_worker(state: Dict[str, Any]) -> Any:
    """Worker node: generate experiment code and await user results."""

    contract = state.get("research_contract", {})
    question = state.get("normalized_question", state.get("research_question", ""))
    seed = state.get("random_seed", 42)
    mode = state.get("execution_mode", "dry_run")
    ctx = state.get("_ctx", {})
    llm = ctx.get("llm")

    # ── Guard: approval check ────────────────────────────────────────
    decisions = state.get("human_decisions", [])
    if decisions and decisions[-1].get("approval_status") != "approved":
        return {
            "execution_status": "aborted",
            "errors": state.get("errors", []) + [
                "NODE-5: Cannot execute without approved contract."
            ],
        }

    # ── Generate experiment code ─────────────────────────────────────
    code = _generate_code(llm, contract, question, seed, mode)

    instructions = (
        "## Experiment Execution Instructions\n\n"
        "1. Copy the generated Python code below.\n"
        "2. Run it in your local environment with GPU or `dry_run` mode.\n"
        "3. Collect the JSON output from stdout.\n"
        "4. Submit the results back to the API.\n\n"
        f"**Seed:** {seed}  |  **Mode:** {mode}  |  "
        f"**Max experiments:** {contract.get('constraints', {}).get('max_experiments', 3)}"
    )

    # ── Dry-run: generate mock logs ──────────────────────────────────
    if mode == "dry_run":
        mock_logs = [
            {
                "experiment_id": "EXP_FP16",
                "model": "distilgpt2",
                "quantization": "FP16",
                "latency_ms": 145.2,
                "gpu_memory_mb": 0.0,
                "semantic_similarity": 1.0,
                "random_seed": seed,
                "status": "success",
            },
            {
                "experiment_id": "EXP_INT8",
                "model": "distilgpt2",
                "quantization": "INT8",
                "latency_ms": 98.7,
                "gpu_memory_mb": 0.0,
                "semantic_similarity": 0.87,
                "random_seed": seed,
                "status": "success",
            },
        ]
        return {
            "execution_status": "completed",
            "execution_logs": mock_logs,
            "experiment_code": code,
            "experiment_instructions": instructions,
            "artifacts": [],
        }

    # ── Real execution: interrupt for user results (B-09 fix) ────────
    result_payload = {
        "type": "experiment_results",
        "experiment_code": code,
        "experiment_instructions": instructions,
    }
    user_results = interrupt(result_payload)
    logger.info("[NODE-5] Received user experiment results.")

    execution_logs = user_results.get("results", []) if isinstance(user_results, dict) else []

    return {
        "execution_status": "completed",
        "execution_logs": execution_logs,
        "experiment_code": code,
        "experiment_instructions": instructions,
        "artifacts": [],
    }


def _generate_code(llm, contract, question, seed, mode) -> str:
    """Generate experiment code via LLM or template fallback."""
    if llm and llm.is_available():
        tasks_str = "\n".join(
            f"- {t['id']}: {t['description']}"
            for t in contract.get("tasks", [])
        )
        prompt = (
            f"Generate a complete Python experiment script for:\n"
            f"Question: {question}\n"
            f"Tasks:\n{tasks_str}\n"
            f"Seed: {seed}, Mode: {mode}\n"
            f"Output a SINGLE Python file that prints JSON results to stdout."
        )
        resp = llm.generate(prompt, mode=LLMMode.EXECUTION_SUPPORT, expect_json=False)
        if resp.success and resp.content:
            # Extract code from markdown if needed
            content = resp.content
            if "```python" in content:
                content = content.split("```python")[-1].split("```")[0]
            return content.strip()

    return _EXPERIMENT_TEMPLATE.format(question=question, seed=seed, mode=mode)
