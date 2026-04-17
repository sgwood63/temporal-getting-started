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
