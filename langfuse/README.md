# Langfuse Local Deployment

Runs Langfuse v2 locally via Docker Compose. Once running, you can point the temporal-ai-agent at it to trace every LLM call made during planning and validation.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker + Compose plugin)

## Setup

**1. Create your `.env` file**

```bash
cp .env.example .env
```

**2. Fill in the three required secrets in `langfuse/.env`**

| Variable | How to generate |
|---|---|
| `NEXTAUTH_SECRET` | `openssl rand -base64 32` |
| `SALT` | `openssl rand -base64 32` |
| `POSTGRES_PASSWORD` | Any strong password |

**3. Start the stack**

```bash
docker compose up -d
```

**4. Create your account**

Open http://localhost:3000, click **Sign up**, and create an account. Then create a new **Project**.

**5. Get your API keys**

Inside the project, go to **Settings → API Keys** and create a key pair. Copy the public and secret keys.

**6. Add the keys to the agent**

In `temporal-ai-agent/.env`:

```
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000
```

Restart the worker (`uv run scripts/run_worker.py`) and send a prompt. Traces will appear in the Langfuse UI under **Traces**, grouped by Temporal workflow ID as the session.

## Stopping

```bash
docker compose down        # stop containers, keep DB volume
docker compose down -v     # stop and delete all data
```
