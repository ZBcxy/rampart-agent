"""Local LLM Provider — Ollama, vLLM, llama.cpp, and any OpenAI-compatible endpoint.

Zero API key needed. Run models locally.

Supported backends:
- Ollama: auto-detects at http://localhost:11434
- vLLM: OpenAI-compatible at http://localhost:8000/v1
- llama.cpp server: OpenAI-compatible at http://localhost:8080/v1
- Generic: any OpenAI-compatible endpoint

Usage:
    from core.planner.local_llm import LocalLLM

    llm = LocalLLM(provider="ollama", model="qwen3:14b")
    response = llm.chat([{"role": "user", "content": "Hello"}])

    # or with custom endpoint
    llm = LocalLLM(provider="openai_compatible", model="deepseek-v3",
                   base_url="http://localhost:8000/v1")
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LocalModelInfo:
    """Info about an available local model."""
    name: str
    provider: str
    size: str = ""
    modified: str = ""
    available: bool = True


class LocalLLM:
    """Unified interface for local LLM inference.

    Auto-discovers Ollama models, supports any OpenAI-compatible endpoint.
    """

    # Recommended models per task type
    RECOMMENDED = {
        "fast": ["qwen3:8b", "llama3.1:8b", "mistral:7b", "deepseek-r1:8b"],
        "balanced": ["qwen3:14b", "llama3.1:70b", "deepseek-r1:14b"],
        "powerful": ["qwen3:32b", "deepseek-r1:32b", "llama3.1:70b"],
    }

    def __init__(
        self,
        provider: str = "ollama",
        model: str = "qwen3:8b",
        base_url: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        api_key: str = "not-needed",
    ):
        """
        Args:
            provider: ollama | openai_compatible
            model: model name (e.g., 'qwen3:14b', 'llama3.1:8b')
            base_url: endpoint URL (auto-detected if None)
            temperature: sampling temperature
            max_tokens: max output tokens
            api_key: API key (ignored for local, used for OpenAI compatible)
        """
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = api_key

        # Auto-detect base URL
        if base_url:
            self.base_url = base_url.rstrip("/")
        elif provider == "ollama":
            self.base_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434/v1")
        else:
            self.base_url = os.environ.get("LOCAL_LLM_URL", "http://localhost:8000/v1")

        self._client = None

    def _get_client(self):
        """Lazy-init OpenAI-compatible client."""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        return self._client

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Send a chat completion request.

        Args:
            messages: List of {"role": "...", "content": "..."} dicts
            **kwargs: extra params (temperature, max_tokens, etc.)

        Returns:
            Model response text
        """
        client = self._get_client()

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )

        return response.choices[0].message.content

    def chat_stream(self, messages: List[Dict[str, str]], **kwargs):
        """Stream a chat completion."""
        client = self._get_client()

        stream = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            stream=True,
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def list_models(self) -> List[LocalModelInfo]:
        """List available local models."""
        if self.provider == "ollama":
            return self._list_ollama_models()
        else:
            return self._list_openai_models()

    def _list_ollama_models(self) -> List[LocalModelInfo]:
        """Query Ollama for available models."""
        try:
            import requests
            resp = requests.get(
                self.base_url.replace("/v1", "/api/tags"),
                timeout=5,
            )
            if resp.status_code == 200:
                models = []
                for m in resp.json().get("models", []):
                    models.append(LocalModelInfo(
                        name=m["name"],
                        provider="ollama",
                        size=m.get("size", ""),
                        modified=m.get("modified_at", ""),
                    ))
                return models
        except Exception:
            pass
        return []

    def _list_openai_models(self) -> List[LocalModelInfo]:
        """Query OpenAI-compatible endpoint for models."""
        try:
            client = self._get_client()
            models = client.models.list()
            return [
                LocalModelInfo(name=m.id, provider=self.provider)
                for m in models.data[:20]
            ]
        except Exception:
            return [LocalModelInfo(name=self.model, provider=self.provider)]

    def ping(self) -> bool:
        """Check if the local model server is reachable."""
        try:
            self._get_client().models.list()
            return True
        except Exception:
            return False

    @classmethod
    def discover(cls) -> Dict[str, bool]:
        """Auto-discover available local LLM backends.

        Returns:
            {"ollama": True/False, "vllm": True/False}
        """
        import requests

        results = {}

        # Check Ollama
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=3)
            results["ollama"] = r.status_code == 200
        except Exception:
            results["ollama"] = False

        # Check common OpenAI-compatible endpoints
        for name, url in [
            ("vllm", "http://localhost:8000/v1/models"),
            ("llama_cpp", "http://localhost:8080/v1/models"),
        ]:
            try:
                r = requests.get(url, timeout=3)
                results[name] = r.status_code == 200
            except Exception:
                results[name] = False

        return results

    @classmethod
    def quick_start(cls) -> Optional["LocalLLM"]:
        """Auto-discover and connect to the first available local LLM.

        Tries: Ollama → vLLM → llama.cpp → fails

        Returns:
            LocalLLM instance or None if no backend found
        """
        discovered = cls.discover()

        if discovered.get("ollama"):
            llm = cls(provider="ollama", model="qwen3:8b")
            if llm.ping():
                models = llm.list_models()
                if models:
                    llm.model = models[0].name
                return llm

        for name, url in [("vllm", "http://localhost:8000/v1"), ("llama_cpp", "http://localhost:8080/v1")]:
            if discovered.get(name):
                llm = cls(provider="openai_compatible", base_url=url)
                try:
                    models = llm.list_models()
                    if models:
                        llm.model = models[0].name
                    return llm
                except Exception:
                    continue

        return None


# ── Integration with LLMPlanner ──────────────────────────────────────────────

def create_local_planner(
    provider: str = "ollama",
    model: str = "qwen3:8b",
    base_url: Optional[str] = None,
):
    """Create an LLMPlanner backed by a local model.

    Usage:
        from core.planner.llm_planner import LLMPlanner
        from core.planner.local_llm import create_local_planner

        planner = create_local_planner(provider="ollama", model="qwen3:14b")
        plan = planner.generate_plan("analyze data", {})
    """
    from core.planner.llm_planner import LLMPlanner, LLMPlannerConfig

    if base_url is None:
        if provider == "ollama":
            base_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434/v1")
        else:
            base_url = os.environ.get("LOCAL_LLM_URL", "http://localhost:8000/v1")

    config = LLMPlannerConfig(
        model=model,
        provider="openai",  # Use OpenAI client path
        api_key="not-needed",
        api_base=base_url,
    )
    return LLMPlanner(config=config)
