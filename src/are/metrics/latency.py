import time
from typing import Callable, Any, Tuple

def measure_latency(fn: Callable, *args, **kwargs) -> Tuple[Any, float]:
    """
    Measures wall-clock inference latency in milliseconds.
    Excludes setup time by wrapping the target function.
    
    Returns:
        (result, latency_ms)
    """
    start_time = time.perf_counter()
    result = fn(*args, **kwargs)
    end_time = time.perf_counter()
    
    latency_ms = (end_time - start_time) * 1000
    return result, latency_ms
