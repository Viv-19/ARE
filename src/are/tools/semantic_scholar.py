"""
Semantic Scholar API adapter for academic paper search.
Uses the Semantic Scholar API for paper metadata with citation counts.
"""

from typing import List, Dict, Any
import logging
import requests

logger = logging.getLogger(__name__)

SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"

def search(query: str, max_results: int = 10) -> tuple[List[Dict[str, Any]], bool]:
    """
    Perform a metadata-only academic search on Semantic Scholar.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        
    Returns:
        tuple: (List of paper metadata dictionaries, is_rate_limited boolean)
    """
    from . import USE_MOCK
    from ..config import SEMANTIC_SCHOLAR_API_KEY
    
    if USE_MOCK:
        logger.info(f"[SemanticScholar] Using mock data for query: {query[:50]}...")
        return _get_mock_results(), False
    
    logger.info(f"[SemanticScholar] Searching for: {query[:50]}...")
    
    try:
        headers = {}
        if SEMANTIC_SCHOLAR_API_KEY:
            headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY
            logger.info("[SemanticScholar] Using API key for authenticated request")
        
        response = requests.get(
            f"{SEMANTIC_SCHOLAR_API}/paper/search",
            params={
                "query": query,
                "limit": max_results,
                "fields": "title,year,authors,citationCount,venue,abstract,url"
            },
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 429:
            logger.warning("[SemanticScholar] Rate limited. Using mock results.")
            return _get_mock_results(), True
        
        response.raise_for_status()
        data = response.json()
        
        results = []
        for paper in data.get("data", []):
            authors = paper.get("authors", [])
            author_names = [a.get("name", "Unknown") for a in authors][:5]
            
            results.append({
                "title": paper.get("title", "Untitled"),
                "year": paper.get("year", 2024),
                "authors": author_names,
                "citation_count": paper.get("citationCount", 0),
                "venue": paper.get("venue", "Unknown"),
                "abstract": (paper.get("abstract") or "")[:500],
                "url": paper.get("url", ""),
                "source": "SemanticScholar"
            })
        
        logger.info(f"[SemanticScholar] ✓ Found {len(results)} papers")
        return results, False
        
    except requests.exceptions.Timeout:
        logger.error("[SemanticScholar] ✗ Request timed out")
        return _get_mock_results(), False
    except requests.exceptions.RequestException as e:
        logger.error(f"[SemanticScholar] ✗ Request failed: {e}")
        return _get_mock_results(), False
    except Exception as e:
        logger.error(f"[SemanticScholar] ✗ Search failed: {e}")
        return _get_mock_results(), False


def _get_mock_results() -> List[Dict[str, Any]]:
    """Return mock results for testing."""
    return [
        {
            "title": "GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers",
            "year": 2023,
            "authors": ["Elias Frantar", "Saleh Ashkboos", "Torsten Hoefler", "Dan Alistarh"],
            "citation_count": 850,
            "venue": "ICLR",
            "abstract": "We present GPTQ, a new one-shot weight quantization method based on approximate second-order information.",
            "source": "SemanticScholar"
        },
        {
            "title": "AWQ: Activation-aware Weight Quantization for LLM Compression",
            "year": 2024,
            "authors": ["Ji Lin", "Jiaming Tang", "Haotian Tang", "Song Han"],
            "citation_count": 420,
            "venue": "MLSys",
            "abstract": "We propose Activation-aware Weight Quantization (AWQ) for low-bit weight-only quantization.",
            "source": "SemanticScholar"
        },
        {
            "title": "SmoothQuant: Accurate and Efficient Post-Training Quantization",
            "year": 2023,
            "authors": ["Guangxuan Xiao", "Ji Lin", "Song Han"],
            "citation_count": 580,
            "venue": "ICML",
            "abstract": "SmoothQuant enables 8-bit weight and activation quantization for LLMs without accuracy loss.",
            "source": "SemanticScholar"
        }
    ]
