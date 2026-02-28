"""
ArXiv API adapter for academic paper search.
Uses the arxiv library for real paper retrieval.
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def search(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Perform a metadata-only academic search on ArXiv.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        
    Returns:
        List of paper metadata dictionaries
    """
    from . import USE_MOCK
    
    if USE_MOCK:
        logger.info(f"[ArXiv] Using mock data for query: {query[:50]}...")
        return _get_mock_results()
    
    logger.info(f"[ArXiv] Searching for: {query[:50]}...")
    
    try:
        import arxiv
        
        # Create search client
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        results = []
        for paper in client.results(search):
            results.append({
                "title": paper.title,
                "year": paper.published.year if paper.published else 2024,
                "authors": [author.name for author in paper.authors][:5],  # First 5 authors
                "citation_count": 0,  # ArXiv doesn't provide citation counts
                "venue": "arXiv",
                "abstract": paper.summary[:500] if paper.summary else "",
                "url": paper.entry_id,
                "pdf_url": paper.pdf_url,
                "categories": paper.categories,
                "source": "ArXiv"
            })
        
        logger.info(f"[ArXiv] ✓ Found {len(results)} papers")
        return results
        
    except ImportError:
        logger.error("[ArXiv] ✗ arxiv library not installed. Run: pip install arxiv")
        return _get_mock_results()
    except Exception as e:
        logger.error(f"[ArXiv] ✗ Search failed: {e}")
        return _get_mock_results()


def _get_mock_results() -> List[Dict[str, Any]]:
    """Return mock results for testing."""
    return [
        {
            "title": "A Survey on Model Quantization for Deep Neural Networks",
            "year": 2023,
            "authors": ["Author A", "Author B"],
            "citation_count": 250,
            "venue": "arXiv",
            "abstract": "Comprehensive survey on quantization techniques for neural networks including INT8 and INT4 approaches.",
            "source": "ArXiv"
        },
        {
            "title": "Low-bit Quantization of Large Language Models",
            "year": 2024,
            "authors": ["Author C", "Author D"],
            "citation_count": 85,
            "venue": "arXiv",
            "abstract": "Analysis of sub-8-bit quantization effects on transformer inference quality and latency.",
            "source": "ArXiv"
        },
        {
            "title": "Residual Stream Stability in Quantized Transformers",
            "year": 2024,
            "authors": ["Author E", "Author F"],
            "citation_count": 45,
            "venue": "NeurIPS",
            "abstract": "Investigating numerical stability of residual streams under aggressive quantization.",
            "source": "ArXiv"
        }
    ]
