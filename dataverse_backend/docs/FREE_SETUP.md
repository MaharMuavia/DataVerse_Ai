# DataVerse AI Free Model Setup

## 1) Install free-model dependencies

```bash
pip install -r requirements/free_models.txt
```

## 2) Configure environment variables

Copy [config/.env.example](../config/.env.example) into your runtime `.env` and set values:

- `GOOGLE_API_KEY`: https://aistudio.google.com/
- `GROQ_API_KEY`: https://console.groq.com/
- `DEEPSEEK_API_KEY`: https://platform.deepseek.com/
- `TOGETHER_API_KEY`: https://api.together.ai/
- `HF_TOKEN`: https://huggingface.co/settings/tokens
- `OLLAMA_BASE_URL`: optional local fallback endpoint

## 3) How model routing works

`config/llm_providers.py` maps each agent to primary and fallback models:

- `orchestrator`: Gemini 2.5 Pro -> Groq Llama 3.3 70B
- `data_analyst`: DeepSeek V3 -> Together Qwen2.5-72B
- `visualizer`: Gemini 2.5 Flash -> Groq Llama 3.3 70B
- `ml_agent`: Together Qwen2.5-72B -> DeepSeek V3
- `insight_generator`: DeepSeek R1 -> Gemini 2.5 Pro
- `anomaly_detector`: Groq Llama 3.3 70B -> Ollama llama3.2

If a provider fails or reaches token thresholds, the router automatically falls back.

## 4) LangGraph wiring

Main graph file: `graph/dataverse_graph.py`

```python
from graph.dataverse_graph import compile_app, make_input_state

app = compile_app("dataverse_memory.db")
state = make_input_state("Find sales trends by region", dataset_path="data/my.csv")
```

## 5) Session persistence

`compile_app()` uses SQLite checkpointer (`dataverse_memory.db`) and expects `thread_id` per session.

## 6) Real-time streaming

Use the helper `stream_graph_events(...)` in `graph/dataverse_graph.py` to stream model chunks to SSE/WebSocket.

## 7) Production notes

- Keep generated-code execution isolated (subprocess is included; stronger sandbox is recommended for untrusted code).
- Run PyCaret in a worker thread or Celery task for heavy training workloads.
- Use Redis-backed tracking for distributed rate-limit accounting.
