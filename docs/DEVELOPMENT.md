# Development Guide

Welcome to the ARE contributor guide. This document outlines how to set up the project locally for development and testing.

## Prerequisites
- Python 3.10+
- Node.js (Optional, for frontend tooling if added later)
- An active API key for Gemini (if `USE_GEMINI=True` in config).

## Environment Setup

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd ARE
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Ensure you have `langchain`, `langgraph`, `fastapi`, and `uvicorn` installed).*

4. **Configuration (`.env`):**
   Copy `.env.example` to `.env` and fill in your keys:
   ```env
   GEMINI_API_KEY=your_api_key_here
   DEBUG_MODE=True
   ```
   You can verify your configuration by running `python check_config.py`.

## Running the Application

### Backend Server
Run the FastAPI application with auto-reload enabled:
```bash
uvicorn api:app --reload --port 8000
```
Then navigate to `http://localhost:8000`.

### CLI Interface
You can bypass the frontend entirely and run a research session directly from the terminal. This is useful for rapid testing of the LangGraph state machine:
```bash
python run.py "What is the optimal batch size for fine-tuning Llama-3.2-3B?"
```

## Testing

ARE uses `pytest` for unit and integration testing. Tests are located in the `tests/` directory.

```bash
# Run all tests
pytest tests/

# Run a specific test file
pytest tests/test_v4_flow.py -v
```

## Code Structure Overview

- `api.py`: FastAPI application, SSE streaming, and route definitions.
- `run.py`: CLI entrypoint for running the LangGraph workflow directly.
- `src/are/graph.py`: The core LangGraph state machine definition.
- `src/are/state.py`: The `TypedDict` defining the shared memory for the graph.
- `src/are/nodes/`: Directory containing the logic for nodes 0 through 8.
- `frontend/`: Static HTML, CSS, and JS files for the web interface. 
