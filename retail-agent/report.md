# Retail Analytics Report
Generated: 2026-03-10 06:39:28
User Query: What are the hot selling products?

## 1. Data Overview
- Rows: 10
- Columns: 10
- Missing Values: 0

### Preprocessing Actions
- Quantity: capped 4 outliers using IQR bounds
- UnitPrice: capped 2 outliers using IQR bounds

## 2. Exploratory Data Analysis
### Numeric Summary
|       |    InvoiceNo |   Quantity |   UnitPrice |   CustomerID |   Revenue |   Profit |
|:------|-------------:|-----------:|------------:|-------------:|----------:|---------:|
| count |     10       |   10       |    10       |        10    |  10       | 10       |
| mean  | 536369       |    6.5     |     3.07425 |     14488.4  |  18.658   |  5.11    |
| std   |      2.87518 |    2.10159 |     1.2234  |      2319.95 |   5.09102 |  1.63466 |
| min   | 536365       |    3.75    |     1.85    |     13047    |  11.1     |  2.6     |
| 25%   | 536366       |    6       |     2.2125  |     13047    |  15.9375  |  4.3     |
| 50%   | 536368       |    6       |     2.65    |     13048    |  19.095   |  5.15    |
| 75%   | 536371       |    7.5     |     3.39    |     16649.8  |  21.585   |  6.1     |
| max   | 536373       |    9.75    |     5.15625 |     17851    |  25.5     |  7.4     |

### Top Categories
- StockCode: 85123A (2), 71053 (1), 84406B (1), 84029G (1), 22745 (1)
- Description: WHITE HANGING HEART T-LIGHT HOLDER (2), WHITE METAL LANTERN (1), CREAM CUPID HEARTS COAT HANGER (1), KNITTED UNION FLAG HOT WATER BOTTLE (1), POPPY'S PLAYHOUSE BEDROOM (1)
- InvoiceDate: 2010-12-01 08:26 (2), 2010-12-01 08:35 (2), 2010-12-01 08:28 (1), 2010-12-01 08:34 (1), 2010-12-01 08:36 (1)

### Correlation Insights
Strong positive correlations:
- Revenue & Profit: 0.98
- Profit & Revenue: 0.98
- Quantity & Revenue: 0.63
Strong negative correlations:
- InvoiceNo & CustomerID: -0.78
- CustomerID & InvoiceNo: -0.78
- Quantity & UnitPrice: -0.68

## 3. Explainable Insights
### Top Driving Factors
- Revenue: importance 0.691
- Profit: importance 0.593
- UnitPrice: importance 0.250
- InvoiceNo: importance 0.238
- CustomerID: importance 0.033

### AI Explanation
LLM explanation unavailable: model 'retail-analyst' not found (status code: 404)

## 4. Recommendations
Recommendation generation unavailable: model 'retail-analyst' not found (status code: 404)
