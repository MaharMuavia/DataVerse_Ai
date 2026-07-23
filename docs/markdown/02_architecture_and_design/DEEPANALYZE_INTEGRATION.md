# DeepAnalyze as DataVerse's agentic engine

[DeepAnalyze](https://github.com/ruc-datalab/DeepAnalyze) (RUC DataLab) is the
first agentic LLM purpose-built for autonomous data science — an 8B model
served through an OpenAI-compatible API. DataVerse integrates it as the
**reasoning and narration engine** on top of its deterministic core:

```
Upload → deterministic pipeline (Pandas/sklearn computes every number)
       → DeepAnalyze (plans chat answers, narrates reports, explains drivers)
       → verification layer (receipts + reproducibility certificate)
```

The deterministic core stays authoritative by design: DeepAnalyze reasons
*about* computed facts but never originates a number, so every figure in the
product remains provable. If the model is unreachable, the system degrades
gracefully to Mock/deterministic mode — the demo can never be taken down by
the LLM.

## Wiring (already in the codebase)

- `app/services/deepanalyze_client.py` — OpenAI-compatible client.
- `app/services/llm_provider.py` — provider chain; DeepAnalyze participates in
  `auto` mode and becomes the preferred engine when selected.
- Tests: `tests/test_deepanalyze_provider.py`.

Enable it with two env vars (in `dataverse_backend/.env` or the host's env):

```
LLM_PROVIDER=deepanalyze
DEEPANALYZE_LOCAL_BASE_URL=http://127.0.0.1:8010/v1   # or a remote URL
DEEPANALYZE_MODEL=deepanalyze-8b                       # model name at the server
```

Remote servers with an API key use `DEEPANALYZE_API_BASE` + `DEEPANALYZE_API_KEY`
instead of the local URL.

## Serving DeepAnalyze-8B (pick one)

The model needs a GPU with ≥16 GB VRAM for real-time use. This laptop has no
NVIDIA GPU, so the realistic options are:

### A. Free Google Colab GPU + tunnel (recommended for the demo)
1. Colab notebook with a T4 GPU (free tier):
   ```
   !pip install vllm
   !python -m vllm.entrypoints.openai.api_server \
       --model RUC-DataLab/DeepAnalyze-8B --quantization awq \
       --max-model-len 16384 --port 8010
   ```
2. Expose it with a tunnel (ngrok/cloudflared) from the notebook.
3. Point `DEEPANALYZE_LOCAL_BASE_URL` at `https://<tunnel>/v1` and restart the
   backend.

### B. Local Ollama (CPU — works, but slow)
Ollama is installed on this machine. A community GGUF build of
DeepAnalyze-8B (~5 GB) runs on CPU at roughly 3–8 tokens/s:
```
ollama pull hf.co/mattritchey/DeepAnalyze-8B-Q4_K_M-GGUF
```
then set `DEEPANALYZE_LOCAL_BASE_URL=http://localhost:11434/v1` and
`DEEPANALYZE_MODEL=hf.co/mattritchey/DeepAnalyze-8B-Q4_K_M-GGUF`.
Expect ~30 s per chat answer on CPU — fine for testing, risky live.

### C. University lab / any CUDA machine
Same vLLM command as option A on the lab machine; point the env var at its
address.

## Why not replace the backend with the DeepAnalyze repo?

The DeepAnalyze repository ships model weights, serving scripts, and training
code — it is an engine, not an application server. DataVerse's FastAPI backend
provides what the product is graded on: per-user auth, session persistence,
deterministic verifiable analytics, receipts/certificates, and report
generation. The integration above gives DataVerse DeepAnalyze's agentic
reasoning while keeping every number provable.
