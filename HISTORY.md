# Dev Log

---

## 2026-04-17 — Initial project setup

**Asked:** Set up an AI application using Temporal Cloud based on `getting-started.md`.

**Decisions:**
- Used `sgwood63/temporal-getting-started` as the GitHub repo (authenticated account).
- Temporal Cloud with API key authentication (not mTLS).
- OpenAI (`gpt-4o`) as the LLM provider via temporal-ai-agent's LiteLLM abstraction.
- Used `uv` to manage temporal-ai-agent dependencies (project's native tooling).
- Created a standard Python `venv` at `.venv/` for the Temporal SDK and top-level scripts.

**Files created/affected:**
- `.venv/` — Python 3.13.2 virtual environment with `temporalio 1.26.0`
- `temporal-ai-agent/` — cloned from `temporal-community/temporal-ai-agent`, dependencies installed via `uv sync`
- `temporal-ai-agent/.env` — config with placeholders for `LLM_KEY`, `TEMPORAL_ADDRESS`, `TEMPORAL_NAMESPACE`, `TEMPORAL_API_KEY`
- `CLAUDE.md` — project documentation and run instructions
- `HISTORY.md` — this file
- `.gitignore` — excludes `.venv/`, `.env` files, `__pycache__`, etc.
- GitHub repo created: `sgwood63/temporal-getting-started` (public)

**Tools installed:**
- Temporal CLI 1.6.2 (via `brew install temporal`)
- uv (via `brew install uv`)

---

## 2026-04-17 — LLM model updates

**Asked:** Find the current best OpenAI model and update the config.

**Decisions:**
- Upgraded from `openai/gpt-4o` → `openai/gpt-5.4-mini-2026-03-17` (faster, cheaper) → then to `openai/gpt-5.4-2026-03-05` (flagship, user switched back manually).
- Model selection informed by web search against OpenAI docs as of April 2026.

**Files affected:**
- `temporal-ai-agent/.env` — `LLM_MODEL` updated

---

## 2026-04-17 — App launch

**Asked:** Launch the app.

**Decisions:**
- Frontend npm deps were not yet installed; ran `npm install` in `temporal-ai-agent/frontend/`.
- API server (`api/main.py`) requires uvicorn explicitly — `uv run python api/main.py` exits silently; correct invocation is `uv run uvicorn api.main:app`.
- Worker and frontend launched via `uv run` and `npm run dev` respectively.

**Files affected:**
- `temporal-ai-agent/frontend/node_modules/` — npm deps installed

---

## 2026-04-17 — Bug fix: ValidationResult crash on double-encoded LLM response

**Asked:** Investigate crash when switching to a different travel task.

**Root cause:** When the user asked to switch goals, the LLM returned `validationFailedReason` as a double-encoded JSON string instead of a dict. The Temporal data converter expected `dict` for `ValidationResult.validationFailedReason` and threw `Failed decoding arguments`.

**Decision:** Defensively parse `validationFailedReason` in the activity — if the LLM returns it as a string, `json.loads()` it before constructing `ValidationResult`. Falls back to wrapping it in `{"response": ...}` if parsing fails.

**Files affected:**
- `temporal-ai-agent/activities/tool_activities.py` — lines 106–114, `agent_validatePrompt`

---

## 2026-04-17 — App launch + crash fixes (this session)

**Asked:** Launch the app; then fix "chat ended" on load and worker crash.

**Issues found and fixed:**

1. **CLAUDE.md had wrong API command** — `uv run main.py` doesn't work; correct command is `uv run uvicorn api.main:app --reload`. Updated CLAUDE.md.

2. **CORS blocked frontend on port 5174** — `allow_origins` was hardcoded to `localhost:5173`; Vite picked `5174` because `5173` was already in use. Added `5174` to the allowed origins list.

3. **"Workflow Task in failed state" returned 500** — `get_conversation_history` only checked TERMINATED/CANCELED/FAILED workflow statuses, but a workflow with a failed *task* (still technically Running) caused a `TemporalError` that fell through to the `else` 500 branch. Added an explicit check for `"workflow task in failed state"` in the error message to return `[]` instead.

4. **`ValidationResult.validationFailedReason` type mismatch crashed the worker** — The LLM had previously returned `validationFailedReason` as a JSON string; Temporal stored it as a string in event history, but the dataclass annotation was `dict`, causing `Failed decoding arguments` on replay. Fixed by changing the annotation to `Optional[Union[dict, str]]` and normalizing to dict in `__post_init__`. Also terminated the stale failed workflow run in Temporal Cloud.

**Files affected:**
- `CLAUDE.md` — corrected API run command and file path
- `temporal-ai-agent/api/main.py` — CORS origins, "workflow task in failed state" error handling
- `temporal-ai-agent/models/data_types.py` — `ValidationResult.validationFailedReason` type + normalization

---

## 2026-04-17 — Switch to multi-agent mode

**Asked:** (User updated `.env` directly) Switched `AGENT_GOAL` from `goal_event_flight_invoice` to `goal_choose_agent_type` to enable multi-agent mode and allow goals beyond Australia/NZ event search.

---

## 2026-04-17 — Make SILLY_MODE configurable via .env

**Asked:** Move SILLY_MODE from a hardcoded value in agent_selection.py to an environment variable.

**Change:** Replaced `SILLY_MODE = "off"` with `SILLY_MODE = os.getenv("SILLY_MODE", "off")`. No dotenv import needed — `shared/config.py` already calls `load_dotenv()` before this module is imported.

**Files affected:**
- `temporal-ai-agent/goals/agent_selection.py` — reads SILLY_MODE from env
- `temporal-ai-agent/.env.example` — added SILLY_MODE comment with examples

---

## 2026-04-17 — Add End Chat button and fix new chat flow

**Asked:** Add an End Chat button (top and bottom of UI); fix "Start New Chat" not re-enabling the chat input.

**Changes:**
- Added `endChat()` to `api.js` — POSTs to `/end-chat`
- Added End Chat button at top of page (visible only when chat active) and bottom-left of input bar
- Fixed `fetchConversationHistory`: empty conversation no longer forces `done=true` — respects `workflow_done` flag instead, so the input stays enabled while a new workflow is starting up
- API `get-conversation-history`: added `COMPLETED` to inactive states and returns `workflow_done: true` in the JSON response so the frontend knows the workflow finished

**Files affected:**
- `temporal-ai-agent/frontend/src/services/api.js` — added `endChat()`
- `temporal-ai-agent/frontend/src/pages/App.jsx` — End Chat buttons, `handleEndChat`, `done` state fix
- `temporal-ai-agent/api/main.py` — `workflow_done` flag in conversation history response; CORS origin added for port 5175

---

## 2026-04-17 — Fix LLM returning duplicate JSON / worker crash loop

**Asked:** UI hung after running ListAgents; worker was stuck retrying at attempt 40+.

**Root cause:** With `SILLY_MODE="a pirate"`, the LLM (gpt-5.4-2026-03-05) consistently returned the JSON response body twice, separated by a newline. `json.loads()` raised `JSONDecodeError: Extra data` on every attempt, causing infinite retries.

**Fix:** `parse_json_response` now falls back to `json.JSONDecoder().raw_decode()` which parses the first complete JSON object and ignores any trailing content (pirate commentary, duplicate JSON, etc.).

**Files affected:**
- `temporal-ai-agent/activities/tool_activities.py` — `parse_json_response` fallback to `raw_decode`

---

## 2026-04-22 — Migrate agent planning logic to LangGraph (branch: langgraph-switch)

**Asked:** Replace the custom LLM orchestration inside the agent with a popular framework while keeping Temporal as the workflow engine.

**Decision:** Adopted [LangGraph](https://langchain-ai.github.io/langgraph/) with [langchain-litellm](https://pypi.org/project/langchain-litellm/) for the planning layer. LangGraph's `with_structured_output` replaces manual `litellm.completion()` + JSON sanitization/parsing. Temporal still controls the outer conversation loop, durability, signals, and tool execution.

**Architecture:**
- `activities/langgraph_agent.py` (new) — two single-step LangGraph `StateGraph`s:
  - `get_planner_graph()` — uses `ChatLiteLLM.with_structured_output(ToolPlannerOutput)` to produce `{response, next, tool, args}` dicts
  - `get_validation_graph()` — uses `ChatLiteLLM.with_structured_output(ValidationOutput)` to produce `{validationResult, validationFailedReason}`
- Both graphs are lazily compiled singletons (safe for Temporal's determinism requirement — graphs compile once at module load, only `invoke` has side effects)
- `agent_validatePrompt` no longer calls `agent_toolPlanner` internally; it uses its own dedicated validation graph
- Removed `sanitize_json_response`, `parse_json_response`, and the `litellm.completion` import from `tool_activities.py`
- Workflow (`agent_goal_workflow.py`) and all tools (`tools/`) are unchanged
- LiteLLM multi-provider support preserved — `LLM_MODEL` env var still controls the provider

**New dependencies (added to `pyproject.toml`):**
- `langgraph>=0.2.0,<0.3`
- `langchain-core>=0.3.0,<0.4`
- `langchain-litellm>=0.1.0,<0.2`

**Tests:** All 40 tests pass. Updated `tests/test_tool_activities.py` to mock `get_planner_graph` / `get_validation_graph` instead of `litellm.completion`. Removed tests for the deleted `sanitize_json_response` / `parse_json_response` helpers; replaced with Pydantic model tests.

**Files created:**
- `temporal-ai-agent/activities/langgraph_agent.py`

**Files modified:**
- `temporal-ai-agent/pyproject.toml` — added three new dependencies
- `temporal-ai-agent/activities/tool_activities.py` — replaced agent planning internals
- `temporal-ai-agent/tests/test_tool_activities.py` — updated mocks, added LangGraph tests
- `CLAUDE.md` — updated project description and structure
- `temporal-ai-agent/.env` — `TEMPORAL_TASK_QUEUE` updated to `langgraph-agent-task-queue`
- `temporal-ai-agent/.env.example` — `TEMPORAL_TASK_QUEUE` example updated to match
- `temporal-ai-agent/README.md` — added LangGraph description
- `temporal-ai-agent/docs/architecture.md` — added LangGraph section under Activities
- `temporal-ai-agent/docs/architecture-decisions.md` — added LangGraph decision rationale
- `temporal-ai-agent/docs/setup.md` — updated default task queue name
- `temporal-ai-agent/docs/testing.md` — updated test names and mocking descriptions
- `temporal-ai-agent/tests/README.md` — updated mocking example to use LangGraph pattern
- `temporal-ai-agent/docs/langgraph-switch.md` — implementation plan saved to docs

---

## 2026-04-22 — Fix `tool_choice='any'` crash with OpenAI provider prefix

**Asked:** App wasn't responding to user input after LangGraph switch.

**Root cause:** `langchain_core.BaseChatModel.with_structured_output()` hardcodes `tool_choice="any"` when calling `bind_tools`. `langchain-litellm` converts `"any"` → `"required"` for models in its `_OPENAI_MODELS` list — but that list only contains bare model names (e.g. `gpt-4o`), not models specified with the `openai/` provider prefix (e.g. `openai/gpt-5.4-2026-03-05`). OpenAI rejects `tool_choice="any"` with a `BadRequestError`.

**Fix:** Replaced `with_structured_output()` calls with a `_structured_output()` helper that calls `bind_tools([schema], tool_choice="required")` directly and pipes through `PydanticToolsParser`. Works for any model name format.

**Files affected:**
- `temporal-ai-agent/activities/langgraph_agent.py` — added `_structured_output()` helper; replaced both `with_structured_output()` calls
- `temporal-ai-agent/docs/architecture.md` — updated LangGraph description to reflect `bind_tools` usage
- `temporal-ai-agent/docs/architecture-decisions.md` — documented the `with_structured_output` limitation and fix
- `temporal-ai-agent/docs/langgraph-switch.md` — added "Why `bind_tools`" section to Actual Implementation

---

## 2026-04-23 — Pass conversation history as LangChain message objects

**Asked:** Instead of JSON-dumping conversation history into the SystemMessage, convert it to proper LangChain `HumanMessage`/`AIMessage` objects and pass them in the messages list, keeping the system prompt for instructions only.

**Decisions:**
- Temporal's `ConversationHistory` dict format is unchanged (persisted in workflow state, returned to UI).
- Conversion happens in the activity layer via a new utility `prompts/history_converter.py`.
- Actor mapping: `"user"` → `HumanMessage`, `"agent"` → `AIMessage` (text extracted from dict if applicable), `"tool_result"` → `HumanMessage` prefixed `[Tool result]`, `"user_confirmed_tool_run"` → `HumanMessage` prefixed `[Confirmed tool run]`, `"conversation_summary"` → extracted as plain text for injection into the system prompt.
- `generate_genai_prompt` no longer takes `conversation_history`; instead accepts optional `conversation_summary` to embed prior-session context in the system prompt.
- `ToolPromptInput` gains an optional `conversation_history` field so the planner activity can access it.
- Both `agent_toolPlanner` and `agent_validatePrompt` now build: `[SystemMessage] + history_messages + [HumanMessage(prompt)]`.
- 21/21 tests pass.

**Files affected:**
- `temporal-ai-agent/prompts/history_converter.py` — new file; `convert_history_to_messages()` utility
- `temporal-ai-agent/models/data_types.py` — added `conversation_history: Optional[ConversationHistory]` to `ToolPromptInput`
- `temporal-ai-agent/prompts/agent_prompt_generators.py` — removed history JSON embedding; added `conversation_summary` param
- `temporal-ai-agent/activities/tool_activities.py` — both activities use `convert_history_to_messages` and expand into graph messages list
- `temporal-ai-agent/workflows/agent_goal_workflow.py` — updated `generate_genai_prompt` call and `ToolPromptInput` construction
- `temporal-ai-agent/tests/test_tool_activities.py` — added `test_agent_toolPlanner_injects_history_messages`

---

## 2026-04-23 — Update documentation for multi-turn message format change

**Asked:** Update docs to reflect the conversation history → LangChain messages change.

**Files affected:**
- `temporal-ai-agent/docs/langgraph-switch.md` — added "Conversation History as LangChain Messages" section; annotated the outdated "no changes to data models" claim
- `temporal-ai-agent/docs/architecture.md` — extended LangGraph section with message list structure
- `temporal-ai-agent/docs/architecture-decisions.md` — added "Conversation History as LangChain Message Objects" decision entry

---

## 2026-04-23 — Update temporal-ai-agent README with current setup and run docs

**Asked:** Update the ai-agent level README with current setup and run documentation.

**Changes:**
- Updated LangGraph description to mention `bind_tools` + `PydanticToolsParser` and the multi-turn history message format
- Replaced sparse "Setup and Configuration" section with a proper quick-start: prerequisites, `.env` config, `uv sync`, and the three run commands (worker / API / frontend)
- Replaced stale "Development" section link text

**Files affected:**
- `temporal-ai-agent/README.md`
