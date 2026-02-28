from typing import Dict, Any

def log_state_transition(node_name: str, state: Dict[str, Any]):
    """
    Stabilization Utility: Log node entry and visible state surface area.
    Rules: Call only at node entry; do not print full state values.
    """
    # Defensive key collection to avoid mutation during iteration
    keys = list(state.keys())
    print(f"[ARE] Entering {node_name} | Known State Keys: {len(keys)}")
    # Optional detailing for troubleshooting
    # print(f"  - Keys: {keys}")
