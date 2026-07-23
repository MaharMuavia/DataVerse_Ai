# Chapter 6: Data Collection & Analysis

## 6.1 Introduction

This chapter presents the data collection and analysis work completed for the DataVerse AI final year project. The analysis is based on the actual dataset located at `data/retail_mart_processed_v1.csv` and on the implemented DataVerse AI codebase. The dataset represents a retail mart transaction table with encoded store, geography, product, customer, payment, channel, and time fields. The analysis focuses on data quality, preprocessing, exploratory data analysis, business KPIs, and visualization planning.

## 6.2 Dataset Source and Collection

The dataset used in this chapter is `retail_mart_processed_v1.csv`. It is stored locally inside the project repository at `data/retail_mart_processed_v1.csv`. The file size is `3,113,988` bytes and the dataset contains `35,000` rows and `21` columns.

The dataset appears to be a processed retail transaction dataset. Encoded columns such as `region`, `city`, `category`, `subcategory`, `customer_type`, and `payment_method` represent categorical business dimensions, while columns such as `unit_price`, `quantity`, `discount`, `total_sales`, `profit`, `discount_value`, and `profit_margin` represent business measures. The purpose of the dataset is to support sales, profit, discount, channel, customer, payment, time, and store performance analysis.

| Property | Value |
| --- | --- |
| Dataset name | retail_mart_processed_v1.csv |
| Dataset path | data/retail_mart_processed_v1.csv |
| Dataset purpose | Retail transaction analysis for sales, profit, discount, customer, payment, online/offline, store, and time-based performance. |
| Numeric business columns | unit_price, quantity, discount, total_sales, profit, price_qty, discount_value, profit_margin |
| Categorical / encoded columns | store_id, region, city, category, subcategory, customer_type, payment_method, online_order, stockout_flag, weekday, month, year, hour |
| Date/time component columns | weekday, month, year, hour |
| Target / important business columns | total_sales, profit, quantity, profit_margin, discount |

## 6.3 Dataset Loading Process

DataVerse AI contains an implemented upload and loading flow. The frontend file `frontend/lib/dataverse-api.ts` defines `uploadDataset`, which creates `FormData` and posts the selected file to `/api/sessions/{session_id}/datasets/upload`. The visible upload experience is implemented in `frontend/app/page.tsx`, where the user uploads a CSV or Excel file from the chat/dashboard interface.

On the backend, `dataverse_backend/app/api/session_routes.py` defines `upload_dataset_to_session`. This endpoint reads the uploaded file, checks for empty content, enforces `MAX_UPLOAD_SIZE_MB`, and allows only `.csv`, `.xlsx`, and `.xls` files. The actual CSV/Excel parsing is implemented in `dataverse_backend/app/api/upload_parsing.py` through `parse_uploaded_dataframe`. CSV files are decoded using multiple encodings, dialects are detected with `csv.Sniffer`, malformed rows can be repaired, and Pandas is used through `pd.read_csv`. Excel files are read with `pd.read_excel`.

After parsing, `dataverse_backend/app/services/session_service.py` stores the dataset through `upload_dataset`. If Supabase is configured, files are uploaded to Supabase Storage; otherwise the local fallback writes into `session_storage/dataverse_chat`. The same method calls `AnalysisPipeline().profile_dataset(df)` and `SemanticMapper().map_dataframe(df)` to generate metadata, schema profile, preview rows, and semantic mapping.

Figure 6.1: Dataset Upload Workflow

```text
Frontend upload component
  -> frontend/lib/dataverse-api.ts uploadDataset()
  -> POST /api/sessions/{session_id}/datasets/upload
  -> session_routes.upload_dataset_to_session()
  -> session_service.upload_dataset()
  -> upload_parsing.parse_uploaded_dataframe()
  -> Pandas read_csv/read_excel
  -> local session storage or Supabase storage
  -> AnalysisPipeline.profile_dataset()
  -> SemanticMapper.map_dataframe()
  -> dataset metadata returned to frontend
```

## 6.4 Dataset Description

The dataset columns are:

`store_id, region, city, category, subcategory, unit_price, quantity, discount, total_sales, profit, customer_type, payment_method, online_order, stockout_flag, weekday, month, year, hour, price_qty, discount_value, profit_margin`

All columns were read successfully by Pandas. Although all columns are encoded as numeric types, the business interpretation separates encoded categorical fields from continuous numeric measures.

| Column | Pandas Type | Analytical Role | Unique Values | Missing Values |
| --- | --- | --- | --- | --- |
| store_id | int64 | Categorical / encoded | 80 | 0 |
| region | int64 | Categorical / encoded | 4 | 0 |
| city | int64 | Categorical / encoded | 7 | 0 |
| category | int64 | Categorical / encoded | 4 | 0 |
| subcategory | int64 | Categorical / encoded | 10 | 0 |
| unit_price | float64 | Numeric measure | 8713 | 0 |
| quantity | int64 | Numeric measure | 4 | 0 |
| discount | float64 | Numeric measure | 5 | 0 |
| total_sales | float64 | Numeric measure | 14187 | 0 |
| profit | float64 | Numeric measure | 4186 | 0 |
| customer_type | int64 | Categorical / encoded | 2 | 0 |
| payment_method | int64 | Categorical / encoded | 4 | 0 |
| online_order | int64 | Categorical / encoded | 2 | 0 |
| stockout_flag | int64 | Categorical / encoded | 2 | 0 |
| weekday | int64 | Categorical / encoded | 7 | 0 |
| month | int64 | Categorical / encoded | 12 | 0 |
| year | int64 | Categorical / encoded | 3 | 0 |
| hour | int64 | Categorical / encoded | 24 | 0 |
| price_qty | float64 | Numeric measure | 13915 | 0 |
| discount_value | float64 | Numeric measure | 14775 | 0 |
| profit_margin | float64 | Numeric measure | 33701 | 0 |

## 6.5 Data Preprocessing

The retail mart dataset was already processed before this report because it contains normalized numeric/encoded fields and derived columns such as `price_qty`, `discount_value`, and `profit_margin`. The current project still performs important preprocessing during upload: file validation, encoding detection, CSV dialect detection, row repair for inconsistent CSVs, empty-file checks, schema profiling, data quality scoring, semantic mapping, and JSON-safe conversion for API responses.

Figure 6.2: Data Preprocessing Pipeline

```text
Raw CSV/Excel file
  -> extension and size validation
  -> decode CSV / read Excel bytes
  -> detect delimiter and repair row-width issues where needed
  -> load Pandas DataFrame
  -> validate non-empty rows and columns
  -> infer schema, data types, missingness, uniqueness, and semantic roles
  -> compute quality, EDA, outliers, trends, correlations, business metrics
  -> produce charts, tables, recommendations, and report export payload
```

In this dataset, missing-value analysis found no missing cells. Duplicate detection found `0` duplicate rows. Constant-column detection found `no constant columns`. No high-cardinality columns crossed the 50% uniqueness threshold.

| Column | Missing Values | Missing % |
| --- | --- | --- |
| store_id | 0 | 0.00% |
| region | 0 | 0.00% |
| city | 0 | 0.00% |
| category | 0 | 0.00% |
| subcategory | 0 | 0.00% |
| unit_price | 0 | 0.00% |
| quantity | 0 | 0.00% |
| discount | 0 | 0.00% |
| total_sales | 0 | 0.00% |
| profit | 0 | 0.00% |
| customer_type | 0 | 0.00% |
| payment_method | 0 | 0.00% |
| online_order | 0 | 0.00% |
| stockout_flag | 0 | 0.00% |
| weekday | 0 | 0.00% |
| month | 0 | 0.00% |
| year | 0 | 0.00% |
| hour | 0 | 0.00% |
| price_qty | 0 | 0.00% |
| discount_value | 0 | 0.00% |
| profit_margin | 0 | 0.00% |

## 6.6 Data Quality Analysis

The dataset quality is strong for the current analysis because all required business columns are present, there are no missing values, and no duplicate rows were detected. The computed data quality score is `1.0` on a 0 to 1 scale using missing-cell and duplicate-row penalties.

| Column | Mean | Median | Min | Max | Std Dev |
| --- | --- | --- | --- | --- | --- |
| unit_price | 35.28 | 32.20 | 0 | 134.56 | 23.01 |
| quantity | 1.99 | 2 | 1 | 4 | 1.07 |
| discount | 0.08 | 0.10 | 0 | 0.20 | 0.07 |
| total_sales | 64.25 | 46.32 | 0 | 495.44 | 59.00 |
| profit | 9.63 | 6.34 | 0 | 101.63 | 10.19 |
| price_qty | 70.17 | 50.68 | 0 | 514.32 | 64.16 |
| discount_value | 5.92 | 2.49 | 0 | 102.86 | 9.02 |
| profit_margin | 0.14 | 0.14 | 0 | 0.25 | 0.06 |

| Column | Unique Values | Top Value | Top Count | Top Share |
| --- | --- | --- | --- | --- |
| store_id | 80 | 64 | 485 | 1.39% |
| region | 4 | 2 | 19905 | 56.87% |
| city | 7 | 5 | 5059 | 14.45% |
| category | 4 | 2 | 8826 | 25.22% |
| subcategory | 10 | 2 | 4385 | 12.53% |
| customer_type | 2 | 0 | 17522 | 50.06% |
| payment_method | 4 | 3 | 8845 | 25.27% |
| online_order | 2 | 1 | 17570 | 50.20% |
| stockout_flag | 2 | 0 | 27947 | 79.85% |
| weekday | 7 | 0 | 5115 | 14.61% |
| month | 12 | 5 | 3036 | 8.67% |
| year | 3 | 2024 | 17542 | 50.12% |
| hour | 24 | 2 | 1513 | 4.32% |

Outliers were detected using the Interquartile Range method. Numeric values below `Q1 - 1.5 * IQR` or above `Q3 + 1.5 * IQR` were counted as outliers.

| Column | Q1 | Q3 | IQR | Lower Fence | Upper Fence | Outliers | Outlier % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| unit_price | 17.01 | 50.27 | 33.26 | -32.88 | 100.16 | 198 | 0.57% |
| quantity | 1 | 3 | 2 | -2 | 6 | 0 | 0.00% |
| discount | 0 | 0.15 | 0.15 | -0.22 | 0.38 | 0 | 0.00% |
| total_sales | 22.89 | 86.54 | 63.65 | -72.59 | 182.02 | 1904 | 5.44% |
| profit | 2.88 | 12.65 | 9.77 | -11.78 | 27.31 | 2266 | 6.47% |
| price_qty | 25.26 | 94.50 | 69.24 | -78.60 | 198.37 | 1897 | 5.42% |
| discount_value | 0 | 7.98 | 7.98 | -11.97 | 19.95 | 2562 | 7.32% |
| profit_margin | 0.09 | 0.19 | 0.10 | -0.05 | 0.34 | 0 | 0.00% |

## 6.7 Exploratory Data Analysis

The total sales in the dataset are `$2,248,662.62` and total profit is `$336,938.93`. Total quantity sold is `69,546` units. The average sales value per row is `$64.25`, and the overall profit margin is `14.98%`.

Region `2.0` is the strongest region by sales with `$1,279,763.60` in sales and `$191,713.72` in profit. Category `1.0` is the strongest category by sales with `$964,022.78`. Category `1.0` is the strongest category by profit with `$144,405.95`. Store `27.0` is the top store among the top-ten store ranking generated for this report.

Figure 6.3: Sales by Category

![Sales by Category](../../../../report/chapter_outputs/figure_6_3_sales_by_category.png)

Figure 6.4: Sales by Region

![Sales by Region](../../../../report/chapter_outputs/figure_6_4_sales_by_region.png)

Figure 6.5: Profit by Category

![Profit by Category](../../../../report/chapter_outputs/figure_6_5_profit_by_category.png)

Figure 6.6: Monthly Sales Trend

![Monthly Sales Trend](../../../../report/chapter_outputs/figure_6_6_monthly_sales_trend.png)

The time-series window runs from January 2023 through January 2025. The January 2025 value is based on only 42 rows, so it should be treated as a partial-period point rather than a full-month decline.

| category | total_sales | total_profit | total_quantity | orders | profit_margin |
| --- | --- | --- | --- | --- | --- |
| 1 | $964,022.78 | $144,405.95 | 17517 | 8794 | 14.98% |
| 2 | $433,278.77 | $65,192.01 | 17646 | 8826 | 15.05% |
| 3 | $426,792.73 | $63,601.16 | 17236 | 8685 | 14.90% |
| 0 | $424,568.34 | $63,739.81 | 17147 | 8695 | 15.01% |

| region | total_sales | total_profit | total_quantity | orders | profit_margin |
| --- | --- | --- | --- | --- | --- |
| 2 | $1,279,763.60 | $191,713.72 | 39466 | 19905 | 14.98% |
| 0 | $328,285.13 | $49,646.34 | 10123 | 5051 | 15.12% |
| 1 | $320,928.87 | $47,777.62 | 10033 | 5059 | 14.89% |
| 3 | $319,685.02 | $47,801.25 | 9924 | 4985 | 14.95% |

| city | total_sales | total_profit | total_quantity | orders | profit_margin |
| --- | --- | --- | --- | --- | --- |
| 0 | $328,830.32 | $49,133.91 | 9967 | 5018 | 14.94% |
| 1 | $328,285.13 | $49,646.34 | 10123 | 5051 | 15.12% |
| 4 | $322,475.07 | $48,097.48 | 9956 | 4974 | 14.92% |
| 5 | $320,928.87 | $47,777.62 | 10033 | 5059 | 14.89% |
| 2 | $319,685.02 | $47,801.25 | 9924 | 4985 | 14.95% |
| 3 | $318,407.97 | $47,765.26 | 9837 | 4950 | 15.00% |
| 6 | $310,050.24 | $46,717.07 | 9706 | 4963 | 15.07% |

## 6.8 Business Metrics and KPI Analysis

The main business KPIs extracted from the dataset are shown below.

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

Customer type analysis shows that encoded customer type `0.0` contributes the largest sales total. Payment-method analysis and online/offline analysis were also computed from the encoded payment and channel columns.

Figure 6.7: Customer Type Distribution

![Customer Type Distribution](../../../../report/chapter_outputs/figure_6_7_customer_type_distribution.png)

Figure 6.8: Payment Method Distribution

![Payment Method Distribution](../../../../report/chapter_outputs/figure_6_8_payment_method_distribution.png)

Figure 6.9: Online vs Offline Sales

![Online vs Offline Sales](../../../../report/chapter_outputs/figure_6_9_online_vs_offline_sales.png)

The discount/profit Pearson correlation is `-0.0739`. This indicates a weak negative relationship in this dataset, meaning higher discounts are associated with slightly lower profit at the row level.

Figure 6.10: Discount vs Profit Scatter Chart

![Discount vs Profit](../../../../report/chapter_outputs/figure_6_10_discount_vs_profit.png)

| customer_type | total_sales | total_profit | total_quantity | orders | profit_margin |
| --- | --- | --- | --- | --- | --- |
| 0 | $1,136,762.84 | $170,677.48 | 34875 | 17522 | 15.01% |
| 1 | $1,111,899.78 | $166,261.45 | 34671 | 17478 | 14.95% |

| payment_method | total_sales | total_profit | total_quantity | orders | profit_margin |
| --- | --- | --- | --- | --- | --- |
| 2 | $569,968.83 | $85,175.19 | 17401 | 8766 | 14.94% |
| 3 | $563,971.83 | $85,219.69 | 17492 | 8845 | 15.11% |
| 1 | $560,863.06 | $83,464.06 | 17421 | 8742 | 14.88% |
| 0 | $553,858.90 | $83,079.99 | 17232 | 8647 | 15.00% |

| online_order | total_sales | total_profit | total_quantity | orders | profit_margin |
| --- | --- | --- | --- | --- | --- |
| 1 | $1,129,750.25 | $169,789.49 | 34956 | 17570 | 15.03% |
| 0 | $1,118,912.37 | $167,149.44 | 34590 | 17430 | 14.94% |

| discount | total_sales | total_profit | avg_profit | orders |
| --- | --- | --- | --- | --- |
| 0 | $803,438.05 | $120,942.04 | $10.45 | 11568 |
| 0.05 | $383,225.49 | $57,605.96 | $9.98 | 5773 |
| 0.10 | $377,970.56 | $56,302.83 | $9.50 | 5929 |
| 0.15 | $351,711.37 | $52,771.19 | $9.01 | 5854 |
| 0.20 | $332,317.15 | $49,316.91 | $8.39 | 5876 |

## 6.9 Visualization and Chart Planning

The report-ready figures generated for Chapter 6 and Chapter 7 are stored in `report/chapter_outputs`. The selected chart types follow the data relationship: bar charts for category and region comparisons, a line chart for monthly time trend, a pie chart for customer-type composition, and a scatter chart for the discount-profit relationship.

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

## 6.10 Tools and Technologies Used

The analysis used Python, Pandas, Matplotlib, FastAPI, Next.js, and the implemented DataVerse AI backend services. Project-specific analysis evidence came from `dataverse_backend/app/api/upload_parsing.py`, `dataverse_backend/app/api/session_routes.py`, `dataverse_backend/app/services/session_service.py`, `dataverse_backend/app/services/analysis_pipeline.py`, `dataverse_backend/app/services/report_generator.py`, and `frontend/lib/dataverse-api.ts`.

## 6.11 Summary

This chapter confirmed that the retail mart dataset is complete, structured, and suitable for business analysis. It contains no missing values and no duplicate rows. The dataset supports sales, profit, quantity, discount, customer, payment, channel, store, and time-based analysis. DataVerse AI provides a working upload, profiling, semantic mapping, analysis, charting, and report generation flow for the dataset.
