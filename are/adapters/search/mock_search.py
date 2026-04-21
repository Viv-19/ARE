"""
Mock Search Adapter — deterministic paper results for testing.
"""

from __future__ import annotations

from are.ports.search_port import PaperResult, SearchPort, SearchResponse


_MOCK_PAPERS = [
    PaperResult(
        title="GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers",
        year=2023, authors=["Elias Frantar", "Saleh Ashkboos"], citation_count=850,
        venue="ICLR", abstract="One-shot weight quantization based on approximate second-order information.",
        source="Mock",
    ),
    PaperResult(
        title="AWQ: Activation-aware Weight Quantization for LLM Compression",
        year=2024, authors=["Ji Lin", "Jiaming Tang", "Song Han"], citation_count=420,
        venue="MLSys", abstract="Activation-aware weight quantization for low-bit weight-only quantization.",
        source="Mock",
    ),
    PaperResult(
        title="SmoothQuant: Accurate and Efficient Post-Training Quantization",
        year=2023, authors=["Guangxuan Xiao", "Ji Lin"], citation_count=580,
        venue="ICML", abstract="8-bit weight and activation quantization for LLMs without accuracy loss.",
        source="Mock",
    ),
    PaperResult(
        title="LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale",
        year=2022, authors=["Tim Dettmers", "Mike Lewis"], citation_count=1200,
        venue="NeurIPS", abstract="Large language models loaded in 8-bit precision for inference.",
        source="Mock",
    ),
    PaperResult(
        title="QLoRA: Efficient Finetuning of Quantized LLMs",
        year=2023, authors=["Tim Dettmers", "Artidoro Pagnoni"], citation_count=980,
        venue="NeurIPS", abstract="Efficient finetuning using 4-bit quantization with Low Rank Adapters.",
        source="Mock",
    ),
]


class MockSearchAdapter(SearchPort):
    """Returns pre-built paper data for offline testing."""

    def search(self, query: str, *, max_results: int = 10) -> SearchResponse:
        return SearchResponse(papers=list(_MOCK_PAPERS[:max_results]))

    @property
    def source_name(self) -> str:
        return "Mock"
