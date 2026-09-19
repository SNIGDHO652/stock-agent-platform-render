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
