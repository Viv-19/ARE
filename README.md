# Autonomous Research Engineer (ARE)


Autonomous Research Engineer (ARE) is a production-grade autonomous research system built with LangChain and LangGraph.

For a detailed deep-dive into the system design, see [System Architecture](system_architecture.md).


## 🚀 Quick Start (Frontend)

The system includes a modern web interface for managing research sessions.

1.  **Install Dependencies**:
    ```bash
    pip install fastapi uvicorn python-multipart
    ```

2.  **Start the Server**:
    ```bash
    uvicorn api:app --reload
    ```

3.  **Access the UI**:
    Open [http://localhost:8000](http://localhost:8000) in your browser.

## 🧪 Quick Start (CLI)

You can also run the system directly from the command line:

```bash
python run.py "Your research question here"
```

## 📖 Detailed Documentation

We have comprehensive documentation available in the `docs/` directory:

- [System Architecture](docs/ARCHITECTURE.md): Deep dive into the LangGraph state machine and core topologies.
- [Node Reference](docs/NODES.md): Detailed responsibilities and I/O for all 9 agents (NODE-0 through NODE-8).
- [API Reference](docs/API.md): Endpoints, SSE streaming, and payload schemas for the FastAPI backend.
- [Development Guide](docs/DEVELOPMENT.md): Setup, testing, and contribution guidelines.

