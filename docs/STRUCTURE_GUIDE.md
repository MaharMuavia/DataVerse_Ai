# Repository Structure Guide

This repository was reorganized so a reviewer can understand it quickly. The goal is:
- keep **all documentation** in one place (`docs/`)
- keep **all runnable helpers** in one place (`scripts/`)
- keep **all sample datasets** in one place (`data/`)
- keep **backend/frontend source** in their existing service folders

## Where to start

1. `docs/README.md` — overview, features, architecture
2. `docs/INDEX.md` — links to every document and topic
3. Run options:
   - Docker: `docker-compose up -d --build`
   - Windows local dev: `powershell -ExecutionPolicy Bypass -File scripts/start-all.ps1`
   - API demo: `python scripts/demo_client.py`

## Top-level layout (current)

```text
FINAL3/
  docker-compose.yml           # Full stack (Postgres + Redis + FastAPI + Next.js)
  .env.example                 # Environment template
  .gitignore                   # Ignore venv/node_modules/runtime data

  data/                        # Sample datasets used for demos/tests
    sample_products.csv
    sample_data.csv
    retail_mart_processed_v1.csv

  docs/                        # ALL markdown documentation + assets
    README.md                  # Overview + architecture (start here)
    INDEX.md                   # Documentation index
    SETUP.md                   # Setup guide (manual + docker)
    assets/dashboard.html      # Lightweight HTML dashboard demo
    services/                  # Component docs that used to be in service folders
      backend/README.md
      frontend/README.md
      retail-agent/README.md
    reports/                   # Stored reports/evidence (example: test output)
    specs/                     # Specification docs (DOCX)

  scripts/                     # Helper scripts (start/deploy/tests/db utilities)
    start-all.ps1
    start-all.bat
    START.bat
    deploy.ps1
    deploy.sh
    demo_client.py
    run_server.py
    ...

  dataverse_backend/           # FastAPI backend source
    app/
    tools/
    tests/

  dataverse_frontend/          # Next.js frontend source
    app/
    components/
    lib/

  retail-agent/                # Optional legacy agent source (Ollama-based)

  logs/                        # Runtime logs (generated)
  session_storage/             # Runtime session files (generated)
  tmp_report_exports/          # Runtime exports (generated)
```

## What changed during the restructure

- Moved every project `*.md` into `docs/` (including service READMEs).
- Moved runnable helper scripts into `scripts/`.
- Moved sample datasets into `data/`.
- Moved static dashboard HTML into `docs/assets/`.
- Updated links, commands, and scripts to match the new paths.
- Removed hard-coded absolute machine paths from startup/deploy scripts (portable repo-relative paths).

