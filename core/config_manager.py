"""✦ Polaris Agent — Configuration Manager

Config priority (highest first):
  1. CLI arguments
  2. Environment variables
  3. ~/.polaris/config.json  (canonical config file)
  4. .env file
  5. Built-in defaults

Usage:
    from core.config_manager import ConfigManager

    cm = ConfigManager()
    model = cm.get("LLM_MODEL")
    cm.set("LLM_MODEL", "gpt-4o")
    cm.write()  # persist to disk
"""

import json
import os
from pathlib import Path
from typing import Any

# ── Constants ──────────────────────────────────────────────────────────────

POLARIS_HOME = Path(os.environ.get("POLARIS_HOME", Path.home() / ".polaris"))
CONFIG_FILE = POLARIS_HOME / "config.json"
ENV_FILE = POLARIS_HOME / ".env"

# Canonical defaults — everything has a sensible fallback
DEFAULTS: dict[str, Any] = {
    # ── LLM Provider ──
    "LLM_MODEL": "gpt-4o",
    "LLM_PROVIDER": "openai",
    "LLM_TEMPERATURE": 0.3,
    "LLM_MAX_TOKENS": 2000,
    "OPENAI_API_KEY": "",
    "OPENAI_API_BASE": "",
    "ANTHROPIC_API_KEY": "",
    # ── Server ──
    "SERVER_HOST": "0.0.0.0",
    "SERVER_PORT": 8000,
    "JWT_SECRET": "",
    "TOKEN_EXPIRE_HOURS": 24,
    "RATE_LIMIT_USER": 100,
    "CORS_ALLOW_ORIGINS": '["*"]',
    # ── Agent Runtime ──
    "POLARIS_HOME": str(POLARIS_HOME),
    "POLARIS_LOG_LEVEL": "INFO",
    "POLARIS_AUTONOMY": "L2",
    "POLARIS_MAX_STEPS": 20,
    # ── Local LLM ──
    "LOCAL_LLM_PROVIDER": "",
    "LOCAL_LLM_MODEL": "",
    "LOCAL_LLM_URL": "",
    # ── Memory ──
    "REDIS_HOST": "localhost",
    "REDIS_PORT": 6379,
    "MILVUS_HOST": "localhost",
    "MILVUS_PORT": 19530,
    "EMBEDDING_PROVIDER": "openai",
    "EMBEDDING_MODEL": "text-embedding-3-small",
}


class ConfigManager:
    """Unified configuration manager with layered priority resolution.

    Reads in order: defaults → .env → config.json → env vars.
    Writes to: ~/.polaris/config.json
    """

    def __init__(self, home: Path | None = None):
        self._home = home or POLARIS_HOME
        self._config_path = self._home / "config.json"
        self._env_path = self._home / ".env"
        self._data: dict[str, Any] = {}
        self._ensure_dirs()
        self._load()

    # ── File I/O ────────────────────────────────────────────────────────

    def _ensure_dirs(self) -> None:
        self._home.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        """Load config from JSON file. If absent, seed from .env."""
        if self._config_path.exists():
            try:
                self._data = json.loads(self._config_path.read_text())
            except (json.JSONDecodeError, Exception):
                self._data = {}
        else:
            self._data = {}
            self._seed_from_dotenv()

    def _seed_from_dotenv(self) -> None:
        """On first run, pull values from .env if it exists."""
        if not self._env_path.exists():
            return
        try:
            for line in self._env_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key in DEFAULTS and val and val != f"{key}=your-key-here":
                    self._data[key] = val
        except Exception:
            pass

    def write(self) -> None:
        """Persist current config to disk."""
        self._ensure_dirs()
        self._config_path.write_text(json.dumps(self._data, indent=2, ensure_ascii=False, default=str))

    def reload(self) -> None:
        self._load()

    # ── Get / Set ───────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """Resolve a config value through the priority chain.

        Priority: env var > config file > built-in defaults
        """
        # 1. Environment variable (highest priority)
        env_val = os.environ.get(key)
        if env_val is not None and env_val != "":
            return self._coerce(env_val, key)

        # 2. Config file
        if key in self._data and self._data[key] not in (None, ""):
            return self._data[key]

        # 3. Built-in default
        if key in DEFAULTS:
            return DEFAULTS[key]

        return default

    def get_raw(self, key: str, default: Any = None) -> Any:
        """Get value from config file only (ignore env vars)."""
        return self._data.get(key, default or DEFAULTS.get(key))

    def set(self, key: str, value: Any) -> None:
        """Set a config value (in-memory, call write() to persist)."""
        self._data[key] = value

    def unset(self, key: str) -> None:
        """Remove a config key (reverts to default/env)."""
        self._data.pop(key, None)

    def reset(self) -> None:
        """Clear all config, restoring defaults."""
        self._data = {}
        if self._config_path.exists():
            self._config_path.unlink()
        self._load()

    # ── Bulk ────────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Return all resolved values (for display)."""
        result = {}
        for key in DEFAULTS:
            result[key] = self.get(key)
        for key in self._data:
            if key not in result:
                result[key] = self._data[key]
        return result

    def to_env_file(self) -> str:
        """Export config as .env file content."""
        lines = ["# ✦ Polaris Agent — Navigate Complexity with AI", ""]
        categories = [
            ("LLM Provider", [
                "OPENAI_API_KEY", "OPENAI_API_BASE", "ANTHROPIC_API_KEY",
                "LLM_MODEL", "LLM_PROVIDER", "LLM_TEMPERATURE", "LLM_MAX_TOKENS",
            ]),
            ("Server", [
                "SERVER_HOST", "SERVER_PORT", "JWT_SECRET",
                "TOKEN_EXPIRE_HOURS", "RATE_LIMIT_USER", "CORS_ALLOW_ORIGINS",
            ]),
            ("Agent Runtime", [
                "POLARIS_HOME", "POLARIS_LOG_LEVEL", "POLARIS_AUTONOMY", "POLARIS_MAX_STEPS",
            ]),
            ("Local LLM", [
                "LOCAL_LLM_PROVIDER", "LOCAL_LLM_MODEL", "LOCAL_LLM_URL",
            ]),
            ("Memory & Storage", [
                "REDIS_HOST", "REDIS_PORT", "MILVUS_HOST", "MILVUS_PORT",
                "EMBEDDING_PROVIDER", "EMBEDDING_MODEL",
            ]),
        ]
        for category, keys in categories:
            lines.append(f"# --- {category} ---")
            for k in keys:
                v = self.get(k)
                lines.append(f"{k}={v}")
            lines.append("")
        return "\n".join(lines)

    # ── Paths ───────────────────────────────────────────────────────────

    @property
    def config_path(self) -> Path:
        return self._config_path

    @property
    def home(self) -> Path:
        return self._home

    # ── Helpers ─────────────────────────────────────────────────────────

    def _coerce(self, value: str, key: str) -> Any:
        """Coerce string env var to the type of its default."""
        default = DEFAULTS.get(key)
        if default is None:
            return value
        if isinstance(default, bool):
            return value.lower() in ("true", "1", "yes")
        if isinstance(default, int):
            try:
                return int(value)
            except ValueError:
                return value
        if isinstance(default, float):
            try:
                return float(value)
            except ValueError:
                return value
        return value


# ── Ollama auto-discovery ──────────────────────────────────────────────────

def discover_ollama() -> dict[str, Any] | None:
    """Check if Ollama is running and return available info."""
    import urllib.request

    url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    try:
        req = urllib.request.Request(f"{url}/api/tags", method="GET")
        resp = urllib.request.urlopen(req, timeout=3)
        data = json.loads(resp.read())
        models = [m.get("name", "?") for m in data.get("models", [])]
        return {"running": True, "url": url, "models": models}
    except Exception:
        return None


def discover_vllm() -> dict[str, Any] | None:
    """Check if a vLLM/OpenAI-compatible server is running locally."""
    import urllib.request

    url = os.environ.get("LOCAL_LLM_URL", "http://localhost:8000/v1")
    try:
        req = urllib.request.Request(f"{url}/models", method="GET")
        resp = urllib.request.urlopen(req, timeout=3)
        data = json.loads(resp.read())
        models = [m.get("id", "?") for m in data.get("data", [])]
        return {"running": True, "url": url, "models": models}
    except Exception:
        return None
