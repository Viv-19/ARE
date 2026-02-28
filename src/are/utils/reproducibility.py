try:
    import torch
except ImportError:
    torch = None

try:
    import numpy as np
except ImportError:
    np = None

import random
import logging

logger = logging.getLogger(__name__)

def set_global_seed(seed: int):
    """
    Sets the seed for reproducibility across all common scientific libraries.
    """
    if seed is None:
        seed = 42
        
    random.seed(seed)
    if np:
        np.random.seed(seed)
    if torch:
        torch.manual_seed(seed)
    
    # Ensure CUDA seeds are set if available
    if torch and torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        # Ensure deterministic behavior (performance trade-off)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

    logger.info(f"Global seed set to: {seed}")
