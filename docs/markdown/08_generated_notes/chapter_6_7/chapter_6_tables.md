# Chapter 6 Tables

## Dataset Profile
| Property | Value |
| --- | --- |
| Dataset name | retail_mart_processed_v1.csv |
| Dataset path | data/retail_mart_processed_v1.csv |
| Dataset purpose | Retail transaction analysis for sales, profit, discount, customer, payment, online/offline, store, and time-based performance. |
| Numeric business columns | unit_price, quantity, discount, total_sales, profit, price_qty, discount_value, profit_margin |
| Categorical / encoded columns | store_id, region, city, category, subcategory, customer_type, payment_method, online_order, stockout_flag, weekday, month, year, hour |
| Date/time component columns | weekday, month, year, hour |
| Target / important business columns | total_sales, profit, quantity, profit_margin, discount |

## Missing Values
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

## Column Profile
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

## Numeric Summary
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

## Categorical Summary
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

## Outlier Summary
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

## KPI Summary
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

## Sales by Region
| region | total_sales | total_profit | total_quantity | orders | profit_margin |
| --- | --- | --- | --- | --- | --- |
| 2 | $1,279,763.60 | $191,713.72 | 39466 | 19905 | 14.98% |
| 0 | $328,285.13 | $49,646.34 | 10123 | 5051 | 15.12% |
| 1 | $320,928.87 | $47,777.62 | 10033 | 5059 | 14.89% |
| 3 | $319,685.02 | $47,801.25 | 9924 | 4985 | 14.95% |

## Sales by City
| city | total_sales | total_profit | total_quantity | orders | profit_margin |
| --- | --- | --- | --- | --- | --- |
| 0 | $328,830.32 | $49,133.91 | 9967 | 5018 | 14.94% |
| 1 | $328,285.13 | $49,646.34 | 10123 | 5051 | 15.12% |
| 4 | $322,475.07 | $48,097.48 | 9956 | 4974 | 14.92% |
| 5 | $320,928.87 | $47,777.62 | 10033 | 5059 | 14.89% |
| 2 | $319,685.02 | $47,801.25 | 9924 | 4985 | 14.95% |
| 3 | $318,407.97 | $47,765.26 | 9837 | 4950 | 15.00% |
| 6 | $310,050.24 | $46,717.07 | 9706 | 4963 | 15.07% |

## Category Performance
| category | total_sales | total_profit | total_quantity | orders | profit_margin |
| --- | --- | --- | --- | --- | --- |
| 1 | $964,022.78 | $144,405.95 | 17517 | 8794 | 14.98% |
| 2 | $433,278.77 | $65,192.01 | 17646 | 8826 | 15.05% |
| 3 | $426,792.73 | $63,601.16 | 17236 | 8685 | 14.90% |
| 0 | $424,568.34 | $63,739.81 | 17147 | 8695 | 15.01% |

## Customer Type Analysis
| customer_type | total_sales | total_profit | total_quantity | orders | profit_margin |
| --- | --- | --- | --- | --- | --- |
| 0 | $1,136,762.84 | $170,677.48 | 34875 | 17522 | 15.01% |
| 1 | $1,111,899.78 | $166,261.45 | 34671 | 17478 | 14.95% |

## Payment Method Analysis
| payment_method | total_sales | total_profit | total_quantity | orders | profit_margin |
| --- | --- | --- | --- | --- | --- |
| 2 | $569,968.83 | $85,175.19 | 17401 | 8766 | 14.94% |
| 3 | $563,971.83 | $85,219.69 | 17492 | 8845 | 15.11% |
| 1 | $560,863.06 | $83,464.06 | 17421 | 8742 | 14.88% |
| 0 | $553,858.90 | $83,079.99 | 17232 | 8647 | 15.00% |

## Online vs Offline Analysis
| online_order | total_sales | total_profit | total_quantity | orders | profit_margin |
| --- | --- | --- | --- | --- | --- |
| 1 | $1,129,750.25 | $169,789.49 | 34956 | 17570 | 15.03% |
| 0 | $1,118,912.37 | $167,149.44 | 34590 | 17430 | 14.94% |

## Discount Impact
Discount/profit Pearson correlation: `-0.0739`

| discount | total_sales | total_profit | avg_profit | orders |
| --- | --- | --- | --- | --- |
| 0 | $803,438.05 | $120,942.04 | $10.45 | 11568 |
| 0.05 | $383,225.49 | $57,605.96 | $9.98 | 5773 |
| 0.10 | $377,970.56 | $56,302.83 | $9.50 | 5929 |
| 0.15 | $351,711.37 | $52,771.19 | $9.01 | 5854 |
| 0.20 | $332,317.15 | $49,316.91 | $8.39 | 5876 |

## Top Store Performance
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
