-- Run this in the Supabase SQL editor (or `psql`) before starting the backend.
create extension if not exists pgcrypto;

create table if not exists models (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  version     text not null,
  model_type  text not null check (model_type in ('classification','regression','clustering','nlp','other')),
  description text,
  created_at  timestamptz not null default now(),
  unique (name, version)
);

create table if not exists prediction_logs (
  id          uuid primary key default gen_random_uuid(),
  model_id    uuid not null references models(id) on delete cascade,
  request     jsonb not null,
  response    jsonb not null,
  latency_ms  double precision not null,
  confidence  double precision,
  created_at  timestamptz not null default now()
);
create index if not exists idx_logs_model_created on prediction_logs (model_id, created_at desc);

-- Aggregated metrics per model, computed in the database.
create or replace view model_metrics as
select model_id,
       count(*)::int                       as request_count,
       coalesce(avg(latency_ms), 0)        as avg_latency_ms,
       coalesce(avg(confidence), 0)        as avg_confidence,
       max(created_at)                     as last_request_at
from prediction_logs
group by model_id;

-- The backend uses the service_role key. Keep RLS on so the anon key cannot read these tables.
alter table models enable row level security;
alter table prediction_logs enable row level security;
