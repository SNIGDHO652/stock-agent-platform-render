# Render Deployment — Free UI Version

This version is designed for Render free-tier demos without Celery or Redis.

## Resources

The Blueprint creates:

```text
stock-agent-api-free   FastAPI web service
stock-agent-db-free    PostgreSQL database
```

## What changed for security

The browser UI does **not** ask users to paste `API_KEY`.

```text
Browser → /web/* → server-side code
```

The protected API remains available:

```text
External client → /v1/* → requires X-API-Key
```

Do not put `API_KEY` or `OPENAI_API_KEY` in frontend JavaScript.

## Deploy

1. Push this folder as your GitHub repo root.
2. In Render, choose **New → Blueprint**.
3. Select the repo.
4. Render detects `render.yaml`.
5. Enter `OPENAI_API_KEY` if you want CrewAI LLM summaries.
6. Deploy.

## Use the app

Open:

```text
https://YOUR-APP.onrender.com/
```

or:

```text
https://YOUR-APP.onrender.com/app
```

Users only enter:

```text
Company name or ticker
Forecast horizons
AI narrative checkbox
```

No backend API key is needed in the browser.

## API docs

```text
https://YOUR-APP.onrender.com/docs
```

For `/v1/*` API calls, use the generated `API_KEY` from:

```text
Render Dashboard → stock-agent-api-free → Environment → API_KEY
```

Example external API call:

```bash
curl -H "X-API-Key: YOUR_RENDER_API_KEY" \
  "https://YOUR-APP.onrender.com/v1/companies/search?q=Microsoft"
```

## Startup command fix

Render Docker services now call:

```text
sh ./scripts/start-render.sh
```

The script runs:

```text
alembic upgrade head
fastapi run app/main.py --host 0.0.0.0 --port "$PORT"
```

This avoids Render treating a long inline `alembic ... && fastapi ...` string as a single executable.
