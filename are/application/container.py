"""
Dependency Injection Container — the ONLY place where concrete adapters
are imported and instantiated.

Everything else in the application depends on abstract ports.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

from are.config.settings import Settings
from are.ports.audit_port import AuditPort
from are.ports.llm_port import LLMPort
from are.ports.search_port import SearchPort
from are.ports.storage_port import StoragePort

logger = logging.getLogger(__name__)


@dataclass
class Container:
    """Wired at application startup.  Passed to services and graph context."""

    llm: LLMPort
    search_adapters: List[SearchPort] = field(default_factory=list)
    storage: StoragePort = None  # type: ignore[assignment]
    audit: AuditPort = None  # type: ignore[assignment]
    settings: Settings = None  # type: ignore[assignment]


def build_container(settings: Settings) -> Container:
    """Build the DI container from application settings.

    This is the composition root of the entire application.
    """
    # ── LLM ──────────────────────────────────────────────────────────
    from are.adapters.llm.factory import create_llm_adapter

    llm = create_llm_adapter(
        provider=settings.llm_provider,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
    )
    logger.info("LLM adapter: %s", llm.provider_name)

    # ── Search adapters ──────────────────────────────────────────────
    search_adapters: List[SearchPort] = []

    if settings.use_mock_search:
        from are.adapters.search.mock_search import MockSearchAdapter
        search_adapters.append(MockSearchAdapter())
    else:
        from are.adapters.search.semantic_scholar import SemanticScholarAdapter
        search_adapters.append(
            SemanticScholarAdapter(api_key=settings.semantic_scholar_api_key)
        )

        from are.adapters.search.arxiv_adapter import ArxivAdapter
        search_adapters.append(ArxivAdapter())

    logger.info(
        "Search adapters: %s",
        [a.source_name for a in search_adapters],
    )

    # ── Storage ──────────────────────────────────────────────────────
    if settings.storage_backend == "sqlite":
        # Future: from are.adapters.storage.sqlite_storage import SQLiteStorage
        # storage = SQLiteStorage(db_path=settings.db_path)
        from are.adapters.storage.memory_storage import MemoryStorage
        storage = MemoryStorage()
    else:
        from are.adapters.storage.memory_storage import MemoryStorage
        storage = MemoryStorage()

    # ── Audit ─────────────────────────────────────────────────────────
    from are.adapters.audit.jsonl_audit import JSONLAuditLogger
    audit = JSONLAuditLogger(path=settings.audit_log_path)

    return Container(
        llm=llm,
        search_adapters=search_adapters,
        storage=storage,
        audit=audit,
        settings=settings,
    )
