"""
In-Memory Storage Adapter — non-persistent session store.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from are.ports.storage_port import StoragePort


class MemoryStorage(StoragePort):
    """Thread-safe in-memory session store (fixes B-14)."""

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def save_session(self, session_id: str, data: Dict[str, Any]) -> None:
        with self._lock:
            self._store[session_id] = data

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._store.get(session_id)

    def delete_session(self, session_id: str) -> None:
        with self._lock:
            self._store.pop(session_id, None)

    def list_sessions(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())
