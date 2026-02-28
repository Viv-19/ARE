"""
Audit Logger — Immutable decision logging for human-in-the-loop governance.
Supports HITL decisions, node transition logging, and Gemini usage tracking.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

LOG_PATH = "audit/decisions.jsonl"


def log_decision(decision: Dict[str, Any], node_context: Optional[str] = None) -> None:
    """
    Append a human decision to the audit log with optional node context.
    
    Args:
        decision: The decision data to log (approval status, reasoning, etc.)
        node_context: Optional node name for context (e.g., "NODE-4", "NODE-7")
    """
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "decision": decision
    }
    
    if node_context:
        log_entry["node"] = node_context
    
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def log_gemini_usage(node: str, mode: str, success: bool, fallback_used: bool = False) -> None:
    """
    Log Gemini API usage for auditing and cost tracking.
    
    Args:
        node: Node that made the Gemini call (e.g., "NODE-0")
        mode: Gemini mode used (judgment, execution_support, communication)
        success: Whether the call succeeded
        fallback_used: Whether deterministic fallback was used
    """
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "type": "gemini_usage",
        "node": node,
        "mode": mode,
        "success": success,
        "fallback_used": fallback_used
    }
    
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def log_node_transition(from_node: str, to_node: str, reason: Optional[str] = None) -> None:
    """
    Log graph transitions for debugging and audit trail.
    
    Args:
        from_node: Source node
        to_node: Destination node  
        reason: Optional reason for the transition
    """
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "type": "transition",
        "from": from_node,
        "to": to_node
    }
    
    if reason:
        log_entry["reason"] = reason
    
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

# CORE LOGIC FROZEN — UI SAFE TO ADD
