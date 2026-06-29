"""Unit tests for ConfigManager."""

import json
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_home():
    """Create a temporary Rampart home directory."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


def _import_config_manager(home_path):
    """Import config_manager with a custom RAMPART_HOME, bypassing core.__init__."""
    import importlib.util as iu

    # Set env var BEFORE exec so the module picks it up
    os.environ["RAMPART_HOME"] = str(home_path)

    src = Path(__file__).parent.parent.parent / "core" / "config_manager.py"
    spec = iu.spec_from_file_location("_cm_test", str(src))
    mod = iu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestConfigManager:
    """Tests for ConfigManager CRUD and priority resolution."""

    def test_defaults(self, temp_home):
        mod = _import_config_manager(temp_home)
        cm = mod.ConfigManager(cwd=temp_home)

        assert cm.get("LLM_MODEL") == "gpt-4o"
        assert cm.get("LLM_PROVIDER") == "openai"
        assert cm.get("LLM_TEMPERATURE") == 0.3
        assert cm.get("LLM_MAX_TOKENS") == 2000
        assert cm.get("RAMPART_AUTONOMY") == "L2"
        assert cm.get("RAMPART_MAX_STEPS") == 20
        assert cm.get("SERVER_PORT") == 8000
        assert cm.get("NONEXISTENT_KEY", "fallback") == "fallback"

    def test_set_and_get(self, temp_home):
        mod = _import_config_manager(temp_home)
        cm = mod.ConfigManager(cwd=temp_home)

        cm.set("LLM_MODEL", "gpt-4.1")
        assert cm.get("LLM_MODEL") == "gpt-4.1"
        # Still in-memory, not persisted
        assert not cm.config_path.exists()

    def test_write_and_reload(self, temp_home):
        mod = _import_config_manager(temp_home)
        cm = mod.ConfigManager(cwd=temp_home)

        cm.set("LLM_MODEL", "claude-sonnet-4-6")
        cm.set("LLM_PROVIDER", "anthropic")
        cm.write()

        assert cm.config_path.exists()
        data = json.loads(cm.config_path.read_text())
        assert data["LLM_MODEL"] == "claude-sonnet-4-6"
        assert data["LLM_PROVIDER"] == "anthropic"

        # Reload
        cm2 = mod.ConfigManager(cwd=temp_home)
        assert cm2.get("LLM_MODEL") == "claude-sonnet-4-6"
        assert cm2.get("LLM_PROVIDER") == "anthropic"

    def test_unset(self, temp_home):
        mod = _import_config_manager(temp_home)
        cm = mod.ConfigManager(cwd=temp_home)

        cm.set("LLM_MODEL", "custom-model")
        cm.write()
        assert cm.get("LLM_MODEL") == "custom-model"

        cm.unset("LLM_MODEL")
        cm.write()
        assert cm.get("LLM_MODEL") == "gpt-4o"  # back to default

    def test_reset(self, temp_home):
        mod = _import_config_manager(temp_home)
        cm = mod.ConfigManager(cwd=temp_home)

        cm.set("LLM_MODEL", "custom")
        cm.set("RAMPART_AUTONOMY", "L4")
        cm.write()

        cm.reset()
        assert cm.get("LLM_MODEL") == "gpt-4o"
        assert cm.get("RAMPART_AUTONOMY") == "L2"
        assert not cm.config_path.exists()

    def test_env_var_priority(self, temp_home):
        mod = _import_config_manager(temp_home)
        cm = mod.ConfigManager(cwd=temp_home)

        cm.set("LLM_MODEL", "from-config")
        cm.write()

        # Env var should override config
        os.environ["LLM_MODEL"] = "from-env"
        assert cm.get("LLM_MODEL") == "from-env"
        del os.environ["LLM_MODEL"]

        # Back to config value
        assert cm.get("LLM_MODEL") == "from-config"

    def test_env_var_coercion(self, temp_home):
        mod = _import_config_manager(temp_home)
        cm = mod.ConfigManager(cwd=temp_home)

        os.environ["LLM_TEMPERATURE"] = "0.7"
        assert cm.get("LLM_TEMPERATURE") == 0.7
        del os.environ["LLM_TEMPERATURE"]

        os.environ["RAMPART_MAX_STEPS"] = "50"
        assert cm.get("RAMPART_MAX_STEPS") == 50
        del os.environ["RAMPART_MAX_STEPS"]

    def test_to_dict(self, temp_home):
        mod = _import_config_manager(temp_home)
        cm = mod.ConfigManager(cwd=temp_home)

        cm.set("LLM_MODEL", "test-model")
        d = cm.to_dict()

        assert d["LLM_MODEL"] == "test-model"
        assert d["LLM_PROVIDER"] == "openai"  # default
        assert "LLM_TEMPERATURE" in d
        assert "RAMPART_AUTONOMY" in d

    def test_to_env_file(self, temp_home):
        mod = _import_config_manager(temp_home)
        cm = mod.ConfigManager(cwd=temp_home)

        cm.set("LLM_MODEL", "gpt-4o")
        cm.set("OPENAI_API_KEY", "sk-test123")
        env_content = cm.to_env_file()

        assert "LLM_MODEL=gpt-4o" in env_content
        assert "OPENAI_API_KEY=sk-test123" in env_content
        assert "✦ Rampart Agent" in env_content

    def test_empty_config_dirs_created(self, temp_home):
        mod = _import_config_manager(temp_home)
        mod.ConfigManager(cwd=temp_home)
        assert temp_home.exists()

    def test_config_path_property(self, temp_home):
        mod = _import_config_manager(temp_home)
        cm = mod.ConfigManager(cwd=temp_home)
        assert cm.config_path == temp_home / "config.json"
        assert cm.home == temp_home

    def test_get_source(self, temp_home):
        mod = _import_config_manager(temp_home)
        cm = mod.ConfigManager(cwd=temp_home)

        cm.set("LLM_MODEL", "from-global", layer="global")
        cm.write()
        assert cm.get_source("LLM_MODEL") == "global"
        # Defaults
        assert cm.get_source("LLM_TEMPERATURE") == "default"

    def test_custom_keys(self, temp_home):
        mod = _import_config_manager(temp_home)
        cm = mod.ConfigManager(cwd=temp_home)

        cm.set("MY_CUSTOM_KEY", "custom-value")
        cm.write()

        d = cm.to_dict()
        assert "MY_CUSTOM_KEY" in d
        assert d["MY_CUSTOM_KEY"] == "custom-value"


class TestDiscovery:
    """Tests for Ollama and vLLM auto-discovery."""

    def test_discover_ollama_not_running(self, temp_home):
        mod = _import_config_manager(temp_home)
        result = mod.discover_ollama()
        # Should return None when Ollama is not running
        assert result is None or isinstance(result, dict)

    def test_discover_vllm_not_running(self, temp_home):
        mod = _import_config_manager(temp_home)
        result = mod.discover_vllm()
        assert result is None or isinstance(result, dict)
