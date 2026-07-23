# Repository Structure Guide

The repository keeps executable folders at their framework-compatible paths and organizes human-readable Markdown documentation under one numbered parent folder. Renaming source folders with numeric prefixes would break imports, Docker paths, Next.js conventions, tests, and deployment scripts, so sequence is expressed in the documentation layout instead.

## Recommended reading sequence

1. [`docs/markdown/README.md`](../README.md) - complete documentation index and the purpose of every Markdown file
2. [`01_getting_started/SETUP_GUIDE.md`](../01_getting_started/SETUP_GUIDE.md) - installation and configuration
3. [`02_architecture_and_design/ARCHITECTURE.md`](../02_architecture_and_design/ARCHITECTURE.md) - current component and data flow
4. [`03_implementation_and_services/IMPLEMENTATION_GUIDE.md`](../03_implementation_and_services/IMPLEMENTATION_GUIDE.md) - feature implementation
5. [`04_testing_and_quality/`](../04_testing_and_quality/) - validation and evaluation
6. [`05_deployment_and_operations/`](../05_deployment_and_operations/) - production and operations
7. [`06_project_reports_and_defense/`](../06_project_reports_and_defense/) - academic reporting and defense
8. [`07_completion_and_history/`](../07_completion_and_history/) - historical milestone records

## Current top-level structure

```text
FINAL3/
|-- README.md                  Main repository entry point
|-- AGENTS.md                  Engineering-agent rules
|-- CLAUDE.md                  Claude-compatible guidance
|-- package.json               Workspace development commands
|-- docker-compose.yml         Frontend/backend container orchestration
|-- .env.example               Root environment template
|
|-- frontend/                  Next.js application source
|   |-- app/                   App Router pages and layouts
|   |-- components/            Dashboard and public-site components
|   |-- hooks/                 React hooks
|   |-- lib/                   API, authentication, formatting, and contracts
|   `-- scripts/               HTTPS development and client tests
|
|-- dataverse_backend/         FastAPI and analytics backend
|   |-- app/api/               HTTP routes, schemas, and upload parsing
|   |-- app/agents/            Dataset and analyst agents
|   |-- app/core/              Configuration, middleware, storage, and logging
|   |-- app/services/          Analytics, ML, XAI, reports, auth, and persistence
|   `-- tests/                 Backend unit, API, integration, and security tests
|
|-- data/                      Audited retail training/evaluation dataset
|-- models/                    Saved scikit-learn pipelines and metadata
|-- supabase/                  Ordered database/storage migration
|-- scripts/                   Development, training, smoke-test, report, and document automation
|
|-- docs/
|   |-- markdown/              All non-root Markdown documentation
|   |   |-- 00_index_and_overview/
|   |   |-- 01_getting_started/
|   |   |-- 02_architecture_and_design/
|   |   |-- 03_implementation_and_services/
|   |   |-- 04_testing_and_quality/
|   |   |-- 05_deployment_and_operations/
|   |   |-- 06_project_reports_and_defense/
|   |   |-- 07_completion_and_history/
|   |   `-- 08_generated_notes/
|   |-- specs/                 Word-format specifications
|   `-- reports/               Stored test evidence
|
|-- output/                    Current generated reports, slides, screenshots, and diagrams
|-- outputs/                   Generated academic chapter material
|-- report/                    Generated analytical figures
|-- logs/                      Runtime and development logs
|-- session_storage/           Mutable local session data; not source code
`-- tmp/                       Temporary conversion and visual-QA files
```

## Markdown organization rule

- New project documentation belongs under the appropriate numbered directory in `docs/markdown/`.
- Do not add new Markdown files inside `frontend/`, `dataverse_backend/`, `output/`, or service folders.
- Keep only `README.md`, `AGENTS.md`, and `CLAUDE.md` at the repository root because tools discover them there.
- Update [`docs/markdown/README.md`](../README.md) whenever a Markdown document is added, renamed, archived, or removed.
