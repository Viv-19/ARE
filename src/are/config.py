"""
ARE System Configuration
All settings are loaded from .env file for centralized control.
"""

import os
from pathlib import Path

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, use environment variables directly


def _get_bool(key: str, default: bool) -> bool:
    """Parse boolean from environment variable."""
    val = os.environ.get(key, str(default)).lower()
    return val in ("true", "1", "yes", "on")


# ============================================================
# HITL Controls
# ============================================================
ENABLE_REAL_HITL = _get_bool("ENABLE_REAL_HITL", True)

# ============================================================
# Tool Adapter Controls
# ============================================================
USE_MOCK = _get_bool("USE_MOCK", True)

# ============================================================
# Gemini Controls
# ============================================================
USE_GEMINI = _get_bool("USE_GEMINI", False)
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ============================================================
# Node-0 Confirmation Control
# ============================================================
ENABLE_NODE_0_CONFIRM = _get_bool("ENABLE_NODE_0_CONFIRM", True)

# ============================================================
# Academic Search API Keys
# ============================================================
SEMANTIC_SCHOLAR_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
ARXIV_API_KEY = os.environ.get("ARXIV_API_KEY", "")
OPENALEX_API_KEY = os.environ.get("OPENALEX_API_KEY", "")

# ============================================================
# HuggingFace
# ============================================================
HF_TOKEN = os.environ.get("HF_TOKEN", "")
