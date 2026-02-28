try:
    import torch
except ImportError:
    torch = None

def measure_gpu_memory() -> float:
    """
    Returns peak GPU memory usage in MB.
    Returns 0.0 if CUDA is not available.
    """
    if not torch or not torch.cuda.is_available():
        return 0.0
        
    # Convert bytes to MB
    memory_mb = torch.cuda.max_memory_allocated() / (1024 * 1024)
    return memory_mb

def reset_memory_stats():
    """Reset peak memory stats to ensure fresh measurement."""
    if torch and torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
