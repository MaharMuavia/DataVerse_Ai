"""Client for the locally hosted DeepAnalyze-8B model served by Ollama.

This module communicates with the Ollama HTTP API to send prompts to the DeepAnalyze-8B
model and receive non-streamed responses. It is intended for reasoning-only workloads
and must not be used for numeric computation or raw data processing.

Ollama setup (documented here for reproducibility):

1. Install Ollama (https://ollama.com/docs)
   - macOS (Homebrew): brew install ollama
   - Windows: use the Windows installer from the Ollama website or follow docs
   - Linux: follow distribution-specific instructions in Ollama docs

2. Verify installation:
   - Run: ollama --version
   - Run: ollama list

3. Pull the DeepAnalyze-8B model (example; adjust model name as needed):
   - ollama pull deepanalyze-8b

4. Run the model locally:
   - ollama run --name deepanalyze-8b deepanalyze-8b
   - By default Ollama exposes an HTTP API at http://localhost:11434

5. Confirm accessibility:
   - curl http://localhost:11434/models

Important constraints enforced by code:
- DO NOT pass raw CSV or DataFrame to DeepAnalyze
- Only pass structured facts (dicts) and textual summaries

"""
from __future__ import annotations

import json
import requests
from typing import Dict, Any

from ..core.config import settings
from ..core.logger import logger
from ..core.exceptions import ModelUnavailableError


class DeepAnalyzeClient:
    def __init__(self, base_url: str | None = None, model: str | None = None, timeout: int | None = None):
        self.base_url = base_url or settings.DEEPANALYZE_BASE_URL
        self.model = model or settings.DEEPANALYZE_MODEL
        self.timeout = timeout or settings.DEEPANALYZE_TIMEOUT

    def _http_check(self) -> bool:
        """Check basic HTTP reachability of the Ollama server."""
        try:
            r = requests.get(f"{self.base_url}/", timeout=3)
            logger.debug("DeepAnalyze HTTP root status: %s", r.status_code)
            return r.status_code == 200
        except Exception as e:
            logger.debug("DeepAnalyze HTTP root check failed: %s", e)
            return False

    def _models_endpoint_check(self) -> list[str] | None:
        """Try to retrieve models via possible endpoints and return list of model names if found."""
        endpoints = ["/models", "/api/models", "/v1/models"]
        for ep in endpoints:
            try:
                r = requests.get(f"{self.base_url}{ep}", timeout=3)
                logger.debug("Checked %s: %s", ep, r.status_code)
                if r.status_code == 200:
                    try:
                        data = r.json()
                        # Accept both {models: [...] } and ['name', ...]
                        if isinstance(data, dict) and "models" in data:
                            return [m.get("name") if isinstance(m, dict) else str(m) for m in data.get("models", [])]
                        if isinstance(data, list):
                            return [m.get("name") if isinstance(m, dict) else str(m) for m in data]
                    except Exception:
                        logger.debug("Non-JSON response from %s", ep)
                        continue
            except Exception as e:
                logger.debug("Models endpoint %s not reachable: %s", ep, e)
        return None

    def _local_cli_models(self) -> list[str]:
        """Fallback: use the Ollama CLI to list models if HTTP endpoints don't provide listing.

        This is intended for local debugging and testing only.
        """
        try:
            import subprocess
            out = subprocess.check_output(["ollama", "list"], stderr=subprocess.DEVNULL, text=True)
            # Parse names from output header/columns; simple heuristic
            lines = [l.strip() for l in out.splitlines() if l.strip()]
            models = []
            for l in lines:
                # lines with a space-separated ID and NAME; skip header lines
                parts = l.split()
                if len(parts) >= 1 and not l.lower().startswith("name") and not l.startswith("==="):
                    # assume first token may be name or id; try to use it
                    models.append(parts[0])
            return models
        except Exception as e:
            logger.debug("Failed to query ollama CLI for models: %s", e)
            return []

    def is_available(self) -> bool:
        """Return True when the Ollama server is reachable and a usable model is selected.

        Preference order:
        - If preferred model present -> True
        - If fallback enabled and fallback present -> switch to fallback and return True
        - If any local model exists and fallback enabled -> switch to first available and return True
        - Otherwise return False
        """
        # Server reachability
        if not self._http_check():
            logger.error("DeepAnalyze service HTTP root not reachable at %s", self.base_url)
            return False

        models = self._models_endpoint_check() or []
        cli_models = self._local_cli_models()

        logger.debug("Available models (HTTP): %s; (CLI): %s", models, cli_models)

        # Preferred
        if self.model in models or self.model in cli_models:
            return True

        # Fallback logic
        if getattr(settings, "DEEPANALYZE_ALLOW_FALLBACK", False):
            fallback = settings.DEEPANALYZE_FALLBACK_MODEL
            if fallback in models or fallback in cli_models:
                logger.warning("Preferred model '%s' not found; using fallback '%s'", self.model, fallback)
                self.model = fallback
                return True
            # adopt first available if any
            if models:
                logger.warning("Preferred model '%s' not found; falling back to HTTP model '%s'", self.model, models[0])
                self.model = models[0]
                return True
            if cli_models:
                logger.warning("Preferred model '%s' not found; falling back to CLI model '%s'", self.model, cli_models[0])
                self.model = cli_models[0]
                return True

        logger.error("No suitable reasoning model available (preferred=%s, fallback_allowed=%s)", self.model, settings.DEEPANALYZE_ALLOW_FALLBACK)
        return False

    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for Ollama server and model availability."""
        out = {"server_up": False, "models": [], "using_model": None, "note": None}
        try:
            r = requests.get(f"{self.base_url}/", timeout=3)
            out["server_up"] = r.status_code == 200
        except Exception as e:
            out["note"] = f"HTTP root unreachable: {e}"
            logger.debug("health_check root failed: %s", e)
            return out

        models = self._models_endpoint_check() or []
        out["models"] = models or self._local_cli_models()

        if self.model in out["models"]:
            out["using_model"] = self.model
        elif settings.DEEPANALYZE_ALLOW_FALLBACK and settings.DEEPANALYZE_FALLBACK_MODEL in out["models"]:
            out["using_model"] = settings.DEEPANALYZE_FALLBACK_MODEL
            out["note"] = "Using configured fallback model"
        elif out["models"]:
            out["using_model"] = out["models"][0]
            out["note"] = "Using first available model"
        else:
            out["note"] = "No models discovered"
        return out

    def tag_model(self, tag: str) -> Dict[str, Any]:
        """Optional: tag the running model or create a small marker via Ollama tags API.

        This helps identify runs and is implemented as an HTTP POST to /api/tags. Not all
        Ollama versions support this endpoint; failures are handled gracefully.
        """
        try:
            r = requests.post(f"{self.base_url}/api/tags", json={"tag": tag}, timeout=3)
            if r.status_code == 404:
                logger.debug("Tags endpoint not available on Ollama instance")
                return {"ok": False, "error": "tags endpoint not available"}
            r.raise_for_status()
            return {"ok": True, "response": r.json()}
        except Exception as e:
            logger.debug("Failed to tag model: %s", e)
            return {"ok": False, "error": str(e)}

    def call_model(self, prompt: str, max_tokens: int = 512) -> Dict[str, Any]:
        """Send a prompt to DeepAnalyze via Ollama HTTP API and return structured result.

        Returns dict: {"ok": bool, "text": str} on success, or {"ok": False, "error": str}
        """
        # Ensure server reachable
        if not self._http_check():
            msg = f"DeepAnalyze HTTP root not reachable at {self.base_url}"
            logger.error(msg)
            return {"ok": False, "error": msg}

        # Ensure model availability or choose fallback
        if not self.is_available():
            msg = f"No available reasoning model (preferred={self.model})."
            logger.error(msg)
            return {"ok": False, "error": msg}

        payload = {"model": self.model, "prompt": prompt, "max_length": max_tokens}
        try:
            r = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
            if r.status_code == 404:
                msg = f"Generate endpoint returned 404 for model {self.model}."
                logger.error(msg)
                return {"ok": False, "error": msg}
            r.raise_for_status()
            data = r.json()
            if "response" in data:
                return {"ok": True, "text": data["response"]}
            if "text" in data:
                return {"ok": True, "text": data["text"]}
            return {"ok": True, "text": json.dumps(data)}
        except requests.exceptions.Timeout:
            msg = "DeepAnalyze request timed out"
            logger.exception(msg)
            return {"ok": False, "error": msg}
        except requests.exceptions.ConnectionError as e:
            msg = f"Connection error contacting DeepAnalyze at {self.base_url}: {e}"
            logger.exception(msg)
            return {"ok": False, "error": msg}
        except Exception as e:
            msg = f"DeepAnalyze request failed: {e}"
            logger.exception(msg)
            return {"ok": False, "error": msg}
