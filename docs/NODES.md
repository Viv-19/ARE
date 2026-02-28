# Node Reference Guide

The ARE system consists of 9 distinct nodes (0 through 8), each responsible for a specific cognitive or orchestration task within the research lifecycle.

---

## NODE-0: Research Question Intake
**Role**: Intake and Normalization
**Purpose**: Parses the initial user query, bounds the scope, and identifies the core intent (e.g., exploratory, comparison).
**Outputs to State**:
- `normalized_question`
- `research_intent`
- `variables` (independent, dependent, control)
- `intent_confidence`
- `clarification_needed`
**Conditional Logic**: If `intent_confidence` < 0.7, halts and prompts for clarification (via `NODE-0 Confirm`).

---

## NODE-1: Knowledge Assessment / Router
**Role**: Epistemic Router
**Purpose**: Determines if the question is already `well-studied`, `partial`, or entirely `novel` to decide whether empirical research is needed.
**Outputs to State**:
- `research_status`
- `evidence_required`
- `reasoning_summary`
**Conditional Logic**: If `well-studied`, routes directly to **NODE-8** (Report generation). Otherwise, loops to **NODE-2**.

---

## NODE-2: Evidence Collection
**Role**: Academic Grounding
**Purpose**: Collects verified academic metadata and identifies knowledge gaps to legally ground the research.
**Outputs to State**:
- `search_queries`
- `evidence` (paper metadata)
- `knowledge_gaps`

---

## NODE-3: Research Contract / Orchestration
**Role**: Planner
**Purpose**: Synthesizes knowledge gaps into a formal "Research Contract" consisting of hypotheses, metrics, and executable tasks.
**Outputs to State**:
- `research_contract`

---

## NODE-4: Human Approval (HITL-1)
**Role**: Governance Guardrail
**Purpose**: Pauses execution to await human approval of the proposed research contract. Ensures alignment and cost validation.
**Outputs to State**:
- `human_decisions`
**Conditional Logic**: Routes to **NODE-5** upon approval, or back to **NODE-3** for refinement if rejected.

---

## NODE-5: Worker / Execution Controller
**Role**: Code Generator and Executor
**Purpose**: Generates experiment code and coordinates execution. Collects runtime metrics and artifacts. Hand-offs execution to the user (via API) if local execution constraints require it.
**Outputs to State**:
- `execution_status`
- `execution_logs`
- `artifacts`

---

## NODE-6: Critic / Scientific Review
**Role**: Evaluator
**Purpose**: Cross-references experiment logs (`execution_logs`) against the established hypotheses (`research_contract`) to determine the scientific validity of the results.
**Outputs to State**:
- `verdict` (`conclusive`, `inconclusive`, `contradictory`)
- `confidence`
- `hypothesis_evaluation`
**Conditional Logic**: If `conclusive`, routes to **NODE-8**. If `inconclusive`, routes to **NODE-7** (HITL-2) for review.

---

## NODE-7: Human–Critic Loop (HITL-2)
**Role**: Post-Execution Human Oversight
**Purpose**: Halts the system after an inconclusive execution, allowing the user to decide whether to iterate (`continue` to NODE-5) or terminate early (`finish` to NODE-8).
**Outputs to State**:
- `loop_decision`
- `human_decisions`

---

## NODE-8: Reducer & Report Generator
**Role**: Synthesizer
**Purpose**: Takes all accumulated state data and writes a formal, markdown-based scientific report, concluding the research session.
**Outputs to State**:
- `report_markdown`
- `report_json`
