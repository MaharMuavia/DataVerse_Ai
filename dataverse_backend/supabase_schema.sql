-- ============================================================================
-- DataVerse AI — Supabase schema
-- Paste this whole file into the Supabase dashboard → SQL Editor → Run.
-- Users are managed by Supabase Auth (auth.users); these are the app tables.
-- The backend uses the service_role key (bypasses RLS) and enforces per-user
-- ownership in application code (session_service.ensure_access).
-- ============================================================================

create extension if not exists "pgcrypto";

-- ── Chat sessions ──────────────────────────────────────────────────────────
create table if not exists public.chat_sessions (
    id                uuid primary key default gen_random_uuid(),
    user_id           uuid references auth.users (id) on delete cascade,
    title             text        not null default 'New Chat',
    status            text        not null default 'active',
    active_dataset_id uuid,
    metadata          jsonb       not null default '{}'::jsonb,
    last_message_at   timestamptz,
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now()
);
create index if not exists idx_chat_sessions_user on public.chat_sessions (user_id);

-- ── Chat messages ──────────────────────────────────────────────────────────
create table if not exists public.chat_messages (
    id           uuid primary key default gen_random_uuid(),
    session_id   uuid not null references public.chat_sessions (id) on delete cascade,
    role         text not null,
    content      text,
    message_type text not null default 'text',
    payload      jsonb not null default '{}'::jsonb,
    created_at   timestamptz not null default now()
);
create index if not exists idx_chat_messages_session on public.chat_messages (session_id);

-- ── Datasets ───────────────────────────────────────────────────────────────
create table if not exists public.datasets (
    id                uuid primary key default gen_random_uuid(),
    session_id        uuid references public.chat_sessions (id) on delete cascade,
    user_id           uuid references auth.users (id) on delete cascade,
    filename          text,
    original_filename text,
    storage_path      text,
    file_type         text,
    file_size         bigint,
    row_count         integer,
    column_count      integer,
    columns           jsonb,
    schema_profile    jsonb,
    semantic_map      jsonb,
    status            text default 'uploaded',
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now()
);
create index if not exists idx_datasets_session on public.datasets (session_id);
create index if not exists idx_datasets_user on public.datasets (user_id);

-- ── Agent runs ─────────────────────────────────────────────────────────────
create table if not exists public.agent_runs (
    id           uuid primary key default gen_random_uuid(),
    session_id   uuid references public.chat_sessions (id) on delete cascade,
    dataset_id   uuid,
    agent_name   text,
    status       text,
    input        jsonb,
    output       jsonb,
    error        text,
    started_at   timestamptz not null default now(),
    completed_at timestamptz
);
create index if not exists idx_agent_runs_session on public.agent_runs (session_id);

-- ── Reports ────────────────────────────────────────────────────────────────
create table if not exists public.reports (
    id           uuid primary key default gen_random_uuid(),
    session_id   uuid references public.chat_sessions (id) on delete cascade,
    dataset_id   uuid,
    title        text,
    report_type  text default 'analysis',
    format       text,
    storage_path text,
    public_url   text,
    metadata     jsonb not null default '{}'::jsonb,
    created_at   timestamptz not null default now()
);
create index if not exists idx_reports_session on public.reports (session_id);

-- ── Storage buckets (datasets + reports) ────────────────────────────────────
insert into storage.buckets (id, name, public)
values ('dataverse-datasets', 'dataverse-datasets', false)
on conflict (id) do nothing;

insert into storage.buckets (id, name, public)
values ('dataverse-reports', 'dataverse-reports', false)
on conflict (id) do nothing;

-- ── Optional defense-in-depth: Row Level Security ───────────────────────────
-- The backend uses the service_role key, which bypasses RLS, so the app works
-- WITHOUT the block below. Enable it only if you also plan to query these
-- tables directly from the browser with the anon key.
--
-- alter table public.chat_sessions enable row level security;
-- create policy "own sessions" on public.chat_sessions
--   for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
-- alter table public.datasets enable row level security;
-- create policy "own datasets" on public.datasets
--   for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
