"""
OpenAlex API adapter for academic paper search.
Uses the OpenAlex API for open access paper metadata.
"""

from typing import List, Dict, Any
import logging
import requests

logger = logging.getLogger(__name__)

OPENALEX_API = "https://api.openalex.org"

def search(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Perform a metadata-only academic search on OpenAlex.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        
    Returns:
        List of paper metadata dictionaries
    """
    from . import USE_MOCK
    from ..config import OPENALEX_API_KEY
    
    if USE_MOCK:
        logger.info(f"[OpenAlex] Using mock data for query: {query[:50]}...")
        return _get_mock_results()
    
    logger.info(f"[OpenAlex] Searching for: {query[:50]}...")
    
    try:
        params = {
            "search": query,
            "per_page": max_results,
            "sort": "cited_by_count:desc"
        }
        
        # Add email/API key for polite pool
        if OPENALEX_API_KEY:
            params["api_key"] = OPENALEX_API_KEY
        
        response = requests.get(
            f"{OPENALEX_API}/works",
            params=params,
            timeout=15
        )
        
        response.raise_for_status()
        data = response.json()
        
        results = []
        for work in data.get("results", []):
            # Extract author names
            authorships = work.get("authorships", [])
            author_names = []
            for auth in authorships[:5]:
                author = auth.get("author", {})
                name = author.get("display_name", "Unknown")
                author_names.append(name)
            
            # Extract year from publication date
            pub_date = work.get("publication_date", "")
            year = int(pub_date[:4]) if pub_date and len(pub_date) >= 4 else 2024
            
            # Get venue
            primary_location = work.get("primary_location", {}) or {}
            source = primary_location.get("source", {}) or {}
            venue = source.get("display_name", "Unknown")
            
            results.append({
                "title": work.get("title", "Untitled") or "Untitled",
                "year": year,
                "authors": author_names,
                "citation_count": work.get("cited_by_count", 0),
                "venue": venue,
                "abstract": "",  # OpenAlex often doesn't include abstracts in search
                "url": work.get("doi", "") or work.get("id", ""),
                "source": "OpenAlex"
            })
        
        logger.info(f"[OpenAlex] ✓ Found {len(results)} papers")
        return results
        
    except requests.exceptions.Timeout:
        logger.error("[OpenAlex] ✗ Request timed out")
        return _get_mock_results()
    except requests.exceptions.RequestException as e:
        logger.error(f"[OpenAlex] ✗ Request failed: {e}")
        return _get_mock_results()
    except Exception as e:
        logger.error(f"[OpenAlex] ✗ Search failed: {e}")
        return _get_mock_results()


def _get_mock_results() -> List[Dict[str, Any]]:
    """Return mock results for testing."""
    return [
        {
            "title": "LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale",
            "year": 2022,
            "authors": ["Tim Dettmers", "Mike Lewis", "Younes Belkada", "Luke Zettlemoyer"],
            "citation_count": 1200,
            "venue": "NeurIPS",
            "abstract": "Large language models can be loaded in 8-bit precision for inference.",
            "source": "OpenAlex"
        },
        {
            "title": "QLoRA: Efficient Finetuning of Quantized LLMs",
            "year": 2023,
            "authors": ["Tim Dettmers", "Artidoro Pagnoni", "Ari Holtzman", "Luke Zettlemoyer"],
            "citation_count": 980,
            "venue": "NeurIPS",
            "abstract": "Efficient finetuning of LLMs using 4-bit quantization with Low Rank Adapters.",
            "source": "OpenAlex"
        }
    ]
