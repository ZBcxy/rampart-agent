#!/usr/bin/env python3
"""✦ Polaris Agent — Complete Lifecycle CLI

Navigate Complexity with AI.

Lifecycle commands (like Claude Code / OpenClaw / Codex):

    polaris "analyze this file"     Single-shot (non-interactive)
    echo "..." | polaris            Pipe / stdin mode
    polaris                         Interactive REPL (default)
    polaris init                    Interactive setup wizard (= setup)
    polaris login                   Save API keys securely
    polaris logout                  Remove stored credentials
    polaris config [get|set|...]    Configuration management
    polaris profiles [list|use|...] Named config profiles
    polaris sessions [list|resume]  Session history
    polaris update                  Self-update via pip
    polaris doctor                  Environment diagnostics
    polaris mcp [add|list|remove]   MCP server management
    polaris exec <file>             Execute a task file
    polaris --model <name>          Override model for this session
    polaris --approval-mode <mode>  Override autonomy for this session
"""

import argparse
import atexit
import json
import os
import readline
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# ── Terminal helpers ───────────────────────────────────────────────────────

_TTY = sys.stdout.isatty()
_FORCE_COLOR = os.environ.get("FORCE_COLOR", "") or os.environ.get("CLICOLOR_FORCE", "")
_COLOR = _TTY or bool(_FORCE_COLOR)
_NO_COLOR = os.environ.get("NO_COLOR", "")


def _c(code: str, text: str) -> str:
    if not _COLOR or _NO_COLOR:
        return text
    colors = {"g": "32", "y": "33", "b": "34", "c": "36", "r": "31", "w": "97",
              "dim": "2", "bold": "1", "m": "95", "gray": "90"}
    return f"\033[{colors.get(code, '0')}m{text}\033[0m"


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences, returning only visible characters."""
    import re
    return re.sub(r"\033\[[0-9;]*m", "", text)


# ── Direct module imports (bypass core.__init__ heavy deps) ────────────────

def _import_by_path(rel_path: str, name: str = None):
    """Import a Python module by filesystem path, bypassing package __init__."""
    import importlib.util as iu
    full = _PROJECT_ROOT / rel_path
    spec = iu.spec_from_file_location(name or full.stem, str(full))
    mod = iu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_logo = _import_by_path("core/logo.py", "_polaris_logo")
_config = _import_by_path("core/config_manager.py", "_polaris_config")
_init_wiz = _import_by_path("cli/init_wizard.py", "_polaris_init_wizard")

PolarisLogo = _logo.PolarisLogo
display_version_info = _logo.display_version_info
BRAND_MARK = _logo.BRAND_MARK
ConfigManager = _config.ConfigManager
discover_ollama = _config.discover_ollama

# ── Constants ──────────────────────────────────────────────────────────────

POLARIS_HOME = Path(os.environ.get("POLARIS_HOME", Path.home() / ".polaris"))
SESSIONS_DIR = POLARIS_HOME / "sessions"
PROFILES_DIR = POLARIS_HOME / "profiles"
HISTORY_FILE = POLARIS_HOME / "history"
MCP_CONFIG_FILE = POLARIS_HOME / "mcp_servers.json"
VERSION = "1.1.0"


# ── Help text ──────────────────────────────────────────────────────────────

CLI_EPILOG = f"""
{_c('bold', '✦ Polaris Agent v' + VERSION + ' — Navigate Complexity with AI')}

{_c('y', 'Lifecycle:')}
  {_c('c', 'polaris')} "analyze this file"        Single-shot mode
  {_c('c', 'echo')} "..." | {_c('c', 'polaris')}               Pipe / stdin mode
  {_c('c', 'polaris')}                         Interactive REPL (default)
  {_c('c', 'polaris')} exec <file>             Execute a task file

{_c('y', 'Setup & Auth:')}
  {_c('c', 'polaris')} init                    Interactive setup wizard
  {_c('c', 'polaris')} login                   Save API keys
  {_c('c', 'polaris')} logout                  Remove stored credentials
  {_c('c', 'polaris')} doctor                  Environment diagnostics

{_c('y', 'Configuration:')}
  {_c('c', 'polaris')} config                  Show all configuration
  {_c('c', 'polaris')} config get <key>        Get a value
  {_c('c', 'polaris')} config set <key> <val>  Set a value
  {_c('c', 'polaris')} config unset <key>      Remove a key
  {_c('c', 'polaris')} config reset            Reset to defaults
  {_c('c', 'polaris')} config path             Show config file path
  {_c('c', 'polaris')} profiles list           List named profiles
  {_c('c', 'polaris')} profiles use <name>     Switch to a profile

{_c('y', 'Sessions:')}
  {_c('c', 'polaris')} sessions list           List recent sessions
  {_c('c', 'polaris')} sessions resume <id>    Resume a session

{_c('y', 'Maintenance:')}
  {_c('c', 'polaris')} update                  Self-update (pip)
  {_c('c', 'polaris')} mcp add <name> <cmd>    Register an MCP server
  {_c('c', 'polaris')} mcp list                List MCP servers
  {_c('c', 'polaris')} mcp remove <name>       Remove an MCP server

{_c('y', 'Flags:')}
  {_c('c', '--model')}, {_c('c', '-m')} <name>          Override model
  {_c('c', '--approval-mode')} <mode>    Override autonomy (L0-L4)
  {_c('c', '--pipe')}, {_c('c', '-p')}               Explicit pipe mode
  {_c('c', '--output-format')} <fmt>     Output format (text | json)
  {_c('c', '--resume')} <id>             Resume a session
  {_c('c', '--no-logo')}                 Skip splash screen
  {_c('c', '--logo')} [--style ...]      Display logo & exit
  {_c('c', '--version')}, {_c('c', '-v')}           Show version info
  {_c('c', '--help')}, {_c('c', '-h')}              Show this help
"""


# ── Config helpers ─────────────────────────────────────────────────────────

def _get_cm():
    return ConfigManager()


def _init_agent(cm=None, model_override=None, approval_override=None):
    """Initialize agent with resolved config. Returns (agent, cm)."""
    if cm is None:
        cm = _get_cm()

    from core.agent import Agent, AgentConfig

    local_provider = cm.get("LOCAL_LLM_PROVIDER")
    model = model_override or cm.get("LLM_MODEL", "gpt-4o")

    if local_provider:
        base_url = cm.get("LOCAL_LLM_URL")
        if local_provider == "ollama" and not base_url:
            base_url = "http://localhost:11434/v1"
        agent_config = AgentConfig(
            model=model, provider="openai", api_key="not-needed",
            api_base=base_url,
            max_steps=int(cm.get("POLARIS_MAX_STEPS", 20)),
        )
    else:
        agent_config = AgentConfig(
            model=model,
            provider=cm.get("LLM_PROVIDER", "openai"),
            api_key=cm.get("OPENAI_API_KEY") or cm.get("ANTHROPIC_API_KEY"),
            api_base=cm.get("OPENAI_API_BASE") or None,
            max_steps=int(cm.get("POLARIS_MAX_STEPS", 20)),
        )

    agent = Agent(config=agent_config)
    try:
        from tools.registry import ToolRegistry
        r = ToolRegistry()
        r.register_all()
        for name in r.list_all():
            agent.register_tool(name, _make_tool_func(r, name),
                                description=r.get(name).description if r.get(name) else "")
    except ImportError:
        pass

    return agent, cm


def _make_tool_func(registry, tool_name):
    def tool_func(**kwargs):
        return registry.execute(tool_name, **kwargs)
    return tool_func


# ── Session management ─────────────────────────────────────────────────────

def _ensure_sessions_dir():
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _save_session(session_id: str, messages: list):
    """Save session messages to disk."""
    _ensure_sessions_dir()
    session_file = SESSIONS_DIR / f"{session_id}.json"
    meta_file = POLARIS_HOME / "sessions_index.json"

    session_file.write_text(json.dumps(messages, indent=2, ensure_ascii=False))

    # Update index
    index = {}
    if meta_file.exists():
        index = json.loads(meta_file.read_text())
    index[session_id] = {
        "id": session_id,
        "message_count": len(messages),
        "last_message": messages[-1].get("content", "")[:100] if messages else "",
        "model": messages[-1].get("model", "") if messages else "",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    meta_file.write_text(json.dumps(index, indent=2, ensure_ascii=False))


def cmd_sessions_list():
    """List recent sessions."""
    meta_file = POLARIS_HOME / "sessions_index.json"
    if not meta_file.exists():
        print(f"{_c('dim', 'No sessions found.')}")
        return

    index = json.loads(meta_file.read_text())
    if not index:
        print(f"{_c('dim', 'No sessions found.')}")
        return

    print(f"\n{_c('c', '┌' + '─' * 68 + '┐')}")
    print(f"{_c('c', '│')}  {_c('bold', '✦ Polaris Sessions'):<66}{_c('c', '│')}")
    print(f"{_c('c', '├' + '─' * 68 + '┤')}")
    for sid, meta in sorted(index.items(), key=lambda x: x[1].get("updated_at", ""), reverse=True)[:20]:
        ts = meta.get("updated_at", "")[:19].replace("T", " ")
        preview = meta.get("last_message", "")[:50]
        count = meta.get("message_count", 0)
        model = meta.get("model", "")[:15]
        print(f"{_c('c', '│')} {_c('y', sid[:12])}  {_c('dim', ts)}  {model:<15}  {count:>3}msgs  {preview:<50}{_c('c', '│')}")
    print(f"{_c('c', '└' + '─' * 68 + '┘')}\n")


def cmd_sessions_resume(session_id: str):
    """Resume a session from history."""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if not session_file.exists():
        # Try partial match
        matches = list(SESSIONS_DIR.glob(f"{session_id[:8]}*.json"))
        if not matches:
            print(f"{_c('r', f'Session not found: {session_id}')}")
            print(f"{_c('dim', 'Use \"polaris sessions list\" to see available sessions.')}")
            return
        session_file = matches[0]

    messages = json.loads(session_file.read_text())
    print(f"{_c('g', f'Resuming session with {len(messages)} messages.')}")
    # Replay the conversation context
    for msg in messages[-10:]:
        role = msg.get("role", "?")
        content = msg.get("content", "")[:200]
        if role == "user":
            print(f"{_c('c', 'You:')} {content}")
        else:
            print(f"{_c('y', 'Polaris:')} {content}")
    print(f"\n{_c('dim', '(Type your next message to continue this session)')}")
    return messages  # Return for interactive mode to continue


# ── Self-update ────────────────────────────────────────────────────────────

def cmd_update():
    """Self-update Polaris Agent via pip."""
    print(f"{_c('c', '✦ Checking for updates...')}")
    import subprocess
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "polaris-agent", "-q"],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        # Check if anything was actually installed
        if "Requirement already satisfied" in r.stdout:
            print(f"{_c('g', '✓ Polaris Agent is up to date (v' + VERSION + ').')}")
        else:
            print(f"{_c('g', '✓ Polaris Agent updated successfully. Restart to use the new version.')}")
    else:
        print(f"{_c('y', '! Could not auto-update:')} {r.stderr[:200]}")
        print(f"{_c('dim', 'Try: pip install --upgrade polaris-agent')}")


# ── Doctor ─────────────────────────────────────────────────────────────────

def cmd_doctor():
    """Environment diagnostics — checks Python, Ollama, API keys, PATH, disk."""
    import subprocess

    print(f"\n{_c('c', '╭' + '─' * 50 + '╮')}")
    print(f"{_c('c', '│')}  {_c('bold', '✦ Polaris Doctor — Environment Diagnostics'):<48}{_c('c', '│')}")
    print(f"{_c('c', '╰' + '─' * 50 + '╯')}\n")

    checks = []

    # Python
    print(f"{_c('bold', 'Python')}")
    py_ok = sys.version_info >= (3, 11)
    print(f"  {'✓' if py_ok else '✗'} Python {sys.version.split()[0]} {'(need 3.11+)' if not py_ok else ''}")
    print(f"    Executable: {sys.executable}")
    checks.append(("Python 3.11+", py_ok))

    # Polaris home
    print(f"\n{_c('bold', 'Polaris Home')}")
    print(f"  {'✓' if POLARIS_HOME.exists() else '✗'} {POLARIS_HOME}")
    if POLARIS_HOME.exists():
        contents = [p.name for p in sorted(POLARIS_HOME.iterdir()) if not p.name.startswith(".")]
        print(f"    Contents: {', '.join(contents) if contents else '(empty)'}")
    checks.append(("Polaris home", POLARIS_HOME.exists()))

    # Config
    cm = _get_cm()
    has_config = cm.config_path.exists()
    print(f"\n{_c('bold', 'Configuration')}")
    print(f"  {'✓' if has_config else '✗'} Config file: {cm.config_path}")
    if has_config:
        model = cm.get("LLM_MODEL", "not set")
        provider = cm.get("LLM_PROVIDER", "not set")
        autonomy = cm.get("POLARIS_AUTONOMY", "L2")
        print(f"    Model: {model}  |  Provider: {provider}  |  Autonomy: {autonomy}")
    checks.append(("Config file", has_config))

    # Ollama
    print(f"\n{_c('bold', 'Local LLM Providers')}")
    ollama = discover_ollama()
    if ollama:
        models = ollama.get("models", [])
        print(f"  ✓ Ollama running")
        print(f"    URL: {ollama.get('url', '?')}")
        print(f"    Models: {', '.join(models[:8])}{'...' if len(models) > 8 else ''}")
        checks.append(("Ollama", True))
    else:
        print(f"  - Ollama not detected (fine if using cloud LLMs)")
        checks.append(("Ollama", None))

    # API keys
    print(f"\n{_c('bold', 'API Keys')}")
    for k, label in [("OPENAI_API_KEY", "OpenAI"), ("ANTHROPIC_API_KEY", "Anthropic")]:
        val = cm.get(k)
        if val:
            masked = val[:4] + "****" if len(val) > 4 else "****"
            print(f"  ✓ {label}: {masked}")
            checks.append((f"{label} key", True))
        else:
            print(f"  - {label}: not set")
            checks.append((f"{label} key", False))

    # PATH
    print(f"\n{_c('bold', 'PATH')}")
    bin_dir = str(Path.home() / ".local" / "bin")
    in_path = bin_dir in os.environ.get("PATH", "")
    print(f"  {'✓' if in_path else '✗'} {bin_dir} in PATH")
    if not in_path:
        print(f"  {_c('y', '! Add to PATH: export PATH=\"' + bin_dir + ':$PATH\"')}")
    checks.append(("PATH", in_path))

    # Disk
    print(f"\n{_c('bold', 'Disk')}")
    try:
        usage = shutil.disk_usage(POLARIS_HOME if POLARIS_HOME.exists() else Path.home())
        gb_free = usage.free / (1024 ** 3)
        icon = "✓" if gb_free > 1 else "✗"
        print(f"  {icon} Free: {gb_free:.1f} GB")
        checks.append(("Disk (>1GB free)", gb_free > 1))
    except Exception:
        pass

    # Summary
    passed = sum(1 for _, ok in checks if ok is True)
    warned = sum(1 for _, ok in checks if ok is None)
    failed = sum(1 for _, ok in checks if ok is False)
    total = len(checks)

    print(f"\n{_c('c', '┌' + '─' * 50 + '┐')}")
    print(f"{_c('c', '│')}  {_c('bold', f'Results: {passed}✓  {warned}-  {failed}✗  ({total} checks)'):<48}{_c('c', '│')}")
    print(f"{_c('c', '└' + '─' * 50 + '┘')}\n")

    if failed > 0:
        print(f"{_c('y', 'Run \"polaris init\" to fix configuration issues.')}\n")


# ── Auth / Login ───────────────────────────────────────────────────────────

def cmd_login():
    """Interactive login — securely save API keys."""
    cm = _get_cm()
    print(f"\n{_c('bold', _c('y', '✦ Polaris Login'))}")
    print(f"{_c('dim', 'Enter your API keys. Leave blank to skip.')}")
    print(f"{_c('dim', 'Keys are stored in ' + str(cm.config_path))}\n")

    openai_key = _secure_input("OpenAI API Key", cm.get("OPENAI_API_KEY"))
    anthropic_key = _secure_input("Anthropic API Key", cm.get("ANTHROPIC_API_KEY"))

    if openai_key:
        cm.set("OPENAI_API_KEY", openai_key)
        _ok("OpenAI key saved")
    if anthropic_key:
        cm.set("ANTHROPIC_API_KEY", anthropic_key)
        _ok("Anthropic key saved")

    cm.write()
    if openai_key or anthropic_key:
        print(f"\n{_c('g', '✓ Credentials saved. Run \"polaris\" to start.')}\n")
    else:
        print(f"\n{_c('y', 'No keys entered. Run \"polaris login\" again to add keys.')}\n")


def cmd_logout():
    """Remove stored API keys."""
    cm = _get_cm()
    cm.set("OPENAI_API_KEY", "")
    cm.set("ANTHROPIC_API_KEY", "")
    cm.write()
    print(f"{_c('g', '✓ Credentials removed from config.')}")
    print(f"{_c('dim', 'API keys in environment variables are still active for this session.')}")


def _secure_input(prompt: str, current: str = "") -> str:
    """Prompt for a value, showing masked existing value."""
    if current and len(current) > 4:
        hint = f" [{current[:4]}****]"
    elif current:
        hint = f" [{current}]"
    else:
        hint = ""
    return input(f"  {prompt}{_c('dim', hint)}: ").strip()


# ── Profiles ───────────────────────────────────────────────────────────────

def cmd_profiles_list():
    """List named config profiles."""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    profiles = list(PROFILES_DIR.glob("*.json"))
    current = _get_cm().config_path

    print(f"\n{_c('bold', '✦ Config Profiles:')}\n")
    if not profiles:
        print(f"  {_c('dim', 'No profiles found. Create one with:')}")
        print(f"  {_c('c', 'polaris config export --profile work')}")
        print(f"  {_c('c', 'polaris profiles use work')}\n")
        return

    for p in sorted(profiles):
        data = json.loads(p.read_text())
        model = data.get("LLM_MODEL", "?")
        provider = data.get("LLM_PROVIDER", "?")
        marker = " ← current" if str(current) == str(p) else ""
        print(f"  {_c('y', p.stem)}  {provider}/{model}{_c('g', marker)}")

    print(f"\n{_c('dim', 'Use \"polaris profiles use <name>\" to switch.')}\n")


def cmd_profiles_use(name: str):
    """Switch to a named profile."""
    profile_path = PROFILES_DIR / f"{name}.json"
    if not profile_path.exists():
        print(f"{_c('r', f'Profile not found: {name}')}")
        # Offer to create from current config
        print(f"{_c('dim', 'Create it from current config:')}")
        print(f"{_c('c', f'  polaris config export --profile {name}')}")
        return

    # Copy profile to active config
    data = json.loads(profile_path.read_text())
    cm = _get_cm()
    for k, v in data.items():
        cm.set(k, v)
    cm.write()
    print(f"{_c('g', f'✓ Switched to profile {name!r}.')}")
    model = data.get('LLM_MODEL', '?')
    provider = data.get('LLM_PROVIDER', '?')
    print(f"{_c('dim', f'  Model: {model}  |  Provider: {provider}')}")


def cmd_config_export(profile_name: str):
    """Export current config as a named profile."""
    cm = _get_cm()
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    profile_path = PROFILES_DIR / f"{profile_name}.json"
    profile_path.write_text(json.dumps(cm.to_dict(), indent=2, ensure_ascii=False))
    print(f"{_c('g', '✓ Profile ' + repr(profile_name) + ' saved.')}")
    print(f"{_c('dim', f'  Switch to it: polaris profiles use {profile_name}')}")


# ── MCP management ─────────────────────────────────────────────────────────

def cmd_mcp_list():
    """List registered MCP servers."""
    if not MCP_CONFIG_FILE.exists():
        print(f"\n{_c('dim', 'No MCP servers registered.')}")
        print(f"{_c('dim', 'Add one: polaris mcp add <name> <command> [args...]')}")
        print(f"{_c('dim', 'Example: polaris mcp add filesystem npx -y @modelcontextprotocol/server-filesystem .')}\n")
        return

    servers = json.loads(MCP_CONFIG_FILE.read_text())
    print(f"\n{_c('bold', '✦ MCP Servers:')}\n")
    for name, cfg in servers.items():
        cmd_str = " ".join(cfg.get("args", []))
        print(f"  {_c('y', name)}")
        print(f"    Command: {cfg.get('command', '?')} {cmd_str[:60]}")
        print(f"    Transport: {cfg.get('transport', 'stdio')}")
    print()


def cmd_mcp_add(name: str, cmd: str):
    """Register an MCP server."""
    servers = {}
    if MCP_CONFIG_FILE.exists():
        servers = json.loads(MCP_CONFIG_FILE.read_text())

    parts = cmd.split()
    command = parts[0] if parts else "python"
    cmd_args = parts[1:] if len(parts) > 1 else []

    servers[name] = {
        "command": command,
        "args": cmd_args,
        "transport": "stdio",
        "added_at": datetime.now(timezone.utc).isoformat(),
    }
    MCP_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    MCP_CONFIG_FILE.write_text(json.dumps(servers, indent=2, ensure_ascii=False))
    print(f"{_c('g', '✓ MCP server ' + repr(name) + ' registered.')}")
    print(f"{_c('dim', '  Edit: ' + str(MCP_CONFIG_FILE))}")


def cmd_mcp_remove(name: str):
    """Remove an MCP server."""
    if not MCP_CONFIG_FILE.exists():
        print(f"{_c('r', 'No MCP servers registered.')}")
        return

    servers = json.loads(MCP_CONFIG_FILE.read_text())
    if name not in servers:
        print(f"{_c('r', f'MCP server not found: {name}')}")
        return

    del servers[name]
    MCP_CONFIG_FILE.write_text(json.dumps(servers, indent=2, ensure_ascii=False))
    print(f"{_c('g', '✓ MCP server ' + repr(name) + ' removed.')}")


# ── Config commands ────────────────────────────────────────────────────────

def cmd_config_show():
    """Display full configuration with layer sources (like Claude Code)."""
    cm = _get_cm()
    data = cm.to_dict()

    BOX_W = 70
    INNER_W = BOX_W - 2

    def _pad(text: str, width: int) -> str:
        visible = _strip_ansi(str(text))
        return str(text) + " " * max(0, width - len(visible))

    def _row(*cols: tuple[str, int]) -> str:
        parts = [_pad(text, w) for text, w in cols]
        return f"{_c('c', '│')} {_pad('  '.join(parts), INNER_W)} {_c('c', '│')}"

    top    = _c("c", "┌" + "─" * BOX_W + "┐")
    sep    = _c("c", "├" + "─" * BOX_W + "┤")
    bottom = _c("c", "└" + "─" * BOX_W + "┘")
    empty  = _c("c", "│") + " " * BOX_W + _c("c", "│")

    # Source labels
    SRC = {"env": "ENV", "local": "LOCAL", "project": "PROJ", "global": "GLOB", "default": "DEF"}
    SRC_C = {"env": _c("y", "ENV"), "local": _c("m", "LOC"), "project": _c("b", "PRJ"),
             "global": _c("c", "GLB"), "default": _c("dim", "DEF")}

    print(f"\n{top}")
    print(_row((_c("bold", "✦ Polaris Agent — Configuration"), INNER_W)))
    # Show layer files
    for label, path in cm.all_paths():
        suffix = _c("g", " ✓") if path and path.exists() else _c("dim", " —")
        p = str(path) if path else "(none)"
        print(_row((_c("dim", label + ":"), 8), (_c("dim", p + suffix), 56)))
    print(sep)

    categories = [
        ("LLM Provider", ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "LLM_MODEL", "LLM_PROVIDER",
                           "LLM_TEMPERATURE", "LLM_MAX_TOKENS", "OPENAI_API_BASE"]),
        ("Local LLM", ["LOCAL_LLM_PROVIDER", "LOCAL_LLM_MODEL", "LOCAL_LLM_URL"]),
        ("Agent Runtime", ["POLARIS_AUTONOMY", "POLARIS_MAX_STEPS", "POLARIS_LOG_LEVEL"]),
        ("Server", ["SERVER_HOST", "SERVER_PORT", "TOKEN_EXPIRE_HOURS", "RATE_LIMIT_USER"]),
        ("Memory", ["REDIS_HOST", "REDIS_PORT", "EMBEDDING_PROVIDER", "EMBEDDING_MODEL"]),
    ]

    for cat, keys in categories:
        print(_row((_c("y", cat), INNER_W)))
        for k in keys:
            v = data.get(k, "")
            src = cm.get_source(k)
            src_tag = SRC_C.get(src, src)

            if k.endswith("_API_KEY") or k == "JWT_SECRET":
                v = str(v)[:4] + "****" if v and len(str(v)) > 4 else _c("dim", "(not set)")
            elif v == "" or v is None:
                v = _c("dim", "(default)")

            print(_row((_c("dim", k), 24), (str(v), 26), (src_tag, 5)))
        print(empty)

    print(f"{bottom}\n")


def _ok(msg): print(f"{_c('g', '✓')} {msg}")


# ── Single-shot mode (polaris "prompt") ────────────────────────────────────

def run_single_shot(prompt: str, model_override=None, approval_override=None, output_format: str = "text"):
    """Non-interactive single-shot execution. Returns exit code.

    Args:
        output_format: "text" for human-readable, "json" for structured output.
    """
    import asyncio

    cm = _get_cm()
    model_name = cm.get('LLM_MODEL', '?')

    # Check if configured
    if not _check_configured(cm):
        if output_format == "json":
            print(json.dumps({"error": "not_configured", "message": "Run polaris init or polaris login first."}))
        else:
            print(f"{_c('r', '✗ Not configured.')} Run {_c('c', 'polaris init')} or {_c('c', 'polaris login')} first.", file=sys.stderr)
        return 1

    try:
        agent, cm = _init_agent(cm, model_override, approval_override)
    except Exception as e:
        if output_format == "json":
            print(json.dumps({"error": "init_failed", "message": str(e)}))
        else:
            print(f"{_c('r', f'Failed to initialize: {e}')}", file=sys.stderr)
            print(f"{_c('y', 'Run \"polaris init\" to configure.')}", file=sys.stderr)
        return 1

    if output_format != "json":
        print(f"{_c('dim', f'Polaris v{VERSION}  |  {model_name}  |  processing...')}", file=sys.stderr)

    try:
        result = asyncio.run(agent.run(prompt))
        if output_format == "json":
            output = {
                "success": result.success,
                "model": model_name,
                "summary": result.summary[:2000] if result.summary else "",
                "tool_calls": [],
            }
            if result.tool_calls:
                for tc in result.tool_calls[-10:]:
                    output["tool_calls"].append({
                        "tool": tc.get("tool", ""),
                        "success": tc.get("error") is None,
                        "result": str(tc.get("result", tc.get("error", "")))[:200],
                    })
            print(json.dumps(output, indent=2, ensure_ascii=False))
            return 0 if result.success else 1

        if result.success:
            print(result.summary)
            if result.tool_calls:
                for tc in result.tool_calls[-5:]:
                    status = "✓" if tc.get("error") is None else "✗"
                    print(f"  {status} {tc['tool']}: {str(tc.get('result', tc.get('error', '')))[:120]}")
            return 0
        else:
            print(f"{_c('r', result.summary)}", file=sys.stderr)
            return 1
    except Exception as e:
        if output_format == "json":
            print(json.dumps({"error": "execution_failed", "message": str(e)}))
        else:
            print(f"{_c('r', f'Error: {e}')}", file=sys.stderr)
        return 1


# ── Pipe / stdin mode ──────────────────────────────────────────────────────

def run_pipe_mode(model_override=None):
    """Read from stdin and process. Like: echo '...' | polaris"""
    if _TTY:
        return None  # No pipe data
    if sys.stdin.isatty():
        return None

    prompt = sys.stdin.read().strip()
    if not prompt:
        return 0

    return run_single_shot(prompt, model_override)


# ── Interactive REPL ───────────────────────────────────────────────────────

def run_interactive(model_override=None, approval_override=None, resume_session_id=None, show_logo=True):
    """Full interactive REPL with readline history, session tracking."""
    import asyncio

    cm = _get_cm()

    # Auto-detect Ollama
    _auto_configure_ollama(cm)

    # Setup readline history
    _setup_readline()

    # Show splash
    if show_logo:
        PolarisLogo(animate=True, show_info=True).display()

    # Check if configured
    if not _check_configured(cm):
        print(f"{_c('y', 'Run \"polaris init\" for interactive setup, or \"polaris login\" to add API keys.')}\n")
        return

    # Init agent
    try:
        agent, cm = _init_agent(cm, model_override, approval_override)
    except Exception as e:
        print(f"{_c('r', f'Failed to initialize agent: {e}')}")
        print(f"{_c('y', 'Run \"polaris init\" to configure your LLM provider.')}\n")
        return

    model = cm.get("LLM_MODEL", "?")
    autonomy = cm.get("POLARIS_AUTONOMY", "L2")

    print(f"\n{_c('g', f'Polaris Agent — Model: {model}  |  Autonomy: {autonomy}')}")
    print(f"{_c('dim', 'Type \"exit\" to quit, \"/help\" for commands')}\n")

    # Session tracking
    session_id = resume_session_id or f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    messages = []
    if resume_session_id:
        session_file = SESSIONS_DIR / f"{resume_session_id}.json"
        if session_file.exists():
            messages = json.loads(session_file.read_text())

    def save():
        if messages:
            _save_session(session_id, messages)

    atexit.register(save)

    # Prompt
    try:
        while True:
            try:
                user_input = input(f"{_c('c', '✦')} {_c('bold', 'polaris')}{_c('dim', '>')} ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not user_input:
                continue

            # Slash commands
            if user_input.startswith("/"):
                _handle_slash_command(user_input, cm)
                continue

            # Built-in commands
            if user_input.lower() in ("exit", "quit", "q"):
                break
            elif user_input.lower() in ("help", "h", "?"):
                _show_repl_help()
                continue
            elif user_input.lower() == "version":
                print(f"Polaris Agent v{VERSION}")
                continue
            elif user_input.lower() == "clear":
                os.system("cls" if os.name == "nt" else "clear")
                continue
            elif user_input.lower() == "config":
                cmd_config_show()
                continue

            # Track message
            messages.append({"role": "user", "content": user_input, "time": datetime.now(timezone.utc).isoformat()})

            print(f"{_c('dim', 'Thinking...')}")
            try:
                result = asyncio.run(agent.run(user_input))
                if result.success:
                    print(f"{_c('g', result.summary[:2000])}")
                    messages.append({"role": "assistant", "content": result.summary[:2000],
                                     "model": model, "time": datetime.now(timezone.utc).isoformat()})
                    if result.tool_calls:
                        for tc in result.tool_calls[-5:]:
                            status = "✓" if tc.get("error") is None else "✗"
                            print(f"  {status} {tc['tool']}: {str(tc.get('result', tc.get('error', '')))[:120]}")
                else:
                    print(f"{_c('r', result.summary)}")
                    messages.append({"role": "error", "content": result.summary,
                                     "time": datetime.now(timezone.utc).isoformat()})
            except Exception as e:
                print(f"{_c('r', f'Error: {e}')}")

        save()
        print(f"\n{_c('y', f'Goodbye! Session saved: {session_id[:16]}')}")
        print(f"{_c('dim', f'Resume: polaris sessions resume {session_id}')}\n")

    except KeyboardInterrupt:
        save()
        print(f"\n{_c('y', 'Goodbye! ✦')}\n")


def _setup_readline():
    """Configure readline with history persistence."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        readline.read_history_file(str(HISTORY_FILE))
    except (FileNotFoundError, OSError):
        pass
    readline.set_history_length(1000)
    atexit.register(lambda: readline.write_history_file(str(HISTORY_FILE)))


def _check_configured(cm) -> bool:
    """Check if Polaris is minimally configured to run."""
    provider = cm.get("LLM_PROVIDER")
    if provider == "ollama" or cm.get("LOCAL_LLM_PROVIDER"):
        return True  # Local — no API key needed
    if cm.get("OPENAI_API_KEY") or cm.get("ANTHROPIC_API_KEY"):
        return True  # Cloud — has API key
    if os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"):
        return True  # Env var
    return False


def _auto_configure_ollama(cm):
    """If no config and Ollama is available, auto-configure."""
    if cm.config_path.exists() and cm.get("OPENAI_API_KEY") or cm.get("LOCAL_LLM_PROVIDER"):
        return  # Already configured
    result = _init_wiz.quick_start_ollama()
    if result:
        print(f"\n{_c('g', '✦ Auto-detected Ollama!')}")
        auto_model = result.get('LLM_MODEL', '?')
        print(f"{_c('dim', f'  Model: {auto_model}')}")
        print(f"{_c('dim', '  Run \"polaris init\" to change.')}\n")


def _handle_slash_command(cmd: str, cm):
    """Handle /slash commands in the REPL."""
    parts = cmd.split()
    cmd_name = parts[0].lower()
    if cmd_name == "/help":
        _show_repl_help()
    elif cmd_name == "/config":
        cmd_config_show()
    elif cmd_name == "/model" and len(parts) > 1:
        cm.set("LLM_MODEL", parts[1])
        cm.write()
        _ok(f"Model set to {parts[1]} (restart to apply)")
    elif cmd_name == "/autonomy" and len(parts) > 1:
        cm.set("POLARIS_AUTONOMY", parts[1].upper())
        cm.write()
        _ok(f"Autonomy set to {parts[1].upper()} (restart to apply)")
    elif cmd_name == "/doctor":
        cmd_doctor()
    elif cmd_name == "/sessions":
        cmd_sessions_list()
    elif cmd_name == "/exit" or cmd_name == "/quit":
        pass  # handled in main loop
    else:
        print(f"{_c('y', f'Unknown command: {cmd_name}')}")
        print(f"{_c('dim', 'Type /help for available commands.')}")


def _show_repl_help():
    print(f"""
{_c('bold', 'REPL Commands:')}
  {_c('c', 'exit, quit, q')}    Exit (session saved)
  {_c('c', 'help')}              This help
  {_c('c', 'version')}           Show version
  {_c('c', 'clear')}             Clear screen
  {_c('c', 'config')}            Show current configuration

{_c('bold', 'Slash Commands:')}
  {_c('c', '/help')}             This help
  {_c('c', '/config')}           Show configuration
  {_c('c', '/model <name>')}     Change model
  {_c('c', '/autonomy <L0-L4>')} Change autonomy level
  {_c('c', '/doctor')}           Run diagnostics
  {_c('c', '/sessions')}         List sessions
""")

# ── Main ───────────────────────────────────────────────────────────────────

def main():
    # ── Pre-scan argv to route single-shot vs subcommand ──────────────
    # The prompt positional conflicts with subcommands in argparse.
    # We detect: if argv[1] is not a known subcommand and not a flag, it's a prompt.

    KNOWN_SUBCOMMANDS = {
        "init", "setup", "login", "logout", "doctor", "update", "upgrade",
        "config", "profiles", "sessions", "mcp", "exec",
    }

    prompt_arg = None
    remaining_argv = sys.argv[1:]

    # Check if first positional is a prompt (not a subcommand, not a flag)
    if remaining_argv and not remaining_argv[0].startswith("-"):
        first = remaining_argv[0]
        if first not in KNOWN_SUBCOMMANDS:
            prompt_arg = first
            remaining_argv = remaining_argv[1:]

    # Parse remaining args as normal
    parser = argparse.ArgumentParser(
        prog="polaris",
        description=f"✦ Polaris Agent — Navigate Complexity with AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=CLI_EPILOG,
    )

    # Subcommands
    sub = parser.add_subparsers(dest="subcommand", help="Command")

    sub.add_parser("init", help="Interactive setup wizard (alias: setup)")
    sub.add_parser("setup", help="Alias for init")
    sub.add_parser("login", help="Save API keys")
    sub.add_parser("logout", help="Remove stored credentials")
    sub.add_parser("doctor", help="Environment diagnostics")
    sub.add_parser("update", help="Self-update via pip")
    sub.add_parser("upgrade", help="Alias for update")

    # config
    cp = sub.add_parser("config", help="Configuration management")
    cs = cp.add_subparsers(dest="config_action")
    cs.add_parser("show", help="Show all config")
    cg = cs.add_parser("get", help="Get a value"); cg.add_argument("key")
    cset = cs.add_parser("set", help="Set a value"); cset.add_argument("key"); cset.add_argument("value"); cset.add_argument("--global", "-g", dest="layer", action="store_const", const="global", help="Write to global config"); cset.add_argument("--project", "-p", dest="layer", action="store_const", const="project", help="Write to project config (.polaris/config.json)"); cset.add_argument("--local", "-l", dest="layer", action="store_const", const="local", help="Write to local config (.polaris/config.local.json)")
    cu = cs.add_parser("unset", help="Unset a key"); cu.add_argument("key"); cu.add_argument("--global", "-g", dest="layer", action="store_const", const="global", help="Remove from global"); cu.add_argument("--project", "-p", dest="layer", action="store_const", const="project", help="Remove from project"); cu.add_argument("--local", "-l", dest="layer", action="store_const", const="local", help="Remove from local")
    cs.add_parser("reset", help="Reset to defaults")
    cs.add_parser("path", help="Show config file path")
    cpath = cs.add_parser("paths", help="Show all config file paths")
    ce = cs.add_parser("export", help="Export as named profile"); ce.add_argument("--profile", "-p", required=True)

    # profiles
    pr = sub.add_parser("profiles", help="Named config profiles")
    ps = pr.add_subparsers(dest="profiles_action")
    ps.add_parser("list", help="List profiles")
    pu = ps.add_parser("use", help="Switch profile"); pu.add_argument("name")

    # sessions
    sp = sub.add_parser("sessions", help="Session management")
    ss = sp.add_subparsers(dest="sessions_action")
    ss.add_parser("list", help="List sessions")
    sr = ss.add_parser("resume", help="Resume session"); sr.add_argument("session_id")

    # mcp
    mp = sub.add_parser("mcp", help="MCP server management")
    ms = mp.add_subparsers(dest="mcp_action")
    ms.add_parser("list", help="List MCP servers")
    ma = ms.add_parser("add", help="Add MCP server (quote the command)"); ma.add_argument("name"); ma.add_argument("cmd", help='Full command, e.g. "npx -y @modelcontextprotocol/server-filesystem ."')
    mr = ms.add_parser("remove", help="Remove MCP server"); mr.add_argument("name")

    # exec
    ep = sub.add_parser("exec", help="Execute a task file"); ep.add_argument("file")

    # Flags
    parser.add_argument("--model", "-m", type=str, help="Override model for this session")
    parser.add_argument("--approval-mode", type=str, choices=["L0", "L1", "L2", "L3", "L4"], help="Override autonomy level")
    parser.add_argument("--pipe", "-p", action="store_true", help="Explicit pipe mode (read from stdin)")
    parser.add_argument("--output-format", type=str, choices=["text", "json"], default="text", help="Output format (default: text)")
    parser.add_argument("--resume", type=str, help="Resume a session by ID (or 'last' for most recent)")
    parser.add_argument("--no-logo", action="store_true", help="Skip splash screen in interactive mode")
    parser.add_argument("--logo", action="store_true", help="Display logo & exit")
    parser.add_argument("--style", "-s", choices=["default", "minimal", "box"], default="default")
    parser.add_argument("--version", "-v", action="store_true", help="Show version & exit")
    parser.add_argument("prompt", nargs="?", default=None, help=argparse.SUPPRESS)

    args = parser.parse_args(remaining_argv)

    # ── Logo / Version (fast paths) ───────────────────────────────────
    if args.logo:
        PolarisLogo(style=args.style, animate=True).display()
        return
    if args.version:
        display_version_info()
        return

    # ── Subcommand dispatch ───────────────────────────────────────────
    cmd = args.subcommand

    if cmd in ("init", "setup"):
        cm_int = _get_cm()
        _init_wiz.run_wizard(cm_int)
        return
    if cmd == "login":
        cmd_login(); return
    if cmd == "logout":
        cmd_logout(); return
    if cmd == "doctor":
        cmd_doctor(); return
    if cmd in ("update", "upgrade"):
        cmd_update(); return

    if cmd == "config":
        act = getattr(args, "config_action", None)
        if act == "get":      _print_val(_get_cm().get(args.key))
        elif act == "set":
            cm_c = _get_cm(); layer = getattr(args, "layer", None) or "global"
            cm_c.set(args.key, args.value, layer=layer); cm_c.write()
            _ok(f"{args.key} = {args.value}  [{layer}]")
        elif act == "unset":
            cm_c = _get_cm(); layer = getattr(args, "layer", None) or "global"
            cm_c.unset(args.key, layer=layer); cm_c.write()
            _ok(f"{args.key} unset [{layer}]")
        elif act == "reset":  _get_cm().reset(); _ok("Config reset to defaults")
        elif act == "path":   print(str(_get_cm().config_path))
        elif act == "paths":
            for label, p in _get_cm().all_paths():
                marker = " ✓" if p and p.exists() else ""
                print(f"{label}: {p}{marker}")
        elif act == "export": cmd_config_export(args.profile)
        else:                 cmd_config_show()
        return
    if cmd == "profiles":
        act = getattr(args, "profiles_action", None) or "list"
        if act == "list": cmd_profiles_list()
        elif act == "use": cmd_profiles_use(args.name)
        return
    if cmd == "sessions":
        act = getattr(args, "sessions_action", None) or "list"
        if act == "list": cmd_sessions_list()
        elif act == "resume": cmd_sessions_resume(args.session_id)
        return
    if cmd == "mcp":
        act = getattr(args, "mcp_action", None) or "list"
        if act == "list": cmd_mcp_list()
        elif act == "add": cmd_mcp_add(args.name, args.cmd)
        elif act == "remove": cmd_mcp_remove(args.name)
        return
    if cmd == "exec":
        content = Path(args.file).read_text()
        sys.exit(run_single_shot(content, args.model, args.approval_mode))

    # ── Determine mode: pipe, single-shot, or interactive ─────────────
    effective_prompt = prompt_arg or args.prompt

    # Explicit pipe mode
    if args.pipe:
        pipe_data = sys.stdin.read().strip()
        if not pipe_data:
            print(f"{_c('r', 'No data on stdin.')}", file=sys.stderr)
            sys.exit(1)
        sys.exit(run_single_shot(pipe_data, args.model, args.approval_mode,
                                 output_format=args.output_format))

    # Implicit pipe / stdin mode
    if not _TTY or not sys.stdin.isatty():
        pipe_data = sys.stdin.read().strip()
        if pipe_data:
            sys.exit(run_single_shot(pipe_data, args.model, args.approval_mode,
                                     output_format=args.output_format))

    # Handle --resume
    resume_id = None
    if args.resume:
        if args.resume == "last":
            # Find most recent session
            meta_file = POLARIS_HOME / "sessions_index.json"
            if meta_file.exists():
                index = json.loads(meta_file.read_text())
                if index:
                    resume_id = sorted(index.keys(), key=lambda k: index[k].get("updated_at", ""), reverse=True)[0]
                    print(f"{_c('dim', f'Resuming: {resume_id}')}")
        else:
            resume_id = args.resume

    # Single-shot mode
    if effective_prompt:
        sys.exit(run_single_shot(effective_prompt, args.model, args.approval_mode,
                                 output_format=args.output_format))

    # Interactive mode
    run_interactive(args.model, args.approval_mode, resume_session_id=resume_id,
                    show_logo=not args.no_logo)


def _print_val(val):
    if val is not None:
        print(val)


if __name__ == "__main__":
    main()
