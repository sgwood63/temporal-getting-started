# temporal-getting-started

AI application using Temporal Cloud with the [temporal-ai-agent](https://github.com/temporal-community/temporal-ai-agent).

## Project Structure

```
.
├── .venv/                  # Python virtual environment (Python 3.13.2)
├── temporal-ai-agent/      # Cloned AI agent application
│   ├── .env                # Local config (not committed — fill in your keys)
│   ├── .env.example        # Template for .env
│   ├── main.py             # FastAPI server (port 8000)
│   ├── scripts/
│   │   └── run_worker.py   # Temporal worker
│   └── frontend/           # Vite frontend (port 5173)
├── CLAUDE.md               # This file
├── HISTORY.md              # Dev log
└── getting-started.md      # Original setup instructions
```

## Prerequisites

- Python 3.10+
- [Temporal CLI](https://docs.temporal.io/cli) (`brew install temporal`)
- [uv](https://docs.astral.sh/uv/) (`brew install uv`)

## Setup

1. **Python venv** (for Temporal SDK scripts):
   ```bash
   source .venv/bin/activate
   ```

2. **temporal-ai-agent dependencies** (managed by uv):
   ```bash
   cd temporal-ai-agent && uv sync
   ```

3. **Fill in your credentials** in `temporal-ai-agent/.env`:
   - `LLM_KEY` — OpenAI API key
   - `TEMPORAL_ADDRESS` — e.g. `my-namespace.acct.tmprl.cloud:7233`
   - `TEMPORAL_NAMESPACE` — your Temporal Cloud namespace
   - `TEMPORAL_API_KEY` — Temporal Cloud API key

## Running the Agent

Open three terminals from the `temporal-ai-agent/` directory:

```bash
# Terminal 1 — Worker
uv run scripts/run_worker.py

# Terminal 2 — API server
uv run main.py

# Terminal 3 — Frontend
cd frontend && npm run dev
```

Access the UI at http://localhost:5173

## Temporal CLI

```bash
# Check server connection
temporal namespace describe --namespace <your-namespace> \
  --address <your-namespace>.tmprl.cloud:7233 \
  --api-key <your-api-key>
```

## Dev Log

See [HISTORY.md](HISTORY.md) for a running log of all changes.
