"""
Node tracing decorator — auto-instruments every node with structured
entry/exit/error logging and latency measurement.
"""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, Dict

logger = logging.getLogger("are.nodes")


def traced_node(node_name: str) -> Callable:
    """Decorator that wraps a node function with observability."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
            session_id = state.get("_session_id", "???")
            state_keys = len(state)

            logger.info(
                "[%s] ENTER  | session=%s  keys=%d",
                node_name, session_id, state_keys,
                extra={"node": node_name, "session_id": session_id, "event_type": "node_entry"},
            )

            start = time.perf_counter()
            try:
                result = func(state)
                elapsed_ms = (time.perf_counter() - start) * 1000

                out_keys = list(result.keys()) if isinstance(result, dict) else ["Command"]
                logger.info(
                    "[%s] EXIT   | %.0fms  output_keys=%s",
                    node_name, elapsed_ms, out_keys,
                    extra={
                        "node": node_name,
                        "session_id": session_id,
                        "event_type": "node_exit",
                        "latency_ms": elapsed_ms,
                    },
                )
                return result

            except Exception as exc:
                # GraphInterrupt is LangGraph's control flow for HITL —
                # it must propagate, NOT be caught as an error.
                from langgraph.errors import GraphInterrupt
                if isinstance(exc, GraphInterrupt):
                    raise

                elapsed_ms = (time.perf_counter() - start) * 1000
                logger.error(
                    "[%s] ERROR  | %.0fms  %s: %s",
                    node_name, elapsed_ms, type(exc).__name__, exc,
                    exc_info=True,
                    extra={
                        "node": node_name,
                        "session_id": session_id,
                        "event_type": "node_error",
                        "latency_ms": elapsed_ms,
                    },
                )
                # Graceful degradation: surface the error in state
                return {
                    "errors": state.get("errors", []) + [f"{node_name}: {exc}"],
                    "reasoning": f"Node {node_name} failed with {type(exc).__name__}: {exc}",
                }

        return wrapper
    return decorator
