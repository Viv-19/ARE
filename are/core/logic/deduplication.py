"""
Cross-source paper deduplication.

Pure function.  Takes papers from multiple sources, deduplicates by
normalised title + year, and merges metadata (keeps max citation count).
"""

from __future__ import annotations

from typing import Any, Dict, List


def _dedup_key(paper: Dict[str, Any]) -> str:
    """Normalise title + year into a dedup key."""
    title = paper.get("title", "").strip().lower()[:50]
    year = paper.get("year", 0)
    return f"{title}_{year}"


def deduplicate_papers(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge papers from multiple sources, keeping the richest metadata.

    For duplicates (same normalised title + year):
    - Keep the highest ``citation_count``.
    - Merge ``source`` into a comma-separated list.
    """
    seen: Dict[str, Dict[str, Any]] = {}

    for paper in papers:
        key = _dedup_key(paper)
        if key in seen:
            existing = seen[key]
            # Keep higher citation count
            if paper.get("citation_count", 0) > existing.get("citation_count", 0):
                existing["citation_count"] = paper["citation_count"]
            # Merge source labels
            existing_sources = set(existing.get("source", "").split(", "))
            existing_sources.add(paper.get("source", "Unknown"))
            existing["source"] = ", ".join(sorted(existing_sources))
        else:
            seen[key] = dict(paper)  # Copy to avoid mutation

    return list(seen.values())
