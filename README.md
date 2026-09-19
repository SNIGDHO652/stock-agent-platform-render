# Stock Agent Platform — Render Free Edition

A free-tier-friendly agentic stock research backend. Users submit a company name; the API resolves the ticker, collects market data, runs deterministic analytics, generates short/medium/long-term ratings, and optionally uses CrewAI for narrative synthesis.

> Educational research only. Ratings and forecasts are not personalised investment advice and do not guarantee future performance.


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

