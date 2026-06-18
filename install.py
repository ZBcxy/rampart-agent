#!/usr/bin/env python3
"""✦ Polaris Agent — One-command lifecycle manager.

Navigate Complexity with AI.

Usage:
    curl -sSL https://raw.githubusercontent.com/ZBcxy/polaris-agent/main/install.py | python3
    python install.py                  # install + launch CLI
    python install.py --no-launch      # install only
    python install.py --upgrade        # upgrade in-place
    python install.py --uninstall      # full uninstall
    python install.py --uninstall --keep-data   # uninstall, keep config & data
    python install.py --verify         # verify installation integrity
    python install.py --doctor         # diagnose environment issues
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────────

APP = "polaris"
HOME = Path.home() / f".{APP}"
VENV = HOME / "venv"
BIN_DIR = Path.home() / ".local" / "bin"
MIN_PY = (3, 11)
GITHUB_REPO = "ZBcxy/polaris-agent"
PYPI_PACKAGE = "polaris-agent"

REQS = [
    "fastapi>=0.100.0", "uvicorn>=0.23.0", "pydantic>=2.0.0",
    "python-multipart>=0.0.6", "openai>=1.0.0", "litellm>=1.0.0",
    "redis>=5.0.0", "python-jose[cryptography]>=3.3.0",
    "python-dotenv>=1.0.0", "requests>=2.31.0", "aiohttp>=3.8.0",
    "orjson>=3.9.0", "pydantic-settings>=2.0.0", "httpx>=0.24.0",
]

# ── Terminal helpers ──────────────────────────────────────────────────────

_TTY = sys.stdout.isatty()
_FORCE_COLOR = os.environ.get("FORCE_COLOR", False) or os.environ.get("CLICOLOR_FORCE", False)
_COLOR = _TTY or _FORCE_COLOR


def _c(code: str, text: str) -> str:
    colors = {"g": 32, "y": 33, "b": 34, "c": 36, "r": 31, "w": 37, "dim": 2, "bold": 1}
    return f"\033[{colors.get(code, 0)}m{text}\033[0m" if _COLOR else text


def _ok(m: str) -> None:
    print(f"  {_c('g', '✓')} {m}")


def _wrn(m: str) -> None:
    print(f"  {_c('y', '!')} {m}")


def _err(m: str) -> None:
    print(f"  {_c('r', '✗')} {m}")


def _step(m: str) -> None:
    print(f"\n{_c('b', '▸')} {m}")


def _info(m: str) -> None:
    print(f"  {_c('c', 'ℹ')} {m}")


def _run(cmd: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)


def _venv_python() -> str:
    return str(VENV / ("Scripts" if sys.platform == "win32" else "bin") / "python")


def _venv_pip() -> str:
    return str(VENV / ("Scripts" if sys.platform == "win32" else "bin") / "pip")


# ── Banner ─────────────────────────────────────────────────────────────────

def _banner(action: str = "Install") -> None:
    bar = "─" * 42
    print(f"\n{_c('c', '╭' + bar + '╮')}")
    print(f"{_c('c', '│')}  {_c('y', '✦')} {_c('bold', 'Polaris Agent')} — {_c('w', action):<27} {_c('c', '│')}")
    print(f"{_c('c', '╰' + bar + '╯')}\n")


def _done_box(message: str) -> None:
    bar = "─" * 50
    print(f"\n{_c('g', '╭' + bar + '╮')}")
    print(f"{_c('g', '│')}   {_c('bold', '✓ ' + message):<46} {_c('g', '│')}")
    print(f"{_c('g', '╰' + bar + '╯')}\n")


# ── Checkers ───────────────────────────────────────────────────────────────

def check_python() -> bool:
    _step("Python")
    v = sys.version_info[:2]
    if v >= MIN_PY:
        _ok(f"Python {sys.version.split()[0]}")
        return True
    _err(f"Need Python {'.'.join(map(str, MIN_PY))}+, got {sys.version.split()[0]}")
    return False


def check_pip() -> bool:
    try:
        import pip
        _ok(f"pip {pip.__version__}")
        return True
    except ImportError:
        _wrn("pip not found. Installing...")
        r = _run(f"{sys.executable} -m ensurepip --upgrade")
        if r.returncode != 0:
            _err(f"Failed to install pip: {r.stderr}")
            return False
        _ok("pip installed")
        return True


def check_platform() -> str:
    _step("Platform")
    p = sys.platform
    m = {"linux": "Linux", "darwin": "macOS", "win32": "Windows"}.get(p, p)
    _ok(m)
    return p


# ── Install ────────────────────────────────────────────────────────────────

def create_dirs() -> None:
    _step("Directories")
    for d in [HOME, HOME / "modules", HOME / "logs", HOME / "data", HOME / "memory"]:
        d.mkdir(parents=True, exist_ok=True)
    _ok(str(HOME))


def setup_venv(force: bool = False) -> bool:
    _step("Virtual environment")
    if VENV.exists() and not force:
        _ok(f"Exists: {VENV}")
        return True
    if VENV.exists():
        shutil.rmtree(VENV)
        _info("Removed old venv")
    r = _run(f"{sys.executable} -m venv {VENV}")
    if r.returncode != 0:
        _err(f"Failed to create venv: {r.stderr}")
        return False
    _ok("Created")
    return True


def install_deps() -> bool:
    _step("Dependencies")
    _run(f"{_venv_pip()} install --upgrade pip -q")
    failed = []
    for req in REQS:
        name = req.split(">=")[0].split("[")[0]
        r = _run(f"{_venv_pip()} install {req} -q")
        if r.returncode != 0:
            _err(name)
            failed.append(name)
    if failed:
        _wrn(f"{len(failed)} packages had issues: {', '.join(failed)}")
    else:
        _ok(f"{len(REQS)} packages")
    return len(failed) == 0


def install_polaris(force: bool = False, editable: bool = False) -> bool:
    _step("Polaris Agent")
    src = Path(__file__).parent.resolve()

    # Determine install source
    if (src / "core").exists() and (src / "pyproject.toml").exists():
        # Installing from local clone
        flag = "-e" if editable else ""
        cmd = f"{_venv_pip()} install {flag} {src} -q"
        _info("Installing from local source")
        r = _run(cmd)
    else:
        # Remote install via PyPI
        cmd = f"{_venv_pip()} install {PYPI_PACKAGE} -q"
        _info("Installing from PyPI")
        r = _run(cmd)

    if r.returncode != 0:
        _err(f"Install failed: {r.stderr[:300] if r.stderr else 'unknown error'}")
        return False

    _ok(f"{PYPI_PACKAGE} installed")

    # Create CLI wrapper
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        cli = BIN_DIR / f"{APP}.bat"
        cli.write_text(
            f'@echo off\r\nset POLARIS_HOME={HOME}\r\n"{_venv_python()}" -m cli.polaris_cli %*\r\n'
        )
    else:
        cli = BIN_DIR / APP
        cli.write_text(
            f'#!/bin/bash\nexport POLARIS_HOME="{HOME}"\nexec {_venv_python()} -m cli.polaris_cli "$@"\n'
        )
        cli.chmod(0o755)
    _ok(f"CLI: {cli}")

    # Add to PATH
    _ensure_path()
    return True


def _ensure_path() -> None:
    """Add ~/.local/bin to user's shell profile if not already present."""
    bin_str = str(BIN_DIR)
    path_env = os.environ.get("PATH", "")
    if bin_str in path_env:
        return

    # Detect shell
    shell = os.environ.get("SHELL", "")
    if "zsh" in shell:
        rc_files = [Path.home() / ".zshrc", Path.home() / ".zshenv"]
    elif "fish" in shell:
        rc_files = [Path.home() / ".config" / "fish" / "config.fish"]
    else:
        rc_files = [Path.home() / ".bashrc", Path.home() / ".profile", Path.home() / ".bash_profile"]

    marker = "# Polaris Agent PATH"
    for rc in rc_files:
        if not rc.exists():
            continue
        try:
            content = rc.read_text()
            if marker in content:
                return
            with open(rc, "a") as f:
                f.write(f"\n{marker}\nexport PATH=\"{bin_str}:$PATH\"\n")
            _ok(f"Added PATH to {rc.name}")
            return
        except Exception:
            continue

    _wrn(f"Could not add PATH automatically. Add '{bin_str}' to your PATH manually.")


def setup_env() -> None:
    _step("Config")
    env_file = HOME / ".env"
    if env_file.exists():
        _ok(".env exists")
        return
    src = Path(__file__).parent / ".env.example"
    if src.exists():
        shutil.copy(src, env_file)
    else:
        env_file.write_text(
            "# ✦ Polaris Agent — Navigate Complexity with AI\n"
            "# Configure your LLM provider below.\n\n"
            "OPENAI_API_KEY=\nLLM_MODEL=gpt-4o\n"
        )
    _ok(f"Created: {env_file}")


# ── Uninstall ──────────────────────────────────────────────────────────────

def do_uninstall(keep_data: bool = False) -> None:
    """Remove Polaris Agent from the system."""
    banner_shown = False

    # Remove venv
    if VENV.exists():
        if not banner_shown:
            _banner("Uninstall")
            banner_shown = True
        _step("Virtual environment")
        shutil.rmtree(VENV)
        _ok(f"Removed {VENV}")

    # Remove CLI wrapper
    for ext in ("", ".bat"):
        cli = BIN_DIR / f"{APP}{ext}"
        if cli.exists():
            if not banner_shown:
                _banner("Uninstall")
                banner_shown = True
            cli.unlink()
            _ok(f"Removed {cli}")

    # Remove config & data
    if not keep_data:
        if HOME.exists():
            if not banner_shown:
                _banner("Uninstall")
                banner_shown = True
            _step("Data directory")
            shutil.rmtree(HOME)
            _ok(f"Removed {HOME}")
    else:
        if not banner_shown:
            _banner("Uninstall")
            banner_shown = True
        _info(f"Kept data at {HOME}")

    # Remove PATH entries (best-effort)
    _step("Shell profiles")
    cleaned = _remove_path_entries()
    if cleaned:
        for f in cleaned:
            _ok(f"Cleaned PATH from {f}")
    else:
        _info("No PATH entries found (or couldn't clean)")

    if not banner_shown:
        _info("Nothing to uninstall. Polaris Agent is not installed.")
        return

    _done_box("Polaris Agent has been uninstalled.")


def _remove_path_entries() -> list:
    """Remove Polaris PATH lines from shell rc files. Returns list of cleaned files."""
    cleaned = []
    bin_str = str(BIN_DIR)
    rc_files = [
        Path.home() / ".zshrc",
        Path.home() / ".zshenv",
        Path.home() / ".bashrc",
        Path.home() / ".profile",
        Path.home() / ".bash_profile",
    ]

    for rc in rc_files:
        if not rc.exists():
            continue
        try:
            lines = rc.read_text().splitlines()
            new_lines = []
            skip_next = False
            for line in lines:
                if "# Polaris Agent PATH" in line:
                    skip_next = True
                    continue
                if skip_next and bin_str in line:
                    skip_next = False
                    continue
                skip_next = False
                if bin_str in line and "export PATH" in line:
                    continue
                new_lines.append(line)
            if len(new_lines) != len(lines):
                rc.write_text("\n".join(new_lines) + "\n")
                cleaned.append(rc.name)
        except Exception:
            continue

    return cleaned


# ── Verify ─────────────────────────────────────────────────────────────────

def do_verify() -> bool:
    """Verify that Polaris Agent is correctly installed."""
    _banner("Verify")
    all_ok = True

    checks = [
        ("Virtual environment", VENV.exists()),
        ("Python binary", Path(_venv_python()).exists()),
        ("pip binary", Path(_venv_pip()).exists()),
        ("CLI wrapper", (BIN_DIR / APP).exists() or (BIN_DIR / f"{APP}.bat").exists()),
        ("Config directory", HOME.exists()),
        ("Env file", (HOME / ".env").exists()),
    ]

    for name, ok in checks:
        if ok:
            _ok(name)
        else:
            _err(name)
            all_ok = False

    # Check that the package is importable
    _step("Package import")
    r = _run(f"{_venv_python()} -c 'import core; print(core.__file__)'")
    if r.returncode == 0:
        _ok(f"Importable: {r.stdout.strip()}")
    else:
        _err(f"Cannot import 'core': {r.stderr.strip()[:200]}")
        all_ok = False

    # Check CLI version
    if (BIN_DIR / APP).exists():
        _step("CLI version")
        r = _run(f"{BIN_DIR / APP} --version 2>&1")
        if r.returncode == 0:
            _ok(f"CLI: {r.stdout.strip()}")
        else:
            _wrn(f"CLI output: {r.stdout.strip() or r.stderr.strip()[:100]}")

    if all_ok:
        _done_box("All checks passed.")
    else:
        print(f"\n{_c('r', 'Some checks failed. Run --doctor for diagnostics.')}\n")

    return all_ok


# ── Doctor (environment diagnostics) ───────────────────────────────────────

def do_doctor() -> None:
    """Run environment diagnostics to help users debug issues."""
    _banner("Doctor")

    # Python
    _step("Python environment")
    _info(f"Python: {sys.version}")
    _info(f"Executable: {sys.executable}")
    _info(f"Platform: {sys.platform} ({platform_release()})")

    # Virtual environment
    _step(f"Polaris home ({HOME})")
    if HOME.exists():
        _info(f"Exists, contents: {', '.join(p.name for p in sorted(HOME.iterdir()) if p.is_dir())}")
    else:
        _info("Not found — run install first")

    if VENV.exists():
        r = _run(f"{_venv_pip()} list --format=columns 2>&1 | head -20")
        _info(f"Top packages:\n{r.stdout.strip()[:600]}")
    else:
        _info("Venv not found")

    # Disk
    _step("Disk usage")
    try:
        usage = shutil.disk_usage(HOME)
        gb_free = usage.free / (1024 ** 3)
        _info(f"Free: {gb_free:.1f} GB on {HOME}")
        if gb_free < 1:
            _wrn("Low disk space — may cause issues")
    except Exception:
        pass

    # Ollama
    _step("Local LLM providers")
    ollama_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    _info(f"Checking Ollama at {ollama_url}...")
    try:
        import urllib.request
        req = urllib.request.Request(f"{ollama_url}/api/tags", method="GET")
        resp = urllib.request.urlopen(req, timeout=5)
        import json
        data = json.loads(resp.read())
        models = [m.get("name", "?") for m in data.get("models", [])]
        if models:
            _ok(f"Ollama running — models: {', '.join(models[:5])}")
        else:
            _info("Ollama running but no models pulled")
    except Exception:
        _info("Ollama not reachable (this is fine if you use cloud LLMs)")

    # API keys
    _step("API keys")
    keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "LOCAL_LLM_PROVIDER"]
    for k in keys:
        if os.environ.get(k):
            masked = os.environ[k][:4] + "****" if len(os.environ[k]) > 4 else "****"
            _ok(f"{k}={masked}")
        else:
            _info(f"{k} not set")

    # PATH
    _step("PATH check")
    bin_str = str(BIN_DIR)
    if bin_str in os.environ.get("PATH", ""):
        _ok(f"{bin_str} is in PATH")
    else:
        _wrn(f"{bin_str} not in PATH. Add it manually or restart your shell.")
        _info(f"Run: export PATH=\"{bin_str}:$PATH\"")

    print(f"\n{_c('c', 'Diagnostics complete.')}\n")


def platform_release() -> str:
    try:
        import platform
        return platform.release() or "unknown"
    except Exception:
        return "unknown"


# ── Upgrade ────────────────────────────────────────────────────────────────

def do_upgrade() -> bool:
    """Upgrade Polaris Agent in-place."""
    _banner("Upgrade")
    _step("Upgrading Polaris Agent")

    r = _run(f"{_venv_pip()} install --upgrade {PYPI_PACKAGE} -q")
    if r.returncode == 0:
        # Show new version
        r2 = _run(f"{_venv_pip()} show {PYPI_PACKAGE}")
        for line in r2.stdout.splitlines():
            if line.startswith("Version:"):
                _ok(f"Upgraded to {line.split(':')[1].strip()}")
                break
        _done_box("Polaris Agent is up to date.")
        return True
    else:
        _wrn(f"Upgrade had issues: {r.stderr[:300] if r.stderr else ''}")
        _info("Try reinstalling: python install.py --force")
        return False


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="✦ Polaris Agent — One-command lifecycle manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python install.py                  Install + launch interactive CLI
  python install.py --no-launch      Install only
  python install.py --upgrade        Upgrade to latest version
  python install.py --uninstall      Full uninstall
  python install.py --uninstall --keep-data   Uninstall, keep config
  python install.py --verify         Verify installation
  python install.py --doctor         Environment diagnostics
  python install.py --force          Reinstall from scratch
        """,
    )

    # Actions
    parser.add_argument("--no-launch", action="store_true", help="Install only, don't launch CLI")
    parser.add_argument("--upgrade", action="store_true", help="Upgrade to latest version")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall Polaris Agent")
    parser.add_argument("--keep-data", action="store_true", help="Keep config & data during uninstall")
    parser.add_argument("--verify", action="store_true", help="Verify installation integrity")
    parser.add_argument("--doctor", action="store_true", help="Run environment diagnostics")
    parser.add_argument("--force", action="store_true", help="Force reinstall / recreate venv")

    args = parser.parse_args()

    # ── Uninstall path ──────────────────────────────────────────────────
    if args.uninstall:
        do_uninstall(keep_data=args.keep_data)
        return

    # ── Verify path ─────────────────────────────────────────────────────
    if args.verify:
        do_verify()
        return

    # ── Doctor path ─────────────────────────────────────────────────────
    if args.doctor:
        do_doctor()
        return

    # ── Upgrade path ────────────────────────────────────────────────────
    if args.upgrade:
        if not VENV.exists():
            _err("Polaris Agent is not installed. Run without --upgrade first.")
            sys.exit(1)
        do_upgrade()
        # Launch after upgrade
        if not args.no_launch:
            _launch_cli()
        return

    # ── Install path ────────────────────────────────────────────────────
    _banner("Install")

    if not check_python():
        sys.exit(1)
    if not check_pip():
        sys.exit(1)
    check_platform()
    create_dirs()

    if not setup_venv(force=args.force):
        sys.exit(1)

    install_deps()

    if not install_polaris(force=args.force):
        sys.exit(1)

    setup_env()

    _done_box(f"✦ Ready! Run '{APP}' to start.")

    if not args.no_launch:
        _launch_cli()


def _launch_cli() -> None:
    """Launch the Polaris CLI by replacing the current process."""
    _step("Launching...\n")
    python = _venv_python()
    cli_path = Path(__file__).parent / "cli" / "polaris_cli.py"
    if cli_path.exists():
        os.execve(python, [python, str(cli_path)], os.environ)
    else:
        os.execve(python, [python, "-m", "cli.polaris_cli"], os.environ)


if __name__ == "__main__":
    main()
