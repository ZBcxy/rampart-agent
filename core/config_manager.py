"""✦ Rampart Agent — Layered Configuration Manager

Config layers (like Claude Code's settings.json + .claude.json):

  1. CLI arguments                         (highest priority)
  2. Environment variables
  3. .rampart/config.local.json  (project-local, gitignored)
  4. .rampart/config.json        (project, committed)
  5. ~/.rampart/config.json      (global)
  6. Built-in defaults            (lowest)

Usage:
    from core.config_manager import ConfigManager

    cm = ConfigManager()
    model = cm.get("LLM_MODEL")
    cm.set("LLM_MODEL", "gpt-4o")   # writes to global by default
    cm.set("LLM_MODEL", "claude-4", layer="project")
    cm.write()                       # persist all layers
    print(cm.get_source("LLM_MODEL"))  # "project"
"""

import json
import os
from pathlib import Path
from typing import Any

# ── Constants ──────────────────────────────────────────────────────────────

RAMPART_HOME = Path(os.environ.get("RAMPART_HOME", Path.home() / ".rampart"))

# Canonical defaults
DEFAULTS: dict[str, Any] = {
    "LLM_MODEL": "gpt-4o",
    "LLM_PROVIDER": "openai",
    "LLM_TEMPERATURE": 0.3,
    "LLM_MAX_TOKENS": 2000,
    "OPENAI_API_KEY": "",
    "OPENAI_API_BASE": "",
    "ANTHROPIC_API_KEY": "",
    "SERVER_HOST": "0.0.0.0",
    "SERVER_PORT": 8000,
    "JWT_SECRET": "",
    "TOKEN_EXPIRE_HOURS": 24,
    "RATE_LIMIT_USER": 100,
    "CORS_ALLOW_ORIGINS": '["*"]',
    "RAMPART_HOME": str(RAMPART_HOME),
    "RAMPART_LOG_LEVEL": "INFO",
    "RAMPART_AUTONOMY": "L2",
    "RAMPART_MAX_STEPS": 20,
    "LOCAL_LLM_PROVIDER": "",
    "LOCAL_LLM_MODEL": "",
    "LOCAL_LLM_URL": "",
    "REDIS_HOST": "localhost",
    "REDIS_PORT": 6379,
    "MILVUS_HOST": "localhost",
    "MILVUS_PORT": 19530,
    "EMBEDDING_PROVIDER": "openai",
    "EMBEDDING_MODEL": "text-embedding-3-small",
}


class ConfigManager:
    """Layered configuration manager.

    Three config files (plus env vars and defaults):
      Layer 3 (project-local): .rampart/config.local.json   ← gitignored
      Layer 2 (project):       .rampart/config.json         ← committed
      Layer 1 (global):        ~/.rampart/config.json       ← user-global

    Resolution order: env var > L3 > L2 > L1 > defaults
    """

    def __init__(self, cwd: Path | None = None):
        self._cwd = cwd or Path.cwd()
        self._home = RAMPART_HOME

        # Layer paths (highest priority first in resolution)
        self._global_path = self._home / "config.json"
        self._project_path: Path | None = self._find_project_config()
        self._local_path: Path | None = self._find_local_config()

        # Data stores per layer
        self._global: dict[str, Any] = {}
        self._project: dict[str, Any] = {}
        self._local: dict[str, Any] = {}

        self._ensure_dirs()
        self._load_all()

    # ── Layer discovery ─────────────────────────────────────────────────

    def _find_project_config(self) -> Path | None:
        """Walk up from cwd to find .rampart/config.json.
        Stops before ~/.rampart to avoid treating global as project."""
        d = self._cwd.resolve()
        home = Path.home().resolve()
        while True:
            candidate = d / ".rampart" / "config.json"
            if candidate.exists() and candidate != self._global_path:
                return candidate
            parent = d.parent
            if parent == d or d == home:
                break
            d = parent
        return None

    def _find_local_config(self) -> Path | None:
        """Walk up from cwd to find .rampart/config.local.json."""
        d = self._cwd.resolve()
        home = Path.home().resolve()
        while True:
            candidate = d / ".rampart" / "config.local.json"
            if candidate.exists() and candidate != self._global_path:
                return candidate
            parent = d.parent
            if parent == d or d == home:
                break
            d = parent
        return None

    # ── File I/O ────────────────────────────────────────────────────────

    def _ensure_dirs(self) -> None:
        self._home.mkdir(parents=True, exist_ok=True)

    def _load_json(self, path: Path) -> dict[str, Any]:
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, FileNotFoundError, Exception):
            return {}

    def _load_all(self) -> None:
        self._global = self._load_json(self._global_path)
        if self._project_path:
            self._project = self._load_json(self._project_path)
        if self._local_path:
            self._local = self._load_json(self._local_path)

    def write(self) -> None:
        """Persist in-memory changes to the appropriate layer files."""
        self._ensure_dirs()
        if self._global:
            self._global_path.write_text(json.dumps(self._global, indent=2, ensure_ascii=False, default=str))
        if self._project is not None and self._project_path:
            self._project_path.parent.mkdir(parents=True, exist_ok=True)
            self._project_path.write_text(json.dumps(self._project, indent=2, ensure_ascii=False, default=str))
        if self._local is not None and self._local_path:
            self._local_path.parent.mkdir(parents=True, exist_ok=True)
            self._local_path.write_text(json.dumps(self._local, indent=2, ensure_ascii=False, default=str))

    def reload(self) -> None:
        self._load_all()

    # ── Get / Set ───────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """Resolve a config value through all layers.

        Priority: env var > local > project > global > defaults
        """
        # 1. Environment variable
        env_val = os.environ.get(key)
        if env_val is not None and env_val != "":
            return self._coerce(env_val, key)

        # 2. Project-local layer
        if key in self._local and self._local[key] not in (None, ""):
            return self._local[key]

        # 3. Project layer
        if key in self._project and self._project[key] not in (None, ""):
            return self._project[key]

        # 4. Global layer
        if key in self._global and self._global[key] not in (None, ""):
            return self._global[key]

        # 5. Defaults
        if key in DEFAULTS:
            return DEFAULTS[key]

        return default

    def get_source(self, key: str) -> str:
        """Return which layer provides the value: 'env' | 'local' | 'project' | 'global' | 'default'."""
        if os.environ.get(key):
            return "env"
        if key in self._local and self._local[key] not in (None, ""):
            return "local"
        if key in self._project and self._project[key] not in (None, ""):
            return "project"
        if key in self._global and self._global[key] not in (None, ""):
            return "global"
        return "default"

    def set(self, key: str, value: Any, layer: str = "global") -> None:
        """Set a config value. layer: 'global', 'project', or 'local'."""
        if layer == "local":
            if self._local_path is None:
                self._local_path = self._cwd / ".rampart" / "config.local.json"
            self._local[key] = value
        elif layer == "project":
            if self._project_path is None:
                self._project_path = self._cwd / ".rampart" / "config.json"
            self._project[key] = value
        else:
            self._global[key] = value

    def unset(self, key: str, layer: str = "global") -> None:
        if layer == "local":
            self._local.pop(key, None)
        elif layer == "project":
            self._project.pop(key, None)
        else:
            self._global.pop(key, None)

    def reset(self, layer: str | None = None) -> None:
        """Clear config. If layer is None, clear all layers."""
        if layer == "global" or layer is None:
            self._global = {}
            if self._global_path.exists():
                self._global_path.unlink()
        if layer == "project" or layer is None:
            self._project = {}
            if self._project_path and self._project_path.exists():
                self._project_path.unlink()
        if layer == "local" or layer is None:
            self._local = {}
            if self._local_path and self._local_path.exists():
                self._local_path.unlink()
        self._load_all()

    # ── Bulk ────────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        result = {}
        for key in DEFAULTS:
            result[key] = self.get(key)
        for store in [self._global, self._project, self._local]:
            for key in store:
                if key not in result:
                    result[key] = store[key]
        return result

    def to_env_file(self) -> str:
        lines = ["# ✦ Rampart Agent — Navigate Complexity with AI", ""]
        categories = [
            ("LLM Provider", ["OPENAI_API_KEY", "OPENAI_API_BASE", "ANTHROPIC_API_KEY",
                              "LLM_MODEL", "LLM_PROVIDER", "LLM_TEMPERATURE", "LLM_MAX_TOKENS"]),
            ("Server", ["SERVER_HOST", "SERVER_PORT", "JWT_SECRET",
                        "TOKEN_EXPIRE_HOURS", "RATE_LIMIT_USER", "CORS_ALLOW_ORIGINS"]),
            ("Agent Runtime", ["RAMPART_HOME", "RAMPART_LOG_LEVEL", "RAMPART_AUTONOMY", "RAMPART_MAX_STEPS"]),
            ("Local LLM", ["LOCAL_LLM_PROVIDER", "LOCAL_LLM_MODEL", "LOCAL_LLM_URL"]),
            ("Memory & Storage", ["REDIS_HOST", "REDIS_PORT", "MILVUS_HOST", "MILVUS_PORT",
                                  "EMBEDDING_PROVIDER", "EMBEDDING_MODEL"]),
        ]
        for category, keys in categories:
            lines.append(f"# --- {category} ---")
            for k in keys:
                lines.append(f"{k}={self.get(k)}")
            lines.append("")
        return "\n".join(lines)

    # ── Paths ───────────────────────────────────────────────────────────

    @property
    def config_path(self) -> Path:
        """Primary config path (global)."""
        return self._global_path

    @property
    def global_path(self) -> Path:
        return self._global_path

    @property
    def project_path(self) -> Path | None:
        return self._project_path

    @property
    def local_path(self) -> Path | None:
        return self._local_path

    @property
    def home(self) -> Path:
        return self._home

    def all_paths(self) -> list[tuple[str, Path | None]]:
        """Return all config file paths with labels."""
        return [
            ("local",   self._local_path),
            ("project", self._project_path),
            ("global",  self._global_path),
        ]

    def raw_data(self) -> dict[str, dict[str, Any]]:
        """Return raw data from each layer for display."""
        return {
            "local":   dict(self._local),
            "project": dict(self._project),
            "global":  dict(self._global),
        }

    # ── Helpers ─────────────────────────────────────────────────────────

    def _coerce(self, value: str, key: str) -> Any:
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


# ── Auto-discovery ─────────────────────────────────────────────────────────

def discover_ollama() -> dict[str, Any] | None:
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
