# Autonomous Research Engineer (ARE) 

<div align="center">
  <h3>A Full-Cycle Autonomous Scientific Research Orchestrator</h3>
</div>

<br />

The **Autonomous Research Engineer (ARE)** is an advanced, production-grade agentic workflow system designed to automate scientific research operations. It manages the complete research lifecycle: from intent clarification and literature review to experiment orchestration, human-in-the-loop review, and scientific report generation. 

Built on a clean **Hexagonal Architecture** and orchestrated via a robust **LangGraph State Machine**, ARE ensures execution reliability and domain-safe LLM integrations.

---

## 🌟 Key Features

- **Agentic State Machine Workflow:** Deterministic pipeline execution governed by [LangGraph](https://github.com/langchain-ai/langgraph) (Node-0 Intake → Node-8 Publishing).
- **Human-In-The-Loop (HITL) Guardrails:** Built-in interrupt checkpoints requiring explicit operator approval for research contract generation and reiterative experiment loops.
- **Provider Agnostic (Hexagonal Layout):** Integrates cleanly with **Gemini**, **Groq**, and **Mock Engines** out of the box via heavily decoupled Adapters and Ports. 
- **Academic API Connections:** Fetches and evaluates primary literature metadata securely from Semantic Scholar/ArXiv.
- **Strictly Typed Pipelines:** Uses Pydantic throughout the architecture for schema checking AI JSON outputs and mitigating Hallucinations.
- **Full Transparency:** Real-time logging of "AI reasoning" inside the server via Server-Sent Events (SSE).

---

## 🚀 Quick Start Environment

### 1. Requirements

Ensure you are running:
- **Python 3.10+**
- (Optional) `conda` or standard Python virtual environment

### 2. Setup

Clone and install backend dependencies:

```bash
git clone https://github.com/Viv-19/ARE.git
cd ARE
pip install -e .
```

### 3. Environment Configuration

Copy the sample environment variables:

```bash
cp .env.example .env
```

Review your `.env` file to select an LLM backend (e.g., set `LLM_PROVIDER=groq`), inject your LLM API Keys, and enable/disable `USE_MOCK_SEARCH`.

### 4. Running the System

ARE can be initialized in multiple modes (driven by `main.py`):

**Option A: Startup the REST API & Web Dashboard**
```bash
python main.py
```
> Opening `http://localhost:8000` sets up the real-time React web-application for tracking pipelines and streaming backend responses.

**Option B: CLI Direct Pipeline (No Server)**
```bash
python main.py --cli --question "Does INT4 Quantization significantly degrade context recall in fine-tuned LLMs?"
```

---

## 📚 Repository Architecture

ARE strictly enforces a **Ports and Adapters** layout to keep domain intelligence decoupled from the runtime execution and API calls. For in-depth context on the LangGraph node routing and dependency injection layout, read the comprehensive **[Architecture Overview](docs/ARCHITECTURE.md)**.

```
are/
├── application/         # DI Container mapping Adapters to their Ports.
├── config/              # Centralized environment configs (no nested config files).
├── core/                # The Pure Domain. Contains GraphState, Routing Rules, and the Node logics (Node-0 -> Node-8).
├── adapters/            # External Integrations (LLMs, Search APIs, Storage).
├── ports/               # Interface Definitions governing external limits.
└── interfaces/          # Top-Level Entry Points (FastAPI app & CLI runner).
```

---

## 🧪 Testing

ARE utilizes `pytest` with rigorous unit and integration assertions ensuring deterministic routes hold strong across variable AI behaviors.

To run the complete test suite:
```bash
pytest tests/unit tests/integration
```

> **Note:** Tests make use of `are/adapters/llm/mock_adapter.py` by default so they will not consume any LLM quota or API keys.

---

## 📄 License & Status
This project focuses on research workflow automation through agentic state-machines. It operates autonomously within strict human-in-the-loop limits. Licensed under standard MIT guidelines. 
