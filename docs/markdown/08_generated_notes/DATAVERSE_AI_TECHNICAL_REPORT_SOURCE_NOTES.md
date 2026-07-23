# DataVerse AI technical report source notes

Audit date: 2026-07-14

## Report spine

- Question: What is present in the complete current FINAL3 folder, what is each project file for, and which models, datasets, libraries, components, services, security controls, APIs, artifacts, and deployment mechanisms are actually used?
- Answer: Deterministic Next.js/FastAPI/Pandas/scikit-learn system with conditional XAI/LLMs and Supabase-backed auth/persistence.
- Key caveats: saved model artifacts are not loaded by live app; total_sales leakage; weak minority stockout performance; external Supabase production state not verified.

## Folder inventory scope

- Every safely reportable project and generated file is included in the CSV/JSON inventory and Appendix D.
- Third-party installations, Git internals, build/test caches, browser traces, session storage, temporary conversions, and local certificate material are counted in Appendix E but their internal contents are not reproduced.
- Environment files are inventoried by filename only; no secret values are read into or written to the report.

## Chart map

1. System architecture: component/flow diagram; source app code and existing architecture asset; supports the end-to-end runtime claim.
2. Saved model feature importance: three horizontal bar panels; source models/model_metadata.json; supports leakage and driver interpretation; single-root palette per panel; exact values shown.
3. Stockout confusion matrix: 2x2 matrix; source models/model_metadata.json; supports minority-class performance limitation; exact counts and test-share labels shown.

## Verification

- Backend: 214 passed, 14 dependency deprecation warnings.
- Frontend lint: passed.
- Frontend production build: passed.
- PDF visual verification is performed after Word export.

## Omitted visuals

- No cross-model performance chart because regression R2/RMSE/MAE and classification accuracy/F1 are not directly comparable.
- Dependency, API, and database inventories use tables because exact lookup is the reader's primary task.
