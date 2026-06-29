"""✦ Rampart Agent — Interactive Setup Wizard

Provides an interactive terminal UI for first-time setup:
  - LLM provider selection (OpenAI / Anthropic / Ollama / vLLM / skip)
  - Model selection (auto-discovered or manual)
  - Autonomy level configuration
  - Writes config to ~/.rampart/config.yaml

Usage:
    python -m cli.init_wizard
    rampart init
"""

import importlib.util as _iu
import os
import sys
from pathlib import Path

# Allow running directly
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# Import config_manager directly, bypassing core.__init__ (avoids heavy deps)
_cm_path = _PROJECT_ROOT / "core" / "config_manager.py"
_cm_spec = _iu.spec_from_file_location("_rampart_config_manager", str(_cm_path))
_cm = _iu.module_from_spec(_cm_spec)
_cm_spec.loader.exec_module(_cm)
ConfigManager = _cm.ConfigManager
discover_ollama = _cm.discover_ollama
discover_vllm = _cm.discover_vllm

# ── Terminal helpers ───────────────────────────────────────────────────────

_TTY = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    colors = {"g": 32, "y": 33, "b": 34, "c": 36, "r": 31, "w": 37, "dim": 2, "bold": 1, "m": 95}
    return f"\033[{colors.get(code, 0)}m{text}\033[0m" if _TTY else text


def _clear():
    os.system("cls" if os.name == "nt" else "clear")


def _header():
    _clear()
    w = 52
    print(f"\n{_c('c', '╭' + '─' * w + '╮')}")
    print(f"{_c('c', '│')}  {_c('y', '✦')} {_c('bold', _c('w', 'Rampart Agent — Setup Wizard'))}{' ' * 21}{_c('c', '│')}")
    print(f"{_c('c', '│')}  {_c('dim', 'Navigate Complexity with AI'):<52}{_c('c', '│')}")
    print(f"{_c('c', '╰' + '─' * w + '╯')}\n")


def _prompt(text: str, default: str = "") -> str:
    """Prompt for input with a default value."""
    if default:
        hint = f" [{default}]"
        result = input(f"  {text}{_c('dim', hint)}: ").strip()
        return result if result else default
    return input(f"  {text}: ").strip()


def _choice(text: str, options: list, default_idx: int = 0) -> str:
    """Present numbered choices, return selected value."""
    print(f"\n  {_c('bold', text)}")
    for i, opt in enumerate(options):
        label, _value, desc = opt if isinstance(opt, tuple) else (opt, opt, "")
        marker = f"← {_c('g', 'recommended')}" if i == default_idx else ""
        tag = _c("dim", f" ({desc})") if desc else ""
        print(f"    {_c('c', f'[{i+1}]')} {_c('w', label)}{tag} {marker}")
    print()

    choice_raw = _prompt(f"Choose [1-{len(options)}]", str(default_idx + 1))
    try:
        idx = int(choice_raw) - 1
        if 0 <= idx < len(options):
            opt = options[idx]
            return opt[1] if isinstance(opt, tuple) else opt
    except ValueError:
        pass
    opt = options[default_idx]
    return opt[1] if isinstance(opt, tuple) else opt


def _ok(m: str) -> None:
    print(f"  {_c('g', '✓')} {m}")


def _info(m: str) -> None:
    print(f"  {_c('c', 'ℹ')} {m}")


# ── Wizard steps ───────────────────────────────────────────────────────────

def run_wizard(cm: ConfigManager | None = None) -> ConfigManager:
    """Run the full interactive setup wizard.

    Returns a ConfigManager with the new configuration (already written to disk).
    """
    if cm is None:
        cm = ConfigManager()

    _header()

    # ── Step 1: LLM Provider ────────────────────────────────────────────
    print(f"  {_c('bold', _c('y', 'Step 1/4') + ' — Choose your LLM Provider')}")
    print(f"  {_c('dim', 'Rampart needs an LLM backend to think and act.')}")
    print(f"  {_c('dim', 'You can change this anytime with: rampart config set LLM_PROVIDER <name>')}")

    # Auto-discover local providers
    ollama = discover_ollama()
    vllm = discover_vllm()

    ollama_label = "Ollama (Local, Free)"
    if ollama and ollama["models"]:
        ollama_label = f"Ollama (Local — {len(ollama['models'])} models found)"

    vllm_label = "vLLM / Custom OpenAI-compatible"
    if vllm and vllm["models"]:
        vllm_label = f"vLLM / Custom (Local — {len(vllm['models'])} models found)"

    options = [
        ("OpenAI (Cloud)", "openai", "GPT-4o, GPT-4.1, o-series"),
        ("Anthropic (Cloud)", "anthropic", "Claude Opus, Sonnet, Haiku"),
    ]

    if ollama:
        options.insert(0, (ollama_label, "ollama", "No API key needed, runs locally"))
    if vllm:
        options.insert(1 if ollama else 0, (vllm_label, "openai_compatible", "Any OpenAI-compatible server"))

    options.append(("Skip for now", "skip", "Configure manually later"))

    # Default to Ollama if available, otherwise OpenAI
    default_idx = 0 if ollama else (2 if vllm else 2)
    provider = _choice("Select LLM provider:", options, default_idx=default_idx)

    if provider == "skip":
        _info("Skipping LLM setup. Run 'rampart init' again to configure.")
        print(f"\n  {_c('y', '✦')} {_c('bold', 'Setup complete (minimal config).')}")
        print(f"  Run {_c('c', 'rampart init')} to configure an LLM provider later.\n")
        cm.write()
        return cm

    cm.set("LLM_PROVIDER", provider)

    # ── Step 2: Model ──────────────────────────────────────────────────
    print(f"\n  {_c('bold', _c('y', 'Step 2/4') + ' — Choose a Model')}")

    if provider == "ollama" and ollama and ollama["models"]:
        model_options = [(m, m, "") for m in ollama["models"][:10]]
        model = _choice("Select an Ollama model:", model_options, default_idx=0)
        cm.set("LLM_MODEL", model)
        cm.set("LOCAL_LLM_PROVIDER", "ollama")
        cm.set("LOCAL_LLM_MODEL", model)
        if ollama.get("url"):
            cm.set("LOCAL_LLM_URL", ollama["url"] + "/v1")
    elif provider == "openai_compatible" and vllm and vllm["models"]:
        model_options = [(m, m, "") for m in vllm["models"][:10]]
        model = _choice("Select a model:", model_options, default_idx=0)
        cm.set("LLM_MODEL", model)
        cm.set("LOCAL_LLM_PROVIDER", "openai_compatible")
        cm.set("LOCAL_LLM_MODEL", model)
        if vllm.get("url"):
            cm.set("LOCAL_LLM_URL", vllm["url"])
    elif provider == "openai":
        model = _prompt("Model name", "gpt-4o")
        cm.set("LLM_MODEL", model)
        api_key = _prompt("OpenAI API Key (or set OPENAI_API_KEY env var)", "")
        if api_key:
            cm.set("OPENAI_API_KEY", api_key)
        else:
            _info("Skipping API key — set OPENAI_API_KEY env var to use.")
    elif provider == "anthropic":
        model = _prompt("Model name", "claude-sonnet-4-6")
        cm.set("LLM_MODEL", model)
        api_key = _prompt("Anthropic API Key (or set ANTHROPIC_API_KEY env var)", "")
        if api_key:
            cm.set("ANTHROPIC_API_KEY", api_key)
        else:
            _info("Skipping API key — set ANTHROPIC_API_KEY env var to use.")
    else:
        model = _prompt("Model name", "gpt-4o")
        cm.set("LLM_MODEL", model)

    if provider == "ollama":
        _ok(f"Using local model: {cm.get('LLM_MODEL')} (free, no API key needed)")

    # ── Step 3: Autonomy Level ──────────────────────────────────────────
    print(f"\n  {_c('bold', _c('y', 'Step 3/4') + ' — Set Autonomy Level')}")
    print(f"  {_c('dim', 'Controls how independently Rampart acts.')}")

    autonomy_options = [
        ("L1 — Assisted", "L1", "Every action needs your explicit confirmation"),
        ("L2 — Supervised", "L2", "Acts autonomously, reports what it did (recommended)"),
        ("L3 — Autonomous", "L3", "Acts freely within safety policy bounds"),
        ("L4 — Full", "L4", "Complete decision-making authority"),
    ]
    auto_level = _choice("Select autonomy level:", autonomy_options, default_idx=1)
    cm.set("RAMPART_AUTONOMY", auto_level)

    # ── Step 4: Review & Save ───────────────────────────────────────────
    print(f"\n  {_c('bold', _c('y', 'Step 4/4') + ' — Review & Save')}")
    print()

    summary = [
        ("Provider", provider),
        ("Model", cm.get("LLM_MODEL")),
        ("Autonomy", cm.get("RAMPART_AUTONOMY")),
    ]
    if provider == "ollama":
        summary.append(("Ollama URL", cm.get("LOCAL_LLM_URL", "auto")))

    for k, v in summary:
        print(f"    {_c('dim', k + ':')} {_c('w', str(v))}")

    print()
    save = _prompt(f"Save configuration to {cm.config_path}?", "Y")
    if save.lower() in ("y", "yes", ""):
        cm.write()
        print(f"\n  {_c('g', '╭────────────────────────────────────────╮')}")
        print(f"  {_c('g', '│')}  {_c('bold', '✓ Configuration saved!')}              {_c('g', '│')}")
        print(f"  {_c('g', '│')}  Run {_c('c', 'rampart')} to start.                {_c('g', '│')}")
        print(f"  {_c('g', '╰────────────────────────────────────────╯')}\n")
    else:
        _info("Configuration not saved. Run 'rampart init' to try again.\n")

    return cm


# ── Quick start (non-interactive) ──────────────────────────────────────────

def quick_start_ollama() -> ConfigManager | None:
    """Try to auto-configure with Ollama. Returns None if not possible.

    This is called automatically when the user runs `rampart`
    with no prior configuration — zero-friction onboarding.
    """
    ollama = discover_ollama()
    if not ollama or not ollama["models"]:
        return None

    cm = ConfigManager()
    cm.set("LLM_PROVIDER", "openai")
    cm.set("LLM_MODEL", ollama["models"][0])
    cm.set("LOCAL_LLM_PROVIDER", "ollama")
    cm.set("LOCAL_LLM_MODEL", ollama["models"][0])
    cm.set("LOCAL_LLM_URL", ollama["url"] + "/v1")
    cm.set("OPENAI_API_KEY", "not-needed")
    cm.set("OPENAI_API_BASE", ollama["url"] + "/v1")
    cm.write()
    return cm


# ── CLI entry point ────────────────────────────────────────────────────────

def main():
    cm = ConfigManager()
    run_wizard(cm)


if __name__ == "__main__":
    main()
