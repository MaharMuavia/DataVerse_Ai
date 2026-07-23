# DataVerse AI Markdown Documentation Library

This is the single entry point for the project's Markdown documentation. Documentation is arranged in numbered folders so readers can follow it in a practical sequence: overview, setup, architecture, implementation, testing, deployment, academic reports, history, and generated notes.

## Required root-file exceptions

Three Markdown files remain at the repository root because development and automation tools discover them by location. They are part of the documentation system but must not be moved.

| File | What it is used for | Authority |
|---|---|---|
| [README.md](../../README.md) | Main repository landing page, product summary, architecture introduction, features, and basic commands. | Current project entry point |
| [AGENTS.md](../../AGENTS.md) | Mandatory engineering, testing, security, database, Git, and delivery instructions for coding agents. | Current operational policy |
| [CLAUDE.md](../../CLAUDE.md) | Additional project context and working guidance for Claude-compatible development tools. | Tool-specific guidance |

## Ordered documentation folders

| Sequence | Folder | Used for |
|---:|---|---|
| 00 | `00_index_and_overview/` | Documentation overview, navigation history, and repository structure |
| 01 | `01_getting_started/` | Installation, configuration, startup, and command references |
| 02 | `02_architecture_and_design/` | Current architecture, AI-provider integration, design specifications, and implementation plans |
| 03 | `03_implementation_and_services/` | Backend, frontend, retail agent, integration, and feature implementation guidance |
| 04 | `04_testing_and_quality/` | Test strategy, evaluation methods, validation evidence, and quality assessment |
| 05 | `05_deployment_and_operations/` | Production deployment, readiness, operations, and cleanup guidance |
| 06 | `06_project_reports_and_defense/` | Academic report content, defense preparation, teacher material, and retail analysis examples |
| 07 | `07_completion_and_history/` | Historical phase, session, completion, and status records |
| 08 | `08_generated_notes/` | Reproducibility notes generated with technical report artifacts |

## What every Markdown file is used for

### Library entry point

| File | What it is used for | Authority |
|---|---|---|
| `docs/markdown/README.md` | Explains the ordered documentation structure and the purpose of every Markdown file. | Current documentation index |

### 00 - Index and overview

| File | What it is used for | Authority |
|---|---|---|
| [PROJECT_DOCUMENTATION_OVERVIEW.md](00_index_and_overview/PROJECT_DOCUMENTATION_OVERVIEW.md) | Broad description of platform features, architecture, technology stack, and documentation resources. | Background overview; verify changing facts in code |
| [DOCUMENTATION_INDEX_LEGACY.md](00_index_and_overview/DOCUMENTATION_INDEX_LEGACY.md) | Preserves the older topic-based documentation index and historical reading paths. | Legacy navigation reference |
| [REPOSITORY_STRUCTURE_GUIDE.md](00_index_and_overview/REPOSITORY_STRUCTURE_GUIDE.md) | Describes the current executable folder layout and the numbered Markdown library. | Current structure reference |

### 01 - Getting started

| File | What it is used for | Authority |
|---|---|---|
| [QUICK_START.md](01_getting_started/QUICK_START.md) | Short path for installing dependencies, starting services, and trying the application. | Convenience guide |
| [QUICK_START_V2.md](01_getting_started/QUICK_START_V2.md) | Expanded version-two startup workflow and updated feature walkthrough. | Convenience guide; confirm commands against manifests |
| [SETUP_GUIDE.md](01_getting_started/SETUP_GUIDE.md) | Detailed local and container setup, environment variables, and troubleshooting steps. | Primary setup explanation |
| [QUICK_REFERENCE.md](01_getting_started/QUICK_REFERENCE.md) | Compact command, endpoint, component, and feature lookup. | Fast reference |

### 02 - Architecture and design

| File | What it is used for | Authority |
|---|---|---|
| [ARCHITECTURE.md](02_architecture_and_design/ARCHITECTURE.md) | Explains the current Next.js, FastAPI, agent, analytics, Supabase, and reporting flow. | Primary architecture reference |
| [DEEPANALYZE_INTEGRATION.md](02_architecture_and_design/DEEPANALYZE_INTEGRATION.md) | Documents how the optional DeepAnalyze-compatible language-model provider connects to the agentic engine. | Conditional integration guide |
| [VERIFIABLE_ANALYST_CHAT_IMPLEMENTATION_PLAN.md](02_architecture_and_design/VERIFIABLE_ANALYST_CHAT_IMPLEMENTATION_PLAN.md) | Records the implementation plan for evidence-backed analyst chat and receipts. | Historical plan |
| [VERIFIABLE_ANALYST_CHAT_DESIGN.md](02_architecture_and_design/VERIFIABLE_ANALYST_CHAT_DESIGN.md) | Defines the intended verifiable-chat architecture, evidence flow, and user experience. | Design record |
| [AGENTIC_XAI_UPGRADE_DESIGN.md](02_architecture_and_design/AGENTIC_XAI_UPGRADE_DESIGN.md) | Defines the agent loop, explainable-AI, counterfactual, root-cause, and verification upgrade. | Design record |
| [REPORT_QUALITY_DESIGN.md](02_architecture_and_design/REPORT_QUALITY_DESIGN.md) | Defines report wording, chart integrity, repetition prevention, and business-readability requirements. | Design record referenced by tests |

### 03 - Implementation and services

| File | What it is used for | Authority |
|---|---|---|
| [IMPLEMENTATION_GUIDE.md](03_implementation_and_services/IMPLEMENTATION_GUIDE.md) | Detailed description of implemented analytics, agents, frontend behavior, and integration steps. | Implementation guide |
| [IMPLEMENTATION_COMPLETION_SUMMARY.md](03_implementation_and_services/IMPLEMENTATION_COMPLETION_SUMMARY.md) | Records what was delivered for the agentic LLM core and its supporting tools. | Completion snapshot |
| [INTEGRATION_GUIDE_PHASE5.md](03_implementation_and_services/INTEGRATION_GUIDE_PHASE5.md) | Explains how Phase 5 enhancements connect to existing backend and frontend flows. | Historical integration guide |
| [NEW_TOOLS_REFERENCE.md](03_implementation_and_services/NEW_TOOLS_REFERENCE.md) | Lists newer analytical tools, their inputs, outputs, and intended use. | Feature reference |
| [BACKEND_SERVICE_GUIDE.md](03_implementation_and_services/BACKEND_SERVICE_GUIDE.md) | Backend service entry point and location of FastAPI source, tests, and configuration. | Service guide |
| [FRONTEND_SERVICE_GUIDE.md](03_implementation_and_services/FRONTEND_SERVICE_GUIDE.md) | Next.js frontend installation, local startup, build, and deployment notes. | Service guide |
| [RETAIL_AGENT_GUIDE.md](03_implementation_and_services/RETAIL_AGENT_GUIDE.md) | Describes the retail-agent example, its input data, model provider, and expected outputs. | Example service guide |

### 04 - Testing and quality

| File | What it is used for | Authority |
|---|---|---|
| [EVALUATION_FRAMEWORK.md](04_testing_and_quality/EVALUATION_FRAMEWORK.md) | Defines evaluation dimensions and criteria for agentic and language-model behavior. | Evaluation methodology |
| [INTEGRATION_TESTING_GUIDE.md](04_testing_and_quality/INTEGRATION_TESTING_GUIDE.md) | Provides integration-test procedures for the agentic backend and related services. | Test guide |
| [PHASE_5_FINAL_VALIDATION.md](04_testing_and_quality/PHASE_5_FINAL_VALIDATION.md) | Records Phase 5 validation results and readiness checks at that point in time. | Historical validation snapshot |
| [PROJECT_EVALUATION_REPORT.md](04_testing_and_quality/PROJECT_EVALUATION_REPORT.md) | Comprehensive assessment of architecture, features, implementation, tests, and readiness. | Evaluation report; current code/tests take precedence |

### 05 - Deployment and operations

| File | What it is used for | Authority |
|---|---|---|
| [DEPLOYMENT_READY.md](05_deployment_and_operations/DEPLOYMENT_READY.md) | Historical checklist and evidence supporting deployment readiness. | Readiness snapshot |
| [PRODUCTION_DEPLOYMENT_GUIDE.md](05_deployment_and_operations/PRODUCTION_DEPLOYMENT_GUIDE.md) | Production environment, container, service, security, and monitoring guidance. | Deployment guide |
| [PRODUCTION_READY_RUNBOOK.md](05_deployment_and_operations/PRODUCTION_READY_RUNBOOK.md) | Short operational checklist for validating a production deployment. | Operations runbook |
| [CLEANUP_REPORT.md](05_deployment_and_operations/CLEANUP_REPORT.md) | Records earlier repository cleanup decisions, removed artifacts, and organization changes. | Historical maintenance record |

### 06 - Project reports and defense

| File | What it is used for | Authority |
|---|---|---|
| [PROJECT_REPORT.md](06_project_reports_and_defense/PROJECT_REPORT.md) | Concise academic project report covering purpose, design, implementation, results, and limitations. | Academic report source |
| [PROJECT_DEFENSE_DOCUMENTATION.md](06_project_reports_and_defense/PROJECT_DEFENSE_DOCUMENTATION.md) | Detailed technical material for the final-year-project defense and examiner questions. | Defense reference |
| [PROJECT_EXPLORATION_SUMMARY.md](06_project_reports_and_defense/PROJECT_EXPLORATION_SUMMARY.md) | Repository exploration findings and high-level component summary. | Audit snapshot |
| [PROJECT_TEACHER_PRESENTATION.md](06_project_reports_and_defense/PROJECT_TEACHER_PRESENTATION.md) | Presentation-oriented explanation of project objectives, architecture, workflow, and results. | Presentation source |
| [TEACHER_EXPLANATION.md](06_project_reports_and_defense/TEACHER_EXPLANATION.md) | Plain-language explanation for supervisors or non-specialist reviewers. | Teaching aid |
| [RETAIL_AGENT_REPORT.md](06_project_reports_and_defense/RETAIL_AGENT_REPORT.md) | Example retail analysis generated with the baseline retail-agent workflow. | Example output |
| [RETAIL_AGENT_REPORT_PHI3.md](06_project_reports_and_defense/RETAIL_AGENT_REPORT_PHI3.md) | Example retail analysis generated with the Phi-3 model configuration. | Example output |

### 07 - Completion and history

These documents are retained for traceability. They describe the project at specific milestones and must not override current source code, tests, environment templates, or the current technical audit.

| File | What it is used for |
|---|---|
| [COMPLETION_CERTIFICATE.md](07_completion_and_history/COMPLETION_CERTIFICATE.md) | Formal record of the features claimed complete at the v2.0 milestone. |
| [COMPLETION_PROOF.md](07_completion_and_history/COMPLETION_PROOF.md) | Evidence list supporting the Phase 5 completion claim. |
| [COMPLETION_SUMMARY.md](07_completion_and_history/COMPLETION_SUMMARY.md) | High-level summary of completed modules and project structure. |
| [FINAL_COMPLETION_PROOF.md](07_completion_and_history/FINAL_COMPLETION_PROOF.md) | Condensed final milestone proof and feature checklist. |
| [FINAL_STATUS.md](07_completion_and_history/FINAL_STATUS.md) | Historical final-status report across project phases. |
| [FINAL_SUMMARY.md](07_completion_and_history/FINAL_SUMMARY.md) | Historical final summary of features, commands, and readiness. |
| [PHASE_2_COMPLETION.md](07_completion_and_history/PHASE_2_COMPLETION.md) | Records Phase 2 agentic-analysis implementation. |
| [PHASE_5_COMPLETION_SUMMARY.md](07_completion_and_history/PHASE_5_COMPLETION_SUMMARY.md) | Records Phase 5 feature completion and deliverables. |
| [PHASE_5_FUNCTIONAL_READINESS.md](07_completion_and_history/PHASE_5_FUNCTIONAL_READINESS.md) | Functional-readiness checklist from the Phase 5 milestone. |
| [PHASE_5_IMPROVEMENTS.md](07_completion_and_history/PHASE_5_IMPROVEMENTS.md) | Describes the enhanced features and frontend changes introduced in Phase 5. |
| [PHASES_COMPLETION_REPORT.md](07_completion_and_history/PHASES_COMPLETION_REPORT.md) | Consolidated completion report for all historical phases. |
| [SESSION_COMPLETION_PRIORITY1.md](07_completion_and_history/SESSION_COMPLETION_PRIORITY1.md) | Development-session record for the priority-one analytical tools. |
| [SESSION_PRIORITY2_SUMMARY.md](07_completion_and_history/SESSION_PRIORITY2_SUMMARY.md) | Development-session record for priority-two testing improvements. |
| [STATUS_REPORT.md](07_completion_and_history/STATUS_REPORT.md) | Historical operational status and feature checklist. |

### 08 - Generated notes

| File | What it is used for | Authority |
|---|---|---|
| [DATAVERSE_AI_TECHNICAL_REPORT_SOURCE_NOTES.md](08_generated_notes/DATAVERSE_AI_TECHNICAL_REPORT_SOURCE_NOTES.md) | Stores the technical report's audit scope, report spine, chart map, verification summary, and omission reasons. | Generated reproducibility evidence |
| [chapter_6_data_collection_analysis.md](08_generated_notes/chapter_6_7/chapter_6_data_collection_analysis.md) | Generated Chapter 6 narrative describing data collection, preparation, profiling, and analysis. | Generated academic-report material |
| [chapter_6_tables.md](08_generated_notes/chapter_6_7/chapter_6_tables.md) | Generated Markdown versions of the tables used in Chapter 6. | Generated academic-report material |
| [chapter_7_results_discussion.md](08_generated_notes/chapter_6_7/chapter_7_results_discussion.md) | Generated Chapter 7 narrative covering results, interpretation, limitations, and discussion. | Generated academic-report material |
| [chapter_7_tables.md](08_generated_notes/chapter_6_7/chapter_7_tables.md) | Generated Markdown versions of the tables used in Chapter 7. | Generated academic-report material |
| [chapter_6_7_figures_list.md](08_generated_notes/chapter_6_7/chapter_6_7_figures_list.md) | Index of generated figures used by Chapters 6 and 7. | Generated figure reference |
| [chapter_6_7_evidence_log.md](08_generated_notes/chapter_6_7/chapter_6_7_evidence_log.md) | Evidence log recording commands, source paths, generated outputs, and environment-dependent checks for Chapters 6 and 7. | Generated reproducibility evidence |

## Source-of-truth order

When documents disagree, use this order:

1. Current executable source code and SQL migrations
2. Automated tests and successful build results
3. Environment examples and package/dependency manifests
4. Current architecture and setup documents
5. Design records and implementation guides
6. Historical phase, completion, and status reports
