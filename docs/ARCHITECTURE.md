# ARE Architecture Overview

The Autonomous Research Engineer (ARE) v2 is built on a **Hexagonal Architecture (Ports & Adapters)** combined with a **LangGraph State Machine**. This decoupled design ensures domain logic remains pure and perfectly separate from external integrations (LLMs, Search APIs, databases).

## Architectural Layout (Hexagonal)

The repository strictly decouples business intent from technical implementation:

1. **Core Domain (`are/core/`)**
   - Contains pure business logic without external side effects.
   - `nodes/`: The LangGraph state machine node operations (Node 0 through Node 8). All computational physics, formatting, and prompting happen here.
   - `state.py`: The single-source-of-truth `GraphState` `TypedDict` representing process memory.
   - `graph.py`: The orchestrator that wires nodes together with conditional logic using entirely *pure functions*.

2. **Ports (`are/ports/`)**
   - The interfaces (abstract base classes) that define how the Core Domain interacts with the outside world.
   - E.g., `LLMPort`, `SearchPort`, `AuditPort`.

3. **Adapters (`are/adapters/`)**
   - Concrete implementations of the Ports. They contain third-party SDKs, networking, and filesystem side-effects.
   - E.g., `GeminiAdapter`, `GroqAdapter`, `SemanticScholarAdapter`, `JsonlAuditAdapter`.

4. **Application Container (`are/application/`)**
   - Performs dependency injection. It wires up the chosen Adapters to their respective Ports based on `are/config/settings.py` and abstracts Graph initialization (`ResearchService`).

5. **Interfaces (`are/interfaces/`)**
   - The entry points into the system. These modules never hold business logic.
   - Includes the **FastAPI Application** (`api/app.py`) for frontend consumption and a **CLI Runner** (`cli/runner.py`) for local execution.

---

## LangGraph State Machine Topology

ARE operates as a multi-node, directional control flow. Each Node represents a distinct research worker and is strictly bounded by schema requirements.

```mermaid
graph TD
    Entry([Entry]) --> N0[NODE-0: Intake]
    
    N0 -->|confidence_gate| CG{Confidence Gate}
    CG -->|confirm| N0C[NODE-0 Confirm]
    CG -->|proceed| N1[NODE-1: Router]
    N0C --> N1
    
    N1 -->|research_router| RR{Research Router}
    RR -->|summarize| N8[NODE-8: Report]
    RR -->|research| N2[NODE-2: Evidence]
    
    N2 --> N3[NODE-3: Contract]
    N3 --> N4[NODE-4: HITL-1]
    
    N4 -->|approval_check| AC{Approval}
    AC -->|approve| N5[NODE-5: Execution]
    AC -->|reject/refine| N3
    
    N5 --> N6[NODE-6: Critic]
    
    N6 -->|verdict_router| VR{Verdict}
    VR -->|report| N8
    VR -->|critic| N7[NODE-7: HITL-2]
    
    N7 -->|loop_decision| LD{Loop Check}
    LD -->|continue| N5
    LD -->|finish| N8
    
    N8 --> Exit([Exit])
```

## GraphState Lifecycle

The `GraphState` dictionary is the shared memory pool. Updates traverse through the pipeline appended to the current state.

1. **INTAKE (0)**: Sets `research_question`, `normalized_question`, `intent_confidence`, and structures `variables`.
2. **ROUTER (1)**: Sets `research_status`. Routes "well-studied" paths directly to Reporting (Node 8).
3. **EVIDENCE (2)**: Assigns populated `evidence` JSON metadata and generates missing `knowledge_gaps`.
4. **CONTRACT (3 & 4)**: Frames the `research_contract` and pauses execution to grab `human_decisions` ensuring agentic safety bounds.
5. **EXECUTION (5)**: Produces the computational worker code (`experiment_code`), and binds `execution_logs` and output `artifacts`.
6. **REVIEW (6)**: Calculates a statistical `confidence` metric and asserts the scientific `verdict`.
7. **LOOP (7)**: The reflection gate. If confidence is low or issues were found, suspends to humans to either retry (Looping back to 5) or abort to completion.
8. **REPORTING (8)**: Renders output artifacts `report_markdown` and `report_json`.
