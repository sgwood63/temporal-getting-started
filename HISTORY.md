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
