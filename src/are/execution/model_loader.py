from typing import Dict, Any, Optional
import os

def resolve_model(
    model_name: str,
    execution_mode: str,
    max_memory_gb: int = 8
) -> Dict[str, Any]:
    """
    The single gatekeeper for academic model resolution.
    Ensures safe loading based on available hardware and execution mode.
    
    Returns:
    {
      "status": "allowed" | "refused",
      "model_id": str,
      "backend": "cpu" | "cuda" | "mps",
      "reason": str
    }
    """
    # 1. Mode Validation
    if execution_mode not in ["dry_run", "local_cpu", "gpu"]:
        return {
            "status": "refused",
            "reason": f"Unsupported execution mode: {execution_mode}"
        }

    # 2. Dry Run - Zero Load Principle
    if execution_mode == "dry_run":
        return {
            "status": "allowed",
            "model_id": f"mock-{model_name}",
            "backend": "none",
            "reason": "Dry run mode - no physical resources allocated"
        }

    # 3. Model Size Estimation (Mock logic for safety gate)
    # In production, this would query a registry or HF metadata
    model_size_params = 7.0 # Default guess in billions
    if "distil" in model_name.lower() or "tiny" in model_name.lower():
        model_size_params = 1.0
    elif "7b" in model_name.lower():
        model_size_params = 7.0

    # 4. Local CPU Constraints
    if execution_mode == "local_cpu":
        if model_size_params > 2.0:
            return {
                "status": "refused",
                "reason": f"Model size ({model_size_params}B) exceeds safety limit for local_cpu (2B)"
            }
        return {
            "status": "allowed",
            "model_id": model_name,
            "backend": "cpu",
            "reason": "Model fits within CPU-safe limits"
        }

    # 5. GPU Constraints (STRICTLY FORBIDDEN IN STABILIZATION PHASE)
    if execution_mode == "gpu":
        return {
            "status": "refused",
            "reason": "GPU execution is strictly disabled during the stabilization phase. Please use 'local_cpu' or 'dry_run'."
        }

    return {"status": "refused", "reason": "Unknown error in model resolution layer"}
