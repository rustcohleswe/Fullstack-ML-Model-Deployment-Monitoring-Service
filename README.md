# ML Model Monitor

Fullstack feature for deploying and monitoring ML models: **FastAPI** backend, **Next.js (TypeScript)** dashboard, **Supabase (Postgres)** storage, **Docker** packaging. Predictions are simulated (deterministic fake inference).

```
frontend (Next.js :3000) --HTTP--> backend (FastAPI :8000) --supabase-py--> Supabase
                                     routes -> service -> repository (Supabase | in-memory)
```

## Quick start (Docker)

1. Create a Supabase project and run [`supabase/schema.sql`](supabase/schema.sql) in the SQL editor (tables `models`, `prediction_logs`, view `model_metrics`).
2. `cp .env.example .env` and fill `SUPABASE_URL` and `SUPABASE_KEY` (the **service_role** key, backend only).
3. `docker compose up --build`
4. Dashboard: http://localhost:3000 · API docs: http://localhost:8000/docs

> Without `.env`, the backend falls back to a **volatile in-memory store** (logged as a warning) so you can try the UI instantly. Use Supabase for real persistence.

## Run without Docker

```bash
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:create_app --factory --reload --port 8000

# frontend (another terminal)
cd frontend && npm install && npm run dev      # NEXT_PUBLIC_API_URL defaults to http://localhost:8000
```

## API

| Method & path | Purpose |
|---|---|
| `POST /models` | Register `{name, version, model_type, description?}`. 201, `409` if name+version exists, `422` invalid |
| `GET /models?name=&version=` | List models (case-insensitive partial filters) |
| `GET /models/{id}` | One model (`404` if unknown) |
| `POST /models/{id}/predict` | Body `{"features": {...}}` -> simulated `prediction`, `confidence`, `latency_ms`; request+response logged with timestamp |
| `GET /models/{id}/predictions?limit=` | Recent logged predictions |
| `GET /models/{id}/metrics` | `request_count`, `avg_latency_ms`, `avg_confidence`, `last_request_at` |
| `GET /metrics` | Metrics for all models (zeros for unused ones) |
| `GET /health` | Liveness |

`model_type`: `classification | regression | clustering | nlp | other`. Storage outage -> `503`; unexpected error -> generic `500`.

```bash
curl -X POST localhost:8000/models -H 'Content-Type: application/json' \
  -d '{"name":"churn","version":"1.0.0","model_type":"classification"}'
curl -X POST localhost:8000/models/<id>/predict -H 'Content-Type: application/json' \
  -d '{"features":{"age":30,"plan":"pro"}}'
```

## Dashboard

- Lists every model with metadata, request count, average latency and average confidence.
- Polls the API every 3 s (so metrics stay current) and shows the last update time.
- Filters by name and version (instant, client side); registration form; "Send test prediction" button to generate traffic.

## Design notes

- **Repository pattern**: `Repository` protocol with `SupabaseRepository` and `InMemoryRepository`; business logic is storage-agnostic and fully testable.
- **Aggregation in the database**: the `model_metrics` view computes counts/averages, so the API never pulls raw logs.
- **Uniqueness** of `(name, version)` is enforced by a DB constraint (race-free); violations map to `409`.
- **Simulation**: output is a hash of `(model_id, features)`; latency is a simulated 5-99 ms plus measured overhead. `avg_confidence` is a simple drift proxy: a downward trend signals degradation.
- Security: service-role key stays server side, RLS enabled on tables, CORS restricted via `CORS_ORIGINS`.

## Tests

```bash
cd backend && pip install -r requirements-dev.txt && pytest     # 40 tests, ~100% coverage
cd frontend && npm install && npm run typecheck && npm run build
```
The Supabase repository is tested against a mocked client, so tests need no network.
