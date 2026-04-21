"""
Centralised settings — single source of truth for all configuration.

Loaded from environment variables and ``.env`` file via Pydantic Settings.
Every adapter and service reads from this; there are NO secondary config
files (the old ``tools/__init__.py USE_MOCK`` anti-pattern is eliminated).
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Immutable application settings."""

    # --- LLM Provider --------------------------------------------------
    llm_provider: Literal["gemini", "openai", "mock", "groq"] = "groq"
    llm_model: str = "llama-3.3-70b-versatile"
    llm_api_key: str = ""
    llm_max_retries: int = 5

    # --- Academic Search -----------------------------------------------
    use_mock_search: bool = True
    semantic_scholar_api_key: str = ""
    arxiv_api_key: str = ""
    openalex_api_key: str = ""

    # --- HITL ----------------------------------------------------------
    enable_real_hitl: bool = True
    enable_node_0_confirm: bool = True
    hitl_timeout_seconds: int = 1800  # 30 min default

    # --- Storage -------------------------------------------------------
    storage_backend: Literal["memory", "sqlite"] = "memory"
    db_path: str = "are_sessions.db"

    # --- Audit ---------------------------------------------------------
    audit_log_path: str = "audit/decisions.jsonl"

    # --- Execution -----------------------------------------------------
    default_execution_mode: str = "dry_run"
    default_random_seed: int = 42
    max_experiments: int = 3
    max_vram_gb: int = 8

    # --- Server --------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    log_structured: bool = False

    # --- HuggingFace ---------------------------------------------------
    hf_token: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton of application settings."""
    return Settings()
