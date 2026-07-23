# Chapter 6/7 Evidence Log

Generated at: 2026-06-16T13:07:49

## Evidence Summary
| Evidence Type | Item | Result |
| --- | --- | --- |
| Dataset | data/retail_mart_processed_v1.csv | 35,000 rows, 21 columns |
| Parser | app.api.upload_parsing.parse_uploaded_dataframe | Passed |
| Pipeline | app.services.analysis_pipeline.AnalysisPipeline.run_full_analysis | Passed |
| API | GET /health/live | Not run |
| API | POST /api/sessions/{session_id}/datasets/upload | Not run |
| API | POST /api/sessions/{session_id}/analyze | Not run |
| Report | HTML/PDF generation | HTML=True; PDF=True |
| Output | outputs/chapter_6_data_collection_analysis.md | Generated |
| Output | outputs/chapter_7_results_discussion.md | Generated |

## Commands Run
| Command | Status | Return Code | Output |
| --- | --- | --- | --- |
| C:\Users\mouav\AppData\Local\Programs\Python\Python312\python.exe -m pytest -q dataverse_backend/tests | Failed | 1 | 7000' in 'Dataset contains 4 rows and 5 columns. Semantic dataset type is transaction_ledger. Data quality score is 95.0. Total... Udhaar Outstanding: 500. Net Profit: 6500. Profit Status: Profit. General Entry is the top revenue product with 5000.'  dataverse_backend\tests\test_analyze_endpoints.py:242: AssertionError ============================== warnings summary =============================== ..\..\..\AppData\Local\Programs\Python\Python312\Lib\site-packages\pydantic\fields.py:804: 140 warnings   C:\Users\mouav\AppData\Local\Programs\Python\Python312\Lib\site-packages\pydantic\fields.py:804: PydanticDeprecatedSince20: Using extra keyword arguments on `Field` is deprecated and will be re |
| npm.cmd run lint | Passed | 0 | > lint > npm --prefix frontend run lint   > dataverse-ai@0.1.0 lint > eslint .   C:\Users\mouav\OneDrive\Desktop\FINAL3\frontend\app\page.tsx   1402:19  warning  Using `<img>` could result in slower LCP and higher bandwidth. Consider using `<Image />` from `next/image` or a custom image loader to automatically optimize images. This may incur additional usage or cost from your provider. See: https://nextjs.org/docs/messages/no-img-element  @next/next/no-img-element   2122:15  warning  Using `<img>` could result in slower LCP and higher bandwidth. Consider using `<Image />` from `next/image` or a custom image loader to automatically optimize images. This may incur additional usage or cost from |
| npm.cmd run build | Passed | 0 | > build > npm --prefix frontend run build   > dataverse-ai@0.1.0 build > next build     â–² Next.js 15.5.18     Creating an optimized production build ...  âœ“ Compiled successfully in 2.7s    Skipping linting    Checking validity of types ...    Collecting page data ...    Generating static pages (0/5) ...    Generating static pages (1/5)     Generating static pages (2/5)     Generating static pages (3/5)   âœ“ Generating static pages (5/5)    Finalizing page optimization ...    Collecting build traces ...  Route (app)                                 Size  First Load JS â”Œ â—‹ /                                    66.9 kB         169 kB â”œ â—‹ /_not-found                            990 B   |
| docker --version | Passed | 0 | Docker version 29.5.3, build d1c06ef |
| docker compose config | Passed | 0 | name: final3 services:   backend:     build:       context: C:\Users\mouav\OneDrive\Desktop\FINAL3\dataverse_backend       dockerfile: Dockerfile     environment:       BACKEND_BASE_URL: http://localhost:8000       CORS_ORIGINS: http://localhost:3000,http://127.0.0.1:3000       ENVIRONMENT: development       OPENAI_API_KEY: [REDACTED]       OPENAI_CHAT_MODEL: ""       PORT: "8000"       SUPABASE_ANON_KEY: [REDACTED]       SUPABASE_SERVICE_ROLE_KEY: [REDACTED]       SUPABASE_URL: ""     networks:       default: null     ports:       - mode: ingress         target: 8000         published: "8000"         protocol: tcp     volumes:       - type: bind         source: C:\Users\mouav\OneDrive\Deskt |
| git grep -n sk-[A-Za-z0-9] | Review needed | 0 | Potential key-like patterns found; output redacted. Review matches to confirm they are placeholders or false positives. dataverse_backend/tests/test_security.py:120:                if "placeholder" not in match.lower() and "your_key" not in match.lower() and "sk-your-openai-api-key" not in match.lower(): docs/PHASE_2_COMPLETION.md:173:ANTHROPIC_API_KEY=[REDACTED] docs/PHASE_2_COMPLETION.md:207:ANTHROPIC_API_KEY=[REDACTED] docs/PROJECT_DEFENSE_DOCUMENTATION.md:264:OPENAI_API_KEY=[REDACTED] docs/QUICK_START.md:88:OPENAI_API_KEY=[REDACTED] frontend/package-lock.json:10374:      "resolved": "https://registry.npmjs.org/netmask/-/netmask-2.1.1.tgz", frontend/package-lock.json:11613:      "resolved |

## File Paths and Functions Checked
| path | line | text |
| --- | --- | --- |
| frontend/app/page.tsx | 17 | analyzeSession, |
| frontend/app/page.tsx | 24 | uploadDataset, |
| frontend/app/page.tsx | 1745 | export default function App() { |
| frontend/app/page.tsx | 1868 | const uploaded = await uploadDataset(file, sessionId, { autoAnalyze: false, generateReport: false, runXai: false }); |
| frontend/app/page.tsx | 1943 | const result = await analyzeSession(sessionId, datasetId, query); |
| frontend/lib/dataverse-api.ts | 19 | function createWorkspaceUserId() { |
| frontend/lib/dataverse-api.ts | 28 | function getWorkspaceUserId() { |
| frontend/lib/dataverse-api.ts | 43 | function withWorkspaceHeaders(init?: RequestInit): RequestInit { |
| frontend/lib/dataverse-api.ts | 209 | async function readError(response: Response): Promise<string> { |
| frontend/lib/dataverse-api.ts | 222 | async function apiFetch(input: string, init?: RequestInit): Promise<Response> { |
| frontend/lib/dataverse-api.ts | 242 | export async function checkBackendHealth(): Promise<BackendHealth> { |
| frontend/lib/dataverse-api.ts | 257 | export async function ensureBackendAvailable(): Promise<void> { |
| frontend/lib/dataverse-api.ts | 273 | export async function createSession(title = 'New Chat'): Promise<ChatSessionSummary> { |
| frontend/lib/dataverse-api.ts | 286 | export async function listSessions(): Promise<ChatSessionSummary[]> { |
| frontend/lib/dataverse-api.ts | 294 | export async function getSession(sessionId: string): Promise<SessionDetail> { |
| frontend/lib/dataverse-api.ts | 302 | export async function listDatasets(): Promise<RecentDataset[]> { |
| frontend/lib/dataverse-api.ts | 310 | export async function uploadDataset( |
| frontend/lib/dataverse-api.ts | 359 | export async function askDataset(datasetId: string, prompt: string): Promise<AskResponse> { |
| frontend/lib/dataverse-api.ts | 374 | export async function getProfile(datasetId: string): Promise<ProfileResponse> { |
| frontend/lib/dataverse-api.ts | 384 | export async function deleteDataset(datasetId: string): Promise<{ dataset_id: string; deleted: boolean }> { |
| frontend/lib/dataverse-api.ts | 396 | export async function analyzeSession( |
| frontend/lib/dataverse-api.ts | 413 | export async function streamQuery( |
| dataverse_backend/app/api/session_routes.py | 17 | async def create_session( |
| dataverse_backend/app/api/session_routes.py | 25 | async def list_sessions( |
| dataverse_backend/app/api/session_routes.py | 32 | async def get_session(session_id: str) -> dict[str, Any]: |
| dataverse_backend/app/api/session_routes.py | 40 | async def update_session(session_id: str, request: ChatSessionUpdate) -> dict[str, Any]: |
| dataverse_backend/app/api/session_routes.py | 49 | async def delete_session(session_id: str) -> dict[str, Any]: |
| dataverse_backend/app/api/session_routes.py | 55 | async def upload_dataset_to_session( |
| dataverse_backend/app/api/session_routes.py | 99 | async def list_session_datasets(session_id: str) -> list[dict[str, Any]]: |
| dataverse_backend/app/api/session_routes.py | 104 | async def analyze_session(session_id: str, request: SessionAnalyzeRequest) -> dict[str, Any]: |
| dataverse_backend/app/api/session_routes.py | 120 | async def create_message(session_id: str, request: ChatMessageCreate) -> dict[str, Any]: |
| dataverse_backend/app/api/session_routes.py | 130 | async def list_agent_runs(session_id: str) -> list[dict[str, Any]]: |
| dataverse_backend/app/api/session_routes.py | 136 | async def list_session_reports(session_id: str) -> list[dict[str, Any]]: |
| dataverse_backend/app/api/dataset_session_routes.py | 17 | async def upload_dataset_compat( |
| dataverse_backend/app/api/dataset_session_routes.py | 50 | async def list_recent_datasets( |
| dataverse_backend/app/api/dataset_session_routes.py | 57 | async def get_dataset(dataset_id: str) -> dict[str, Any]: |
| dataverse_backend/app/api/dataset_session_routes.py | 65 | async def get_dataset_profile(dataset_id: str) -> dict[str, Any]: |
| dataverse_backend/app/api/dataset_session_routes.py | 84 | async def ask_dataset(dataset_id: str, request: AskRequest) -> dict[str, Any]: |
| dataverse_backend/app/api/dataset_session_routes.py | 112 | async def delete_dataset(dataset_id: str) -> dict[str, Any]: |
| dataverse_backend/app/api/upload_parsing.py | 11 | def _decode_csv(contents: bytes) -> str: |
| dataverse_backend/app/api/upload_parsing.py | 20 | def _detect_csv_dialect(csv_text: str) -> csv.Dialect: |
| dataverse_backend/app/api/upload_parsing.py | 28 | def _read_repaired_csv(csv_text: str, dialect: csv.Dialect) -> pd.DataFrame: |
| dataverse_backend/app/api/upload_parsing.py | 51 | return pd.read_csv(repaired_csv) |
| dataverse_backend/app/api/upload_parsing.py | 54 | def _rows_from_csv(csv_text: str, dialect: csv.Dialect) -> list[list[str]]: |
| dataverse_backend/app/api/upload_parsing.py | 62 | def _coerce_sectioned_value(value: str) -> Any: |
| dataverse_backend/app/api/upload_parsing.py | 74 | def _parse_sectioned_report_csv(csv_text: str, dialect: csv.Dialect) -> pd.DataFrame \| None: |
| dataverse_backend/app/api/upload_parsing.py | 80 | because the first row has one field. This function finds the widest |
| dataverse_backend/app/api/upload_parsing.py | 143 | def _ensure_non_empty_dataframe(df: pd.DataFrame) -> pd.DataFrame: |
| dataverse_backend/app/api/upload_parsing.py | 151 | def parse_uploaded_dataframe(filename: str, contents: bytes) -> pd.DataFrame: |
| dataverse_backend/app/api/upload_parsing.py | 163 | df = pd.read_csv(io.StringIO(csv_text), sep=dialect.delimiter) |
| dataverse_backend/app/api/upload_parsing.py | 169 | return _ensure_non_empty_dataframe(pd.read_excel(io.BytesIO(contents))) |
| dataverse_backend/app/services/session_service.py | 12 | from ..api.upload_parsing import parse_uploaded_dataframe |
| dataverse_backend/app/services/session_service.py | 30 | def __init__(self) -> None: |
| dataverse_backend/app/services/session_service.py | 34 | async def create_session(self, title: str = "New Chat", user_id: str \| None = None) -> dict[str, Any]: |
| dataverse_backend/app/services/session_service.py | 50 | async def list_sessions(self, user_id: str \| None = None) -> list[dict[str, Any]]: |
| dataverse_backend/app/services/session_service.py | 76 | async def get_session(self, session_id: str) -> dict[str, Any]: |
| dataverse_backend/app/services/session_service.py | 92 | async def update_session(self, session_id: str, payload: dict[str, Any]) -> dict[str, Any] \| None: |
| dataverse_backend/app/services/session_service.py | 96 | async def delete_session(self, session_id: str) -> None: |
| dataverse_backend/app/services/session_service.py | 99 | async def add_message( |
| dataverse_backend/app/services/session_service.py | 122 | async def upload_dataset(self, session_id: str, filename: str, content: bytes) -> dict[str, Any]: |
| dataverse_backend/app/services/session_service.py | 126 | df = parse_uploaded_dataframe(filename, content) |
| dataverse_backend/app/services/session_service.py | 177 | async def list_datasets(self, user_id: str \| None = None) -> list[dict[str, Any]]: |
| dataverse_backend/app/services/session_service.py | 190 | async def list_session_datasets(self, session_id: str) -> list[dict[str, Any]]: |
| dataverse_backend/app/services/session_service.py | 193 | async def get_dataset(self, dataset_id: str) -> dict[str, Any] \| None: |
| dataverse_backend/app/services/session_service.py | 196 | async def delete_dataset(self, dataset_id: str) -> None: |
| dataverse_backend/app/services/session_service.py | 199 | async def analyze( |
| dataverse_backend/app/services/session_service.py | 322 | async def chat_message(self, session_id: str, content: str, dataset_id: str \| None = None) -> dict[str, Any]: |
| dataverse_backend/app/services/session_service.py | 330 | async def generate_report(self, session_id: str, dataset_id: str, title: str, facts: dict[str, Any], xai_output: dict[str, Any]) -> dict[str, Any]: |
| dataverse_backend/app/services/session_service.py | 362 | async def list_reports(self, session_id: str) -> list[dict[str, Any]]: |
| dataverse_backend/app/services/session_service.py | 365 | async def get_report_download(self, report_id: str, fmt: str) -> tuple[str \| None, Path \| None]: |
| dataverse_backend/app/services/session_service.py | 377 | async def _start_agent( |
| dataverse_backend/app/services/session_service.py | 401 | async def _complete_agent(self, run_id: str, output: dict[str, Any]) -> None: |
| dataverse_backend/app/services/session_service.py | 404 | def _agent_summary( |
| dataverse_backend/app/services/session_service.py | 430 | def _completed_step(self, name: str) -> dict[str, Any]: |
| dataverse_backend/app/services/session_service.py | 433 | def _dataset_steps(self) -> list[dict[str, Any]]: |
| dataverse_backend/app/services/session_service.py | 440 | def _analysis_steps(self) -> list[dict[str, Any]]: |
| dataverse_backend/app/services/session_service.py | 450 | def _report_steps( |
| dataverse_backend/app/services/session_service.py | 463 | async def _insert(self, table: str, payload: dict[str, Any]) -> dict[str, Any]: |
| dataverse_backend/app/services/session_service.py | 468 | async def _update(self, table: str, row_id: str, payload: dict[str, Any]) -> dict[str, Any] \| None: |
| dataverse_backend/app/services/session_service.py | 473 | async def _delete(self, table: str, row_id: str) -> None: |
| dataverse_backend/app/services/session_service.py | 479 | async def _all_rows(self, table: str) -> list[dict[str, Any]]: |
| dataverse_backend/app/services/session_service.py | 484 | async def _get_by_id(self, table: str, row_id: str) -> dict[str, Any] \| None: |
| dataverse_backend/app/services/session_service.py | 492 | def normalize_charts(charts: list[dict[str, Any]]) -> list[dict[str, Any]]: |
| dataverse_backend/app/services/session_service.py | 497 | def _response_charts(facts: dict[str, Any], *, include_report_level: bool) -> list[dict[str, Any]]: |
| dataverse_backend/app/services/session_service.py | 503 | def _response_tables(facts: dict[str, Any]) -> list[dict[str, Any]]: |
| dataverse_backend/app/services/session_service.py | 511 | def _response_xai(facts: dict[str, Any], xai_output: dict[str, Any]) -> dict[str, Any] \| None: |
| dataverse_backend/app/services/session_service.py | 521 | def _should_generate_report(facts: dict[str, Any]) -> bool: |
| dataverse_backend/app/services/session_service.py | 526 | def _explicit_report_request(content: str) -> bool: |
| dataverse_backend/app/services/session_service.py | 533 | def _promote_full_report_facts(facts: dict[str, Any]) -> dict[str, Any]: |
| dataverse_backend/app/services/session_service.py | 549 | def _merge_chart_sources(*chart_groups: list[dict[str, Any]]) -> list[dict[str, Any]]: |
| dataverse_backend/app/services/session_service.py | 564 | def _dedupe_tables(tables: list[dict[str, Any]]) -> list[dict[str, Any]]: |
| dataverse_backend/app/services/session_service.py | 586 | def build_tables(facts: dict[str, Any]) -> list[dict[str, Any]]: |
| dataverse_backend/app/services/analysis_pipeline.py | 39 | def __init__(self, narrator: ReportNarrator \| None = None): |
| dataverse_backend/app/services/analysis_pipeline.py | 42 | def run_full_analysis( |
| dataverse_backend/app/services/analysis_pipeline.py | 73 | async def run_full_analysis_async( |
| dataverse_backend/app/services/analysis_pipeline.py | 104 | def _compute( |
| dataverse_backend/app/services/analysis_pipeline.py | 230 | def _legacy_automl_alias(self, prediction: dict[str, Any]) -> dict[str, Any]: |
| dataverse_backend/app/services/analysis_pipeline.py | 238 | def _merge_narration(self, facts: dict[str, Any], narration: dict[str, Any]) -> dict[str, Any]: |
| dataverse_backend/app/services/analysis_pipeline.py | 253 | def profile_dataset(self, df: pd.DataFrame) -> dict[str, Any]: |
| dataverse_backend/app/services/analysis_pipeline.py | 256 | def compute_data_quality(self, df: pd.DataFrame) -> dict[str, Any]: |
| dataverse_backend/app/services/analysis_pipeline.py | 259 | def compute_eda(self, df: pd.DataFrame, outliers: dict[str, Any] \| None = None) -> dict[str, Any]: |
| dataverse_backend/app/services/analysis_pipeline.py | 262 | def compute_trends(self, df: pd.DataFrame) -> dict[str, Any]: |
| dataverse_backend/app/services/analysis_pipeline.py | 265 | def compute_correlations(self, df: pd.DataFrame) -> dict[str, Any]: |
| dataverse_backend/app/services/analysis_pipeline.py | 268 | def compute_outliers(self, df: pd.DataFrame) -> dict[str, Any]: |
| dataverse_backend/app/services/analysis_pipeline.py | 271 | def train_model( |
| dataverse_backend/app/services/analysis_pipeline.py | 288 | def run_xai(self, trained_bundle: Any, prediction: dict[str, Any], run_xai: bool = True) -> dict[str, Any]: |
| dataverse_backend/app/services/analysis_pipeline.py | 318 | def generate_charts( |
| dataverse_backend/app/services/analysis_pipeline.py | 330 | def _normalize_charts(charts: list[dict[str, Any]]) -> list[dict[str, Any]]: |
| dataverse_backend/app/services/analysis_pipeline.py | 335 | def _food_catalog_analysis(df: pd.DataFrame, semantic_map: dict[str, Any]) -> dict[str, Any]: |
| dataverse_backend/app/services/analysis_pipeline.py | 402 | def _merge_food_analysis(product_analysis: dict[str, Any], food_analysis: dict[str, Any]) -> dict[str, Any]: |
| dataverse_backend/app/services/analysis_pipeline.py | 413 | def _food_query_answer(query: str \| None, food_analysis: dict[str, Any]) -> dict[str, Any] \| None: |
| dataverse_backend/app/services/analysis_pipeline.py | 436 | def _frequency_rows(df: pd.DataFrame, column: str, key: str) -> list[dict[str, Any]]: |
| dataverse_backend/app/services/analysis_pipeline.py | 441 | def _prediction_request( |
| dataverse_backend/app/services/analysis_pipeline.py | 475 | def _default_kpis(business_metrics: dict[str, Any]) -> list[dict[str, Any]]: |
| dataverse_backend/app/services/analysis_pipeline.py | 485 | def _report_charts_for_query( |
| dataverse_backend/app/services/analysis_pipeline.py | 521 | def _bar_chart(title: str, data: list[dict[str, Any]], x_key: str, y_key: str) -> dict[str, Any]: |
| dataverse_backend/app/services/analysis_pipeline.py | 525 | def _line_chart(title: str, data: list[dict[str, Any]], x_key: str, y_key: str) -> dict[str, Any]: |
| dataverse_backend/app/services/analysis_pipeline.py | 529 | def _first_existing_column(df: pd.DataFrame, candidates: tuple[str, ...]) -> str \| None: |
| dataverse_backend/app/services/analysis_pipeline.py | 538 | def _financial_dataset_analysis(df: pd.DataFrame) -> dict[str, Any]: |
| dataverse_backend/app/services/analysis_pipeline.py | 557 | def _find(*candidates: str) -> str \| None: |

## Environment Configuration Presence

Values are intentionally redacted. This table only records whether variables exist and whether they have a non-empty value.

| file | variable | present | has_value |
| --- | --- | --- | --- |
| .env | OPENAI_API_KEY | Yes | Yes |
| .env | OPENAI_CHAT_MODEL | No | No |
| .env | LLM_PROVIDER | No | No |
| .env | USE_LLM_NARRATION | No | No |
| .env | SUPABASE_URL | No | No |
| .env | SUPABASE_SERVICE_ROLE_KEY | No | No |
| .env | SUPABASE_ANON_KEY | No | No |
| dataverse_backend/.env | OPENAI_API_KEY | Yes | Yes |
| dataverse_backend/.env | OPENAI_CHAT_MODEL | Yes | Yes |
| dataverse_backend/.env | LLM_PROVIDER | Yes | Yes |
| dataverse_backend/.env | USE_LLM_NARRATION | No | No |
| dataverse_backend/.env | SUPABASE_URL | No | No |
| dataverse_backend/.env | SUPABASE_SERVICE_ROLE_KEY | No | No |
| dataverse_backend/.env | SUPABASE_ANON_KEY | No | No |
| .env.example | OPENAI_API_KEY | Yes | No |
| .env.example | OPENAI_CHAT_MODEL | Yes | Yes |
| .env.example | LLM_PROVIDER | Yes | Yes |
| .env.example | USE_LLM_NARRATION | Yes | Yes |
| .env.example | SUPABASE_URL | Yes | No |
| .env.example | SUPABASE_SERVICE_ROLE_KEY | Yes | No |
| .env.example | SUPABASE_ANON_KEY | Yes | No |
| dataverse_backend/.env.example | OPENAI_API_KEY | Yes | No |
| dataverse_backend/.env.example | OPENAI_CHAT_MODEL | Yes | Yes |
| dataverse_backend/.env.example | LLM_PROVIDER | Yes | Yes |
| dataverse_backend/.env.example | USE_LLM_NARRATION | Yes | Yes |
| dataverse_backend/.env.example | SUPABASE_URL | No | No |
| dataverse_backend/.env.example | SUPABASE_SERVICE_ROLE_KEY | No | No |
| dataverse_backend/.env.example | SUPABASE_ANON_KEY | No | No |
| frontend/.env.example | OPENAI_API_KEY | No | No |
| frontend/.env.example | OPENAI_CHAT_MODEL | No | No |
| frontend/.env.example | LLM_PROVIDER | No | No |
| frontend/.env.example | USE_LLM_NARRATION | No | No |
| frontend/.env.example | SUPABASE_URL | No | No |
| frontend/.env.example | SUPABASE_SERVICE_ROLE_KEY | No | No |
| frontend/.env.example | SUPABASE_ANON_KEY | No | No |

## Endpoint Checks
| Endpoint | Result |
| --- | --- |
| GET /health/live | Not run |
| POST /api/sessions | Not run |
| POST /api/sessions/{session_id}/datasets/upload | Not run |
| POST /api/sessions/{session_id}/analyze | Not run |
| GET /api/reports/{report_id}/download?format=html | Implemented in report_routes.py; URL generated when report exists |
| GET /api/reports/{report_id}/download?format=pdf | Implemented in report_routes.py; URL generated when report exists |

## Output Files Generated
| Path | Status |
| --- | --- |
| outputs/chapter_6_data_collection_analysis.md | Generated |
| outputs/chapter_7_results_discussion.md | Generated |
| outputs/chapter_6_tables.md | Generated |
| outputs/chapter_7_tables.md | Generated |
| outputs/chapter_6_7_figures_list.md | Generated |
| outputs/chapter_6_7_evidence_log.md | Generated |
| report/chapter_outputs/*.png | Generated |

## Missing or Environment-Dependent Items
| Item | Status | Recommended Addition |
| --- | --- | --- |
| Human-readable labels for encoded categorical columns | Not found / Not implemented | Add lookup tables for region, city, category, subcategory, customer_type, and payment_method. |
| Supabase live connection | Environment-dependent | Configure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY, then run upload/report tests against Supabase. |
| Docker container build/start | Environment-dependent | Run docker compose build and docker compose up when Docker Desktop is available. |
| LLM live OpenAI response | Environment-dependent | Run backend with OPENAI_API_KEY and network access; do not expose key in logs. |
| Browser screenshot of frontend upload flow | Manual screenshot recommended | Start backend/frontend, upload dataset in UI, screenshot upload success and generated report cards. |
