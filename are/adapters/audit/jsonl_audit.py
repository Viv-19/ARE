"""
JSONL Audit Logger — append-only immutable decision log.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from are.ports.audit_port import AuditPort


class JSONLAuditLogger(AuditPort):
    """Thread-safe, append-only JSONL audit logger."""

    def __init__(self, path: str = "audit/decisions.jsonl"):
        self._path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def _append(self, entry: Dict[str, Any]) -> None:
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")

    def log_decision(
        self, decision: Dict[str, Any], *, node: Optional[str] = None
    ) -> None:
        entry: Dict[str, Any] = {"type": "decision", "decision": decision}
        if node:
            entry["node"] = node
        self._append(entry)

    def log_llm_usage(
        self,
        *,
        node: str,
        mode: str,
        success: bool,
        fallback_used: bool = False,
    ) -> None:
        self._append({
            "type": "llm_usage",
            "node": node,
            "mode": mode,
            "success": success,
            "fallback_used": fallback_used,
        })

    def log_transition(
        self, from_node: str, to_node: str, *, reason: Optional[str] = None
    ) -> None:
        entry: Dict[str, Any] = {
            "type": "transition",
            "from": from_node,
            "to": to_node,
        }
        if reason:
            entry["reason"] = reason
        self._append(entry)
