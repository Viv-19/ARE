# API Reference

The ARE backend is built with **FastAPI** and provides REST endpoints alongside Server-Sent Events (SSE) for real-time frontend integration.

## Base URL
`http://localhost:8000`

---

## Endpoints

### 1. Start Research Session
`POST /api/research`

Initializes a new LangGraph state machine flow.

**Request Body**:
```json
{
  "question": "Your research topic here",
  "execution_mode": "dry_run",
  "random_seed": 42
}
```

**Response**:
```json
{
  "session_id": "a1b2c3d4e5f6",
  "status": "started"
}
```

---

### 2. Stream Events (SSE)
`GET /api/events/{session_id}`

Provides real-time Server-Sent Events showing the step-by-step reasoning and phase transitions.

**Event Types**:
- `start`: Research initiated.
- `node_reasoning`: LLM internal thought process.
- `node_complete`: A graph node has finished processing.
- `hitl_required`: The workflow is paused, waiting for human input.
- `hitl_resolved`: Human decision submitted.
- `experiment_code_generated`: NODE-5 generated a code artifact.
- `error`: Execution failed.
- `complete`: Research process finished entirely.

---

### 3. Check Status
`GET /api/status/{session_id}`

Polling endpoint for the current state of a graph run.

**Response**:
```json
{
  "session_id": "a1b2c3d4e5f6",
  "status": "running",
  "current_node": "node_4",
  "hitl_pending": true
}
```

---

### 4. Provide Human Input (HITL)
`POST /api/approve/{session_id}`

Allows the user to resume the graph when it is paused at `NODE-0 Confirm`, `NODE-4`, or `NODE-7`.

**Request Body**:
```json
{
  "action": "approve",
  "feedback": "Optional notes from user"
}
```

Supported actions: `approve`, `reject`, `refine`, `clarify`, `continue`, `stop`

---

### 5. Fetch Final Report
`GET /api/report/{session_id}`

Retrieves the generated Markdown and JSON reports once the session status is `completed`.

**Response**:
```json
{
  "verdict": "conclusive",
  "confidence": 0.85,
  "markdown": "# Research Report...",
  "json": {}
}
```

---

### 6. Health Check
`GET /api/health`

Returns system health, active LLM provider, and configured search adapters.

```json
{
  "status": "healthy",
  "llm": "Groq (llama-3.3-70b-versatile)",
  "search_adapters": ["SemanticScholar", "ArXiv"]
}
```
