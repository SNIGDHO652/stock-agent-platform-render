# Stock Agent Platform — Render Free Edition

A free-tier-friendly agentic stock research backend. Users submit a company name; the API resolves the ticker, collects market data, runs deterministic analytics, generates short/medium/long-term ratings, and optionally uses CrewAI for narrative synthesis.

This edition removes Celery workers and Redis so it can run on Render free resources:

- One Render web service
- One Render Postgres database
- In-process job runner
- In-memory TTL cache and rate limiter

> Educational research only. Ratings and forecasts are not personalised investment advice and do not guarantee future performance.

## Difference from scalable version

| Area | Scalable version | Free Render version |
|---|---|---|
| Job execution | Celery worker | In-process FastAPI background task |
| Queue/broker | Redis + Celery | None |
| Cache | Redis | Process-local TTL cache |
| Rate limit | Redis counter | Process-local counter |
| Render services | API + worker + Postgres + Key Value | API + Postgres |
| Cost goal | Production-like | Free demo |

## Features

- FastAPI API and OpenAPI docs
- LangGraph workflow
- CrewAI investment committee when `OPENAI_API_KEY` is configured
- Deterministic fallback when no LLM key is configured
- PostgreSQL persistence and Alembic migrations
- Durable job records and progress events
- Server-sent event progress stream
- Prometheus metrics
- API-key protection
- Company discovery and stock data collection
- Technical analysis
- Fundamental analysis
- Forecasting
- News sentiment
- Risk analysis
- Explainable short/medium/long-term ratings

## Free-tier limitations

This version is for demos, portfolios, and interviews.

- Jobs run inside the web process, so heavy requests can consume the web instance.
- Render free web services can spin down when idle, so a running in-process job can be interrupted.
- In-memory cache/rate-limit counters reset on restart.
- Only one job runs at a time per web process to reduce memory pressure.
- For production, use the scalable Celery/Redis worker version.

## Local run

```bash
cp .env.example .env
docker compose up --build
```

Open:

```text
http://localhost:8000/docs
http://localhost:8000/health/ready
```

## Render deploy

See [`RENDER_DEPLOYMENT.md`](RENDER_DEPLOYMENT.md).

## API example

```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "https://stock-agent-api-free.onrender.com/v1/companies/search?q=Microsoft"
```

```bash
curl -X POST "https://stock-agent-api-free.onrender.com/v1/analyses" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Idempotency-Key: microsoft-demo-001" \
  -d '{"company_name":"Microsoft","horizons":[5,20,60],"include_ai_narrative":true}'
```

## Production upgrade path

Move back to the scalable package when you need:

- Reliable long-running jobs
- Multiple workers
- Retry queues
- Redis-backed rate limits and cache
- Horizontal scaling
- Better fault tolerance


## Browser UI

This free Render build includes a lightweight browser UI at:

```text
https://<your-render-service>.onrender.com/
```

Use the Render-generated backend `API_KEY` in the page. Do not paste `OPENAI_API_KEY` into the browser.

Useful paths:

```text
/       Browser UI
/app    Browser UI alias
/docs   Swagger/OpenAPI docs
/health/live
/health/ready
```

## Browser UI without exposing API_KEY

This package includes a polished same-origin browser UI at:

```text
/
```

and:

```text
/app
```

The browser no longer asks for `API_KEY`.

Security model:

```text
Browser UI → /web/* routes → FastAPI server-side analysis code → PostgreSQL
External clients → /v1/* routes → requires X-API-Key
```

`API_KEY` remains a backend-only environment variable used to protect `/v1/*`.
The public browser UI uses `/web/*` helper routes on the same server and never
receives, fetches, stores, or sends the secret API key.

Useful URLs after Render deployment:

```text
https://YOUR-APP.onrender.com/
https://YOUR-APP.onrender.com/app
https://YOUR-APP.onrender.com/docs
https://YOUR-APP.onrender.com/health/live
```

Production hardening suggestion: add user login, CAPTCHA, or per-user quotas before
allowing public users to run expensive analysis jobs.
