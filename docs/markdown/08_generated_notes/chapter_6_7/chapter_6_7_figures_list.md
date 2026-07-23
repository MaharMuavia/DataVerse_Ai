# Chapter 6/7 Figures List

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

## Chart Selection Contracts

| Figure | Analytical Question | Chart Family | Data Fields | Supported Claim |
| --- | --- | --- | --- | --- |
| Figure 6.3 | Which category has the highest sales? | Comparison bar | category, total_sales | Encoded category sales ranking |
| Figure 6.4 | Which region has the highest sales? | Comparison bar | region, total_sales | Encoded region sales ranking |
| Figure 6.5 | Which category has the highest profit? | Comparison bar | category, total_profit | Encoded category profit ranking |
| Figure 6.6 | How do sales move by month? | Trend line | year, month, total_sales | Monthly sales trend from 2023-01 to partial 2025-01 |
| Figure 6.7 | What is the order-count mix by customer type? | Composition pie | customer_type, order count | Customer type distribution |
| Figure 6.8 | Which payment method is most common? | Comparison bar | payment_method, order count | Payment method distribution |
| Figure 6.9 | How do online and offline sales compare? | Comparison bar | online_order, total_sales | Channel sales comparison |
| Figure 6.10 | Do discounts relate to profit? | Relationship scatter | discount, profit | Weak negative discount-profit relationship |
