# Retail Agent

Local retail analytics agent with preprocessing, EDA, SHAP-based explainability, and LLM narrative output via Ollama.

## 1) Setup

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

## 2) Pull DeepSeek models in Ollama

```bash
ollama pull deepseek-r1:7b
ollama pull deepseek-r1:14b
ollama create retail-analyst -f Modelfile
```

## 3) Run

```bash
python main.py data/retail_data.csv --query "What are the hot selling products?" --target Quantity
```

Optional args:

- `--model retail-analyst`
- `--output report.md`

## 4) Output

- A markdown report is generated at `report.md` (or your chosen output path).
