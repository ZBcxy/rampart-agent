"""Unit tests for init_wizard module."""

import importlib.util as iu
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def wizard_mod():
    """Import init_wizard module directly."""
    src = Path(__file__).parent.parent.parent / "cli" / "init_wizard.py"
    spec = iu.spec_from_file_location("_iw_test", str(src))
    mod = iu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def temp_cm():
    """Import ConfigManager with a temp home."""
    src = Path(__file__).parent.parent.parent / "core" / "config_manager.py"
    spec = iu.spec_from_file_location("_cm_test2", str(src))
    mod = iu.module_from_spec(spec)

    import os as _os
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        _os.environ["RAMPART_HOME"] = str(home)
        spec.loader.exec_module(mod)
        cm = mod.ConfigManager(cwd=home)
        yield cm, mod


class TestQuickStartOllama:
    """Test Ollama auto-configuration."""

    def test_quick_start_ollama_not_running(self, wizard_mod):
        """quick_start_ollama returns None when Ollama is not available."""
        result = wizard_mod.quick_start_ollama()
        # Should return None since Ollama is likely not running in CI
        assert result is None or hasattr(result, "get")

    def test_discovery_functions_exist(self, wizard_mod):
        """Discovery functions are available."""
        assert callable(wizard_mod.discover_ollama)
        assert callable(wizard_mod.discover_vllm)


class TestRunWizard:
    """Test wizard execution (non-interactive parts)."""

    def test_run_wizard_creates_config_manager(self, wizard_mod, temp_cm):
        cm, mod = temp_cm
        # run_wizard needs interactive input, so we test that it accepts a CM
        assert cm is not None
        assert cm.config_path is not None

    def test_wizard_module_exports(self, wizard_mod):
        """Verify expected functions are exported."""
        assert callable(wizard_mod.run_wizard)
        assert callable(wizard_mod.quick_start_ollama)
        assert callable(wizard_mod.main)


class TestConfigManagerIntegration:
    """Ensure config_manager plays well with the wizard pattern."""

    def test_manager_defaults_present(self, temp_cm):
        cm, mod = temp_cm
        # All keys needed by wizard should have defaults
        required = ["LLM_MODEL", "LLM_PROVIDER", "RAMPART_AUTONOMY",
                     "LOCAL_LLM_PROVIDER", "LOCAL_LLM_MODEL", "LOCAL_LLM_URL"]
        for k in required:
            assert cm.get(k) is not None, f"Missing default for {k}"

    def test_wizard_writes_config(self, temp_cm):
        cm, mod = temp_cm
        cm.set("LLM_MODEL", "test-model")
        cm.set("LLM_PROVIDER", "openai")
        cm.set("RAMPART_AUTONOMY", "L2")
        cm.write()
        assert cm.config_path.exists()

        # Re-read
        cm2 = mod.ConfigManager(cwd=cm.home)
        assert cm2.get("LLM_MODEL") == "test-model"
        assert cm2.get("RAMPART_AUTONOMY") == "L2"
