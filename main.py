"""
ARE Main Entry Point — boots the application.

Usage:
    python main.py                  # Start FastAPI server
    python main.py --cli            # Run CLI demo
    python main.py --cli --question "your question"
"""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="AROS — Autonomous Research Orchestration System")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode (no server)")
    parser.add_argument("--question", type=str, default="", help="Research question (CLI mode)")
    parser.add_argument("--host", type=str, default=None, help="Server host")
    parser.add_argument("--port", type=int, default=None, help="Server port")
    args = parser.parse_args()

    # ── Bootstrap ─────────────────────────────────────────────────────
    from are.config.settings import get_settings
    from are.config.logging_config import configure_logging

    settings = get_settings()
    configure_logging(level=settings.log_level, structured=settings.log_structured)

    from are.application.container import build_container
    container = build_container(settings)

    if args.cli:
        # ── CLI mode ─────────────────────────────────────────────────
        from are.interfaces.cli.runner import run_cli
        question = args.question or input("Enter research question: ")
        run_cli(container, question)
    else:
        # ── Server mode ──────────────────────────────────────────────
        import uvicorn
        from are.interfaces.api.app import create_app

        app = create_app(container)
        uvicorn.run(
            app,
            host=args.host or settings.host,
            port=args.port or settings.port,
        )


if __name__ == "__main__":
    main()
