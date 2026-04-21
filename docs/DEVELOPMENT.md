# Development Guide

## Prerequisites
- Python 3.10+
- A Groq or Gemini API key for LLM-powered reasoning.

## Environment Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Viv-19/ARE.git
   cd ARE
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -e .
   ```

4. **Configuration (`.env`):**
   Copy `.env.example` to `.env` and fill in your API keys:
   ```bash
   cp .env.example .env
   ```
   Key settings:
   - `LLM_PROVIDER` — `groq`, `gemini`, or `mock`
   - `LLM_API_KEY` — Your API key for the chosen provider
   - `USE_MOCK_SEARCH` — Set to `false` for real Semantic Scholar / ArXiv queries

## Running the Application

### Web Server (FastAPI + Frontend)
```bash
python main.py
```
Then open `http://localhost:8000` in your browser.

### CLI Mode
```bash
python main.py --cli --question "Does INT4 quantization reduce inference latency in 7B LLMs?"
```

## Testing

ARE uses `pytest` with unit and integration test suites:

```bash
# Run full test suite
pytest tests/unit tests/integration -v
```

> Tests use the mock LLM adapter by default — no API keys required.

## Code Structure

```
main.py                     # Application entry point (server or CLI)
are/
├── config/settings.py      # Pydantic Settings (single source of truth)
├── core/
│   ├── graph.py            # LangGraph state machine definition
│   ├── state.py            # GraphState TypedDict
│   ├── nodes/              # Node logic (NODE-0 through NODE-8)
│   └── logic/              # Pure business logic (confidence, dedup, etc.)
├── adapters/
│   ├── llm/                # LLM providers (Groq, Gemini, Mock)
│   └── search/             # Academic search (Semantic Scholar, ArXiv, Mock)
├── ports/                  # Abstract interfaces (LLMPort, SearchPort, etc.)
├── application/            # DI Container + ResearchService
└── interfaces/
    ├── api/app.py          # FastAPI app factory
    └── cli/runner.py       # Interactive CLI runner
frontend/                   # Static HTML/CSS/JS web interface
```
