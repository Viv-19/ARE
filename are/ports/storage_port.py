"""
Storage Port — Abstract interface for session / state persistence.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class StoragePort(ABC):
    """Abstract interface for session persistence."""

    @abstractmethod
    def save_session(self, session_id: str, data: Dict[str, Any]) -> None:
        """Persist a complete session snapshot."""
        ...

    @abstractmethod
    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a session by ID, or None if not found."""
        ...

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        """Remove a session from storage."""
        ...

    @abstractmethod
    def list_sessions(self) -> list[str]:
        """Return all known session IDs."""
        ...
