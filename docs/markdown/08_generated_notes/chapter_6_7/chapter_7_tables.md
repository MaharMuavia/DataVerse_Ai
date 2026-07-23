# Chapter 7 Tables

## System Test Cases and Results
| Test Case | Expected | Actual Result | Evidence |
| --- | --- | --- | --- |
| Dataset CSV load | CSV parsed into DataFrame | Passed | 35000 rows / 21 columns |
| Backend health | 200 OK | Not run | /health/live |
| Create session | Session ID returned | Not run | session_id_present=None |
| Upload dataset endpoint | Dataset ID returned | Not run | dataset_id_present=None |
| Analyze endpoint | Charts, agents, report payload | Not run | charts=None; agents=None |
| Report HTML export | HTML URL/payload | Passed | html_url_present=None; html_bytes=40822 |
| Report PDF export | PDF URL/payload | Passed | pdf_url_present=None; pdf_bytes=19743 |

## Dataset Analysis Results
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

## KPI Results
| KPI | Result |
| --- | --- |
| Total Sales | $2,248,662.62 |
| Total Profit | $336,938.93 |
| Total Quantity | 69,546 |
| Average Sales per Row | $64.25 |
| Overall Profit Margin | 14.98% |
| Best Region by Sales | 2.0 |
| Best Category by Sales | 1.0 |
| Best Category by Profit | 1.0 |
| Best Store by Sales | 27.0 |

## Chart Output Results
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

## Report Generation Results
| Output | Status | Path |
| --- | --- | --- |
| Chapter 6 Markdown | Generated | outputs/chapter_6_data_collection_analysis.md |
| Chapter 7 Markdown | Generated | outputs/chapter_7_results_discussion.md |
| HTML report export | Passed | None |
| PDF report export | Passed | None |

## API Endpoint Results
| Endpoint | Result | Purpose |
| --- | --- | --- |
| GET /health/live | Not run | Backend liveness |
| POST /api/sessions | Not run | Create chat session |
| POST /api/sessions/{session_id}/datasets/upload | Not run | Upload dataset |
| POST /api/sessions/{session_id}/analyze | Not run | Analyze dataset and generate report |
| GET /api/reports/{report_id}/download?format=html | Implemented | HTML report download |
| GET /api/reports/{report_id}/download?format=pdf | Implemented | PDF report download |

## Frontend/Backend Integration Results
| Area | Status | Evidence |
| --- | --- | --- |
| Frontend upload | Implemented | frontend/lib/dataverse-api.ts uploadDataset -> /sessions/{sessionId}/datasets/upload |
| Backend upload | Implemented | dataverse_backend/app/api/session_routes.py upload_dataset_to_session |
| CSV/Excel parser | Implemented | dataverse_backend/app/api/upload_parsing.py parse_uploaded_dataframe uses pandas read_csv/read_excel |
| Report download | Implemented | dataverse_backend/app/api/report_routes.py download_report supports pdf/html |
| Supabase | Optional / local fallback | SupabaseClient.configured requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY; LocalPersistence used otherwise |
| Docker | Partially Ready | docker-compose.yml, dataverse_backend/Dockerfile, frontend/Dockerfile |

## Agent and OpenAI Results
| Check | Result | Evidence |
| --- | --- | --- |
| Agent files | Implemented | dataverse_backend/app/agents/dataset_agent.py; dataverse_backend/app/agents/analyst_agent.py; session_service starts DatasetAgent and AnalystAgent runs |
| Agent Provider | OpenAI capable / deterministic fallback | dataverse_backend/app/services/llm_provider.py supports openai, gemini, anthropic, deepanalyze, deterministic |
| API Key Loaded | Yes in local .env files, value redacted | .env and dataverse_backend/.env contain OPENAI_API_KEY with a value |
| Mock Mode Enabled | Deterministic fallback available; app warns mock mode when key missing | dataverse_backend/app/main.py lifespan warning; llm_provider.py deterministic fallback |
| Agent Test Result | Not found / Not implemented | API analysis agent_count=None |
| Prediction Result | complete | Model=RandomForestClassifier; Target=category |
| XAI Result | fallback | Project implements XAI in app/services/xai.py; generation run used run_xai=False to avoid external/slow SHAP path. |

## Supabase and Docker Results
| Area | Status | Evidence |
| --- | --- | --- |
| Supabase usage | Used optionally | dataverse_backend/app/services/supabase_client.py |
| SUPABASE_URL | Present in examples; not found with value in checked local env status | outputs/chapter_6_7_evidence_log.md |
| Service role key frontend exposure | Protected by backend-only client | supabase_client.py comment and backend service use |
| Dockerfile backend | Present | dataverse_backend/Dockerfile |
| Dockerfile frontend | Present | frontend/Dockerfile |
| docker-compose | Present | docker-compose.yml |
| Container build | Checked separately in evidence log if Docker command is available | outputs/chapter_6_7_evidence_log.md |

## Manual Analysis vs DataVerse AI
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
