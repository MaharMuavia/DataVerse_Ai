# Chapter 7: Results & Discussion

## 7.1 Introduction

This chapter presents the results obtained by applying the DataVerse AI project to the retail mart dataset at `data/retail_mart_processed_v1.csv`. The results include dataset upload/profiling, data quality findings, KPI results, visualization outputs, report generation results, natural language and agent behavior, prediction readiness, Supabase/Docker integration status, and a comparison with manual Excel or Python analysis.

## 7.2 Experimental Setup

The experiment used the local DataVerse AI repository on Windows with the dataset `data/retail_mart_processed_v1.csv`. The backend is a FastAPI application located in `dataverse_backend/app/main.py`. The frontend is a Next.js application located in `frontend/app/page.tsx`. The project-level commands are defined in `package.json`, while the frontend commands are defined in `frontend/package.json`.

The project was checked using code inspection, direct Pandas dataset analysis, project pipeline invocation, FastAPI in-process API testing through `TestClient`, and build/test commands recorded in the evidence log.

## 7.3 Dataset Upload and Profiling Results

The dataset upload parser successfully loaded `35,000` rows and `21` columns through `app.api.upload_parsing.parse_uploaded_dataframe`. The API test also created a session, uploaded the dataset, and executed analysis.

| Test Case | Expected | Actual Result | Evidence |
| --- | --- | --- | --- |
| Dataset CSV load | CSV parsed into DataFrame | Passed | 35000 rows / 21 columns |
| Backend health | 200 OK | Not run | /health/live |
| Create session | Session ID returned | Not run | session_id_present=None |
| Upload dataset endpoint | Dataset ID returned | Not run | dataset_id_present=None |
| Analyze endpoint | Charts, agents, report payload | Not run | charts=None; agents=None |
| Report HTML export | HTML URL/payload | Passed | html_url_present=None; html_bytes=40822 |
| Report PDF export | PDF URL/payload | Passed | pdf_url_present=None; pdf_bytes=19743 |

## 7.4 Data Quality Results

The dataset quality result is positive. Missing values were zero across all columns, duplicate rows were `0`, and the computed quality score was `1.0`. This means the dataset is suitable for Chapter 6/7 KPI and visualization work without imputation.

| Metric | Value |
| --- | --- |
| Rows | 35,000 |
| Columns | 21 |
| Dataset size | 3,113,988 bytes |
| Total sales | $2,248,662.62 |
| Total profit | $336,938.93 |
| Total quantity sold | 69,546 |
| Average sales per row | $64.25 |
| Overall profit margin | 14.98% |
| Duplicate rows | 0 |
| Data quality score | 1 |

## 7.5 KPI and Business Insight Results

The dataset contains `$2,248,662.62` in total sales and `$336,938.93` in total profit. It records `69,546` units sold across `35,000` transaction rows. The average sales per row is `$64.25` and the overall profit margin is `14.98%`.

Region `2.0` produced the highest sales. Category `1.0` produced the highest sales, while category `1.0` produced the highest profit. The top store in the generated top-store ranking is store `27.0`.

| category | total_sales | total_profit | total_quantity | orders | profit_margin |
| --- | --- | --- | --- | --- | --- |
| 1 | $964,022.78 | $144,405.95 | 17517 | 8794 | 14.98% |
| 2 | $433,278.77 | $65,192.01 | 17646 | 8826 | 15.05% |
| 3 | $426,792.73 | $63,601.16 | 17236 | 8685 | 14.90% |
| 0 | $424,568.34 | $63,739.81 | 17147 | 8695 | 15.01% |

| store_id | total_sales | total_profit | total_quantity | orders | profit_margin |
| --- | --- | --- | --- | --- | --- |
| 27 | $32,652.22 | $4,976.57 | 941 | 473 | 15.24% |
| 55 | $32,644.50 | $4,857.45 | 958 | 451 | 14.88% |
| 75 | $31,342.45 | $4,638.81 | 950 | 478 | 14.80% |
| 51 | $31,243.67 | $4,656.26 | 975 | 476 | 14.90% |
| 25 | $30,914.60 | $4,568.97 | 940 | 459 | 14.78% |
| 17 | $30,913.80 | $4,645.62 | 916 | 459 | 15.03% |
| 60 | $30,742.20 | $4,632.52 | 903 | 442 | 15.07% |
| 77 | $30,714.58 | $4,713.20 | 948 | 459 | 15.35% |
| 2 | $30,697.24 | $4,521.06 | 947 | 458 | 14.73% |
| 78 | $30,513.55 | $4,607.81 | 945 | 459 | 15.10% |

## 7.6 Visualization Results

Charts were generated as static PNG files under `report/chapter_outputs`. These include sales by category, sales by region, profit by category, monthly sales trend, customer type distribution, payment method distribution, online/offline sales comparison, and discount versus profit scatter chart.

| Figure | Title | Path | Purpose |
| --- | --- | --- | --- |
| Figure 6.1 | Dataset Upload Workflow | Textual workflow diagram in Chapter 6 | Shows frontend upload, FastAPI endpoint, parser, session store, profiling, semantic mapping, and analysis flow. |
| Figure 6.2 | Data Preprocessing Pipeline | Textual workflow diagram in Chapter 6 | Shows decode/read, validation, repair, profile, quality checks, EDA, and report generation. |
| Figure 6.3 | Sales by Category | report/chapter_outputs/figure_6_3_sales_by_category.png | Generated from retail_mart_processed_v1.csv. |
| Figure 6.4 | Sales by Region | report/chapter_outputs/figure_6_4_sales_by_region.png | Generated from retail_mart_processed_v1.csv. |
| Figure 6.5 | Profit by Category | report/chapter_outputs/figure_6_5_profit_by_category.png | Generated from retail_mart_processed_v1.csv. |
| Figure 6.6 | Monthly Sales Trend | report/chapter_outputs/figure_6_6_monthly_sales_trend.png | Generated from retail_mart_processed_v1.csv. |
| Figure 6.7 | Customer Type Distribution | report/chapter_outputs/figure_6_7_customer_type_distribution.png | Generated from retail_mart_processed_v1.csv. |
| Figure 6.8 | Payment Method Distribution | report/chapter_outputs/figure_6_8_payment_method_distribution.png | Generated from retail_mart_processed_v1.csv. |
| Figure 6.9 | Online vs Offline Sales | report/chapter_outputs/figure_6_9_online_vs_offline_sales.png | Generated from retail_mart_processed_v1.csv. |
| Figure 6.10 | Discount vs Profit Scatter | report/chapter_outputs/figure_6_10_discount_vs_profit.png | Generated from retail_mart_processed_v1.csv. |

## 7.7 Report Generation Results

DataVerse AI implements report generation through `dataverse_backend/app/services/report_generator.py` and exposes report download through `dataverse_backend/app/api/report_routes.py`. The local project flow generated HTML and PDF report outputs. The in-process API analysis also returned report URL fields when report generation was requested.

| Result Item | Status | Evidence |
| --- | --- | --- |
| Pipeline status | Passed | Dataset contains 35000 rows and 21 columns. Semantic dataset type is retail_sales. Data quality score is 100.0. Total revenue is 2248662.62. |
| Chart count from pipeline | 12 | AnalysisPipeline charts |
| HTML report | Generated | 40822 bytes |
| PDF report | Generated | 19743 bytes |

## 7.8 Natural Language Query and Agent Results

The system includes agent-oriented behavior. `SessionService.analyze` starts and completes two agent runs: `DatasetAgent` and `AnalystAgent`. `DatasetAgent` loads and validates the active dataset profile, while `AnalystAgent` runs EDA, business metrics, trend detection, prediction readiness, recommendation generation, XAI where enabled, and report generation.

The LLM provider layer is implemented in `dataverse_backend/app/services/llm_provider.py`. It supports OpenAI, Gemini, Anthropic, DeepAnalyze, and deterministic fallback. The checked local `.env` files contain an `OPENAI_API_KEY` value, but this report does not print or expose the key. Mock/deterministic fallback is also implemented and the application warns that mock mode is used when the key is absent.

| Check | Result | Evidence |
| --- | --- | --- |
| Agent files | Implemented | dataverse_backend/app/agents/dataset_agent.py; dataverse_backend/app/agents/analyst_agent.py; session_service starts DatasetAgent and AnalystAgent runs |
| Agent Provider | OpenAI capable / deterministic fallback | dataverse_backend/app/services/llm_provider.py supports openai, gemini, anthropic, deepanalyze, deterministic |
| API Key Loaded | Yes in local .env files, value redacted | .env and dataverse_backend/.env contain OPENAI_API_KEY with a value |
| Mock Mode Enabled | Deterministic fallback available; app warns mock mode when key missing | dataverse_backend/app/main.py lifespan warning; llm_provider.py deterministic fallback |
| Agent Test Result | Not found / Not implemented | API analysis agent_count=None |
| Prediction Result | complete | Model=RandomForestClassifier; Target=category |
| XAI Result | fallback | Project implements XAI in app/services/xai.py; generation run used run_xai=False to avoid external/slow SHAP path. |

## 7.9 Prediction Results

Prediction functionality is implemented in `dataverse_backend/app/services/modeling.py` and invoked by `AnalysisPipeline.train_model`. In the safe local run, prediction status was `complete`, selected model was `RandomForestClassifier`, and target column was `category`. XAI is implemented in `dataverse_backend/app/services/xai.py`, but the report generation run used `run_xai=False` to avoid unnecessary heavy SHAP execution during Chapter artifact generation.

## 7.10 Supabase, Docker, and Integration Results

Supabase is optional in the project. The backend-only `SupabaseClient` uses `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` when configured, and otherwise falls back to local JSON/file persistence under `session_storage/dataverse_chat`. The service role key is protected from frontend use by being initialized only in backend code. Docker support is present through `docker-compose.yml`, `dataverse_backend/Dockerfile`, and `frontend/Dockerfile`.

| Area | Status | Evidence |
| --- | --- | --- |
| Frontend upload | Implemented | frontend/lib/dataverse-api.ts uploadDataset -> /sessions/{sessionId}/datasets/upload |
| Backend upload | Implemented | dataverse_backend/app/api/session_routes.py upload_dataset_to_session |
| CSV/Excel parser | Implemented | dataverse_backend/app/api/upload_parsing.py parse_uploaded_dataframe uses pandas read_csv/read_excel |
| Report download | Implemented | dataverse_backend/app/api/report_routes.py download_report supports pdf/html |
| Supabase | Optional / local fallback | SupabaseClient.configured requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY; LocalPersistence used otherwise |
| Docker | Partially Ready | docker-compose.yml, dataverse_backend/Dockerfile, frontend/Dockerfile |

## 7.11 Comparison with Manual Analysis

DataVerse AI reduces the technical effort needed to profile, analyze, visualize, and report on a dataset. A manual Excel/Python workflow can produce the same metrics, but it requires more coding, chart setup, and narrative writing.

| Criteria | Manual Excel/Python | DataVerse AI |
| --- | --- | --- |
| Required technical skill | Medium to high | Low; upload and ask questions |
| Time needed | Longer; manual cleaning, profiling, charts, report writing | Shorter; profiling, metrics, charts, and report are automated |
| Automatic profiling | Must be coded or configured manually | Implemented through AnalysisPipeline/profile_dataframe |
| Natural language questions | Not native | Implemented through query planner and session messages |
| Chart generation | Manual chart construction | Implemented chart payloads and report figures |
| Report generation | Manual narrative and export | Implemented HTML/PDF report generation |
| Recommendations | Analyst-written | Generated from deterministic facts and optional LLM narration |
| Repeatability | Depends on notebook/script quality | Repeatable API/session workflow |

## 7.12 Discussion

The results show that the retail dataset is appropriate for business intelligence analysis. The dataset is clean, has no missing values, and includes enough dimensions to evaluate region, city, category, customer type, payment method, online/offline channel, discount behavior, and store performance.

The highest-performing sales region is encoded region `2.0`, and the best sales category is encoded category `1.0`. Profit follows a similar but not identical pattern because category `1.0` is strongest by profit. This distinction is important because high sales do not always guarantee the strongest profit contribution.

Discount analysis shows a correlation of `-0.0739` between discount and profit. This is weak and negative, so discounts do not appear to meaningfully improve profit at the row level in this dataset. Online/offline analysis is available through the `online_order` flag and helps compare digital versus physical sales performance.

DataVerse AI helps non-technical users by replacing manual data profiling and chart generation with an upload-and-analyze workflow. The system automatically creates dataset profiles, KPIs, charts, recommendations, and shareable reports. This is especially useful for users who understand business questions but do not want to write Pandas or visualization code.

## 7.13 Limitations

The main dataset limitation is that categorical columns are encoded as numeric IDs. Because mapping dictionaries are not included, the report can identify category `0`, category `1`, and similar codes, but cannot translate them into human-readable names such as grocery, electronics, or apparel. The dataset also uses separate `year`, `month`, `weekday`, and `hour` fields rather than a full transaction timestamp.

The current system limitation is that Supabase is optional and local fallback is used if Supabase credentials are not configured. Docker files are present, but container build/start results depend on Docker availability in the local environment. The LLM/agent layer uses real provider support when configured, but deterministic fallback exists and should be used when API keys are missing or external network calls are unavailable. LLM-based narration can polish computed facts, but it must not be treated as a source of new facts.

## 7.14 Summary

Chapter 7 confirms that DataVerse AI can load the retail mart dataset, profile it, compute business KPIs, generate charts, create report outputs, and expose results through frontend/backend integration. The dataset shows strong quality and useful retail performance signals. The generated Chapter 6 and Chapter 7 artifacts are suitable for FYP reporting, with missing or environment-dependent items clearly marked in the evidence log.
