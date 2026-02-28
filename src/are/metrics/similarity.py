def compute_similarity(text_a: str, text_b: str) -> float:
    """
    Computes semantic similarity score between two strings.
    In a real implementation, this would use SBERT or similar.
    This implementation is deterministic given same inputs.
    """
    if not text_a or not text_b:
        return 0.0
        
    # Standardize
    a = text_a.lower().strip()
    b = text_b.lower().strip()
    
    if a == b:
        return 1.0
        
    # Deterministic placeholder using intersection over union of characters 
    # (Simplified for reproducibility without heavy dependencies)
    set_a = set(a)
    set_b = set(b)
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    
    return intersection / union if union > 0 else 0.0
