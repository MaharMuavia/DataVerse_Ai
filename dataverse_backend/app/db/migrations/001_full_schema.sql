-- Full schema migration for DataVerse AI
-- Run this on startup to ensure all tables exist

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours',
    dataset_filename TEXT NOT NULL,
    dataset_rows INT NOT NULL,
    dataset_cols INT NOT NULL,
    parquet_path TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    query_text TEXT NOT NULL,
    intent TEXT,
    confidence JSONB,
    result_json JSONB,
    narration TEXT,
    chart_spec TEXT,
    execution_ms INT
);

CREATE TABLE IF NOT EXISTS ml_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'pending',
    task_type TEXT,
    target_column TEXT,
    best_model TEXT,
    metrics JSONB,
    shap_values JSONB,
    error TEXT
);

-- Legacy tables (keeping for compatibility)
CREATE TABLE IF NOT EXISTS datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    row_count INT NOT NULL,
    column_metadata JSONB NOT NULL,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID REFERENCES datasets(id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    parsed_intent JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID REFERENCES datasets(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    action TEXT NOT NULL,
    reasoning TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID REFERENCES datasets(id) ON DELETE CASCADE,
    computed_metrics JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_result_id UUID REFERENCES analysis_results(id) ON DELETE CASCADE,
    report_text TEXT NOT NULL,
    model_used TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_queries_session ON queries(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_ml_jobs_session ON ml_jobs(session_id);
CREATE INDEX IF NOT EXISTS idx_user_queries_dataset ON user_queries(dataset_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_dataset ON agent_runs(dataset_id);
CREATE INDEX IF NOT EXISTS idx_analysis_results_dataset ON analysis_results(dataset_id);