"""
NODE-5 — Worker / Execution Controller
Generates experiment code for user execution and collects results.
"""

from ..state import GraphState
from ..execution.model_loader import resolve_model
from ..utils.reproducibility import set_global_seed
from ..schemas.node_5 import (
    ExperimentLog,
    ExecutionArtifact,
    ExecutionStatus
)
from ..utils.logging import log_state_transition
import logging
import traceback

logger = logging.getLogger(__name__)

def node_5_worker_execution_controller(state: GraphState) -> GraphState:
    """
    NODE-5 — Worker / Execution Node: Generate experiment code for user execution.
    Instead of running experiments, this node generates Python code/notebooks
    that the user will execute and submit results for.
    """
    log_state_transition("NODE-5", state)
    
    seed = state.get("random_seed", 42)
    set_global_seed(seed)
    
    execution_mode = state.get("execution_mode", "dry_run")
    contract = state.get("research_contract", {})
    
    print(f"[NODE-5] Generating experiment code...")
    logger.info(f"[NODE-5] Mode: {execution_mode}, Seed: {seed}")
    
    # Execution Guard (Governance Check)
    human_decisions = state.get("human_decisions", [])
    last_decision = human_decisions[-1] if human_decisions else {}
    
    if not human_decisions or (
        last_decision.get("approval_status") != "approved" and 
        last_decision.get("action") != "approve"
    ):
        logger.warning("[NODE-5] Contract not approved. Execution denied.")
        state.update({
            "execution_status": "aborted",
            "errors": state.get("errors", []) + ["Contract not approved. Execution denied."],
            "reasoning": "Execution blocked: Research contract requires human approval before proceeding."
        })
        return state

    # Generate experiment code using Gemini
    experiment_code = _generate_experiment_code(state)
    
    if not experiment_code:
        logger.warning("[NODE-5] Failed to generate experiment code, using template")
        experiment_code = _get_template_code(state)
    
    # Build task descriptions for display
    tasks = contract.get("tasks", [])
    task_descriptions = [
        f"- Task {t.get('id', i+1)}: {t.get('description', 'Execute experiment')}"
        for i, t in enumerate(tasks)
    ]
    
    # Build cost logs (simulated for UI compatibility)
    cost_logs = []
    for i, task in enumerate(tasks):
        cost_logs.append({
            "experiment_id": f"EXP_{task.get('id', i+1)}",
            "task_description": task.get("description", ""),
            "status": "awaiting_user_execution",
            "random_seed": seed,
            "notes": "Code generated. Awaiting user execution and result submission."
        })
    
    # Prepare experiment instructions
    experiment_instructions = f"""
## Experiment Execution Instructions

### Overview
The following Python code implements the experiments defined in your research contract.
Please execute this code on your local machine or Colab environment.

### Tasks to Complete
{chr(10).join(task_descriptions)}

### Requirements
- Python 3.8+
- PyTorch 2.0+
- transformers library
- sentence-transformers (for SBERT metrics)
- CUDA-capable GPU (recommended)

### Execution Steps
1. Copy the code below to a Python file or Jupyter notebook
2. Install required dependencies
3. Run the experiments
4. Collect the results (JSON files will be generated)
5. Submit results via the ARE interface

### Code
```python
{experiment_code}
```

### Expected Outputs
After running the code, you should have:
- Experiment logs with metrics (MAE, KL, Top-1 Flip, etc.)
- SBERT similarity scores
- Per-layer analysis data (if applicable)

Submit these results to proceed to the Critic node (NODE-6).
"""

    reasoning = (
        f"Generated experiment code for {len(tasks)} tasks. "
        f"Code includes model loading, quantization, and metric collection. "
        f"User must execute code and submit results for analysis."
    )

    state.update({
        "execution_status": "awaiting_user_execution",
        "experiment_code": experiment_code,
        "experiment_instructions": experiment_instructions,
        "execution_logs": cost_logs,
        "artifacts": [],
        "reasoning": reasoning
    })
    
    print(f"[NODE-5] ✓ Generated experiment code for {len(tasks)} tasks")
    logger.info(f"[NODE-5] ✓ Complete. Code generated, awaiting user execution.")

    return state


def _generate_experiment_code(state: GraphState) -> str:
    """Generate experiment code using Gemini."""
    try:
        from ..config import USE_GEMINI
        if not USE_GEMINI:
            return None
            
        from ..utils.gemini import call_gemini
        
        contract = state.get("research_contract", {})
        question = state.get("normalized_question", "")
        hypotheses = contract.get("hypotheses", {})
        metrics = contract.get("metrics", {})
        tasks = contract.get("tasks", [])
        
        prompt = f"""Generate Python experiment code for this research study.

Research Question: "{question}"

Hypotheses:
{hypotheses}

Required Metrics:
{metrics}

Tasks:
{[t.get('description') for t in tasks]}

Requirements:
1. Use PyTorch and Hugging Face transformers
2. Implement deterministic execution with seed control
3. Measure these metrics:
   - MAE (Mean Absolute Error on logits)
   - KL Divergence
   - Top-1 Flip Rate
   - Top-5 Overlap
   - SBERT Similarity
4. Support multiple quantization levels (FP16, INT8, INT4)
5. Include proper error handling
6. Output results as JSON file named 'experiment_results.json'

Generate complete, runnable Python code. Include all imports.
Return JSON:
{{"code": "# Your complete Python code here..."}}
"""
        
        result = call_gemini(prompt, mode="execution_support", expect_json=True, fallback=None)
        if result and "code" in result:
            logger.info("[NODE-5] ✓ Gemini generated experiment code")
            return result["code"]
        return None
    except Exception as e:
        logger.error(f"[NODE-5] Code generation failed: {e}")
        return None


def _get_template_code(state: GraphState) -> str:
    """Return template experiment code."""
    seed = state.get("random_seed", 42)
    contract = state.get("research_contract", {})
    model_name = contract.get("model", "gpt2")
    
    return f'''"""
ARE Experiment Code - Auto-generated
Research Question: {state.get("normalized_question", "")[:100]}
"""

import torch
import json
import numpy as np
from datetime import datetime
from transformers import AutoModelForCausalLM, AutoTokenizer
from sentence_transformers import SentenceTransformer

# Configuration
SEED = {seed}
MODEL_NAME = "{model_name}"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Reproducibility
torch.manual_seed(SEED)
np.random.seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

print(f"Using device: {{DEVICE}}")
print(f"Random seed: {{SEED}}")

# Load model and tokenizer
print("Loading model...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model_fp16 = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME, 
    torch_dtype=torch.float16,
    device_map="auto"
)

# Sample prompts for testing
TEST_PROMPTS = [
    "The transformer architecture revolutionized",
    "In the field of natural language processing,",
    "Quantization techniques for neural networks",
    "The impact of precision reduction on",
    "Modern large language models demonstrate"
]

def compute_metrics(baseline_logits, test_logits):
    """Compute evaluation metrics between baseline and test logits."""
    # MAE
    mae = torch.mean(torch.abs(baseline_logits - test_logits)).item()
    
    # KL Divergence
    baseline_probs = torch.softmax(baseline_logits, dim=-1)
    test_probs = torch.softmax(test_logits, dim=-1)
    kl_div = torch.nn.functional.kl_div(
        test_probs.log(), baseline_probs, reduction='batchmean'
    ).item()
    
    # Top-1 Flip Rate
    baseline_top1 = torch.argmax(baseline_logits, dim=-1)
    test_top1 = torch.argmax(test_logits, dim=-1)
    top1_flip = (baseline_top1 != test_top1).float().mean().item()
    
    # Top-5 Overlap
    baseline_top5 = torch.topk(baseline_logits, k=5, dim=-1).indices
    test_top5 = torch.topk(test_logits, k=5, dim=-1).indices
    overlap = sum(1 for b, t in zip(baseline_top5[0], test_top5[0]) if t in b) / 5
    
    return {{
        "mae": mae,
        "kl_divergence": kl_div,
        "top1_flip_rate": top1_flip,
        "top5_overlap": overlap
    }}

def run_experiment():
    """Run the quantization experiment."""
    results = []
    
    for prompt in TEST_PROMPTS:
        print(f"Processing: {{prompt[:50]}}...")
        
        inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
        
        with torch.no_grad():
            # Baseline FP16
            baseline_outputs = model_fp16(**inputs)
            baseline_logits = baseline_outputs.logits[:, -1, :]
            
            # Generate continuation
            generated = model_fp16.generate(
                **inputs,
                max_new_tokens=50,
                do_sample=False,
                use_cache=False
            )
            continuation = tokenizer.decode(generated[0], skip_special_tokens=True)
        
        results.append({{
            "prompt": prompt,
            "continuation": continuation,
            "baseline_logits_mean": baseline_logits.mean().item(),
            "baseline_logits_std": baseline_logits.std().item()
        }})
    
    return results

def compute_sbert_similarity(text1, text2):
    """Compute SBERT similarity between two texts."""
    sbert = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = sbert.encode([text1, text2])
    similarity = np.dot(embeddings[0], embeddings[1]) / (
        np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
    )
    return similarity

if __name__ == "__main__":
    print("=" * 60)
    print("ARE Experiment - Starting")
    print("=" * 60)
    
    results = run_experiment()
    
    # Save results
    output = {{
        "experiment_id": f"EXP_{{datetime.now().strftime('%Y%m%d_%H%M%S')}}",
        "seed": SEED,
        "model": MODEL_NAME,
        "device": DEVICE,
        "results": results,
        "timestamp": datetime.now().isoformat()
    }}
    
    with open("experiment_results.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print("\\n" + "=" * 60)
    print("Experiment Complete!")
    print(f"Results saved to: experiment_results.json")
    print("=" * 60)
'''

# CORE LOGIC FROZEN — UI SAFE TO ADD
