"""
Research Service — core orchestration bridging the graph engine with
the DI container.

Manages graph creation, session lifecycle, and HITL resume operations.
Context is injected into the graph via closures at creation time,
NOT via state (avoids LangGraph serialisation issues).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from are.application.container import Container
from are.core.graph import create_are_graph

logger = logging.getLogger(__name__)


class ResearchService:
    """Stateless service orchestrating the ARE graph lifecycle."""

    def __init__(self, container: Container):
        self._container = container
        self._checkpointer = MemorySaver()

        # Build context dict for closures (NOT stored in state)
        settings = container.settings
        self._ctx = {
            "llm": container.llm,
            "search_adapters": container.search_adapters,
            "audit": container.audit,
            "enable_real_hitl": settings.enable_real_hitl if settings else True,
            "enable_node_0_confirm": settings.enable_node_0_confirm if settings else True,
        }

        self._graph = create_are_graph(
            checkpointer=self._checkpointer,
            ctx=self._ctx,
        )

    # ── Public API ───────────────────────────────────────────────────

    def start_research(
        self,
        question: str,
        *,
        session_id: Optional[str] = None,
        execution_mode: str = "dry_run",
        random_seed: int = 42,
    ) -> Dict[str, Any]:
        """Initialise and begin a research session.

        Returns the session metadata (id, config).
        """
        sid = session_id or str(uuid.uuid4())[:12]
        settings = self._container.settings

        # State contains ONLY serialisable data — no adapter refs
        initial_state = {
            "research_question": question,
            "execution_mode": execution_mode,
            "random_seed": random_seed,
            "constraints": {"max_vram_gb": settings.max_vram_gb if settings else 8},
            "errors": [],
            "iteration_count": 0,
            "human_decisions": [],
            "_session_id": sid,
        }

        config = {"configurable": {"thread_id": sid}}

        logger.info("Starting research session %s", sid)

        return {
            "session_id": sid,
            "config": config,
            "initial_state": initial_state,
        }

    def run_graph(self, initial_state: Dict, config: Dict):
        """Execute the graph (blocking generator).

        Yields (event_type, data) tuples for each graph step.
        Stops at interrupts or completion.
        """
        for event in self._graph.stream(
            initial_state, config, stream_mode="updates"
        ):
            yield event

    def resume_graph(self, session_id: str, decision: Dict[str, Any]):
        """Resume the graph after an HITL interrupt.

        Yields (event_type, data) tuples.
        """
        config = {"configurable": {"thread_id": session_id}}
        for event in self._graph.stream(
            Command(resume=decision), config, stream_mode="updates"
        ):
            yield event

    def get_state(self, session_id: str) -> Dict[str, Any]:
        """Get the current graph state for a session."""
        config = {"configurable": {"thread_id": session_id}}
        state = self._graph.get_state(config)
        return {
            "values": state.values,
            "next": state.next,
        }

    @property
    def graph(self):
        """Expose the compiled graph (for advanced introspection)."""
        return self._graph
