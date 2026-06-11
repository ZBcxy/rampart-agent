#!/usr/bin/env python3
"""Polaris Agent — One-command installer + launcher.

Detects platform, checks deps, creates venv, installs packages,
and launches interactive CLI — all in one go.

Usage:
    curl -sSL https://raw.githubusercontent.com/ZBcxy/polaris-agent/main/install.py | python3
    python install.py              # install + launch CLI
    python install.py --no-launch  # install only
    python install.py --upgrade    # upgrade + launch
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

APP = "polaris"
HOME = Path.home() / f".{APP}"
VENV = HOME / "venv"
MIN_PY = (3, 11)

REQS = [
    "fastapi>=0.100.0", "uvicorn>=0.23.0", "pydantic>=2.0.0",
    "python-multipart>=0.0.6", "openai>=1.0.0", "litellm>=1.0.0",
    "redis>=5.0.0", "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4", "python-dotenv>=1.0.0",
    "requests>=2.31.0", "aiohttp>=3.8.0", "orjson>=3.9.0",
    "pydantic-settings>=2.0.0", "httpx>=0.24.0",
]

def c(code, text):
    colors = {"g": 32, "y": 33, "b": 34, "c": 36, "r": 31}
    return f"\033[{colors.get(code,0)}m{text}\033[0m" if sys.stdout.isatty() else text

def ok(m):    print(f"  {c('g','✓')} {m}")
def wrn(m):   print(f"  {c('y','!')} {m}")
def fl(m):    print(f"  {c('r','✗')} {m}")
def step(m):  print(f"\n{c('b','▸')} {m}")
def run(cmd):
    return subprocess.run(cmd, shell=True, check=False, capture_output=True, text=True)

# ── Checkers ────────────────────────────────────────────────────────────

def check_python():
    step("Python")
    v = sys.version_info[:2]
    if v >= MIN_PY:
        ok(f"Python {sys.version.split()[0]}")
        return True
    fl(f"Need Python {'.'.join(map(str,MIN_PY))}+, got {sys.version.split()[0]}")
    return False

def check_pip():
    try:
        import pip; ok(f"pip {pip.__version__}"); return True
    except ImportError:
        wrn("Installing pip...")
        return run(f"{sys.executable} -m ensurepip --upgrade").returncode == 0

def check_platform():
    step("Platform")
    p = sys.platform
    m = {"linux": "Linux", "darwin": "macOS", "win32": "Windows"}.get(p, p)
    ok(m)
    return p

def pip():
    return str(VENV / ("Scripts" if sys.platform == "win32" else "bin") / "pip")

def py():
    return str(VENV / ("Scripts" if sys.platform == "win32" else "bin") / "python")

# ── Installer ───────────────────────────────────────────────────────────

def create_dirs():
    step("Dirs")
    for d in [HOME, HOME/"modules", HOME/"logs", HOME/"data", HOME/"memory"]:
        d.mkdir(parents=True, exist_ok=True)
    ok(str(HOME))

def setup_venv(force=False):
    step("Virtualenv")
    if VENV.exists() and not force:
        ok(f"Exists: {VENV}"); return True
    if VENV.exists():
        shutil.rmtree(VENV)
    r = run(f"{sys.executable} -m venv {VENV}")
    if r.returncode != 0:
        fl(r.stderr); return False
    ok("Created")
    return True

def install_deps():
    step("Dependencies")
    run(f"{pip()} install --upgrade pip -q")
    failed = []
    for req in REQS:
        name = req.split(">=")[0].split("[")[0]
        r = run(f"{pip()} install {req} -q")
        if r.returncode != 0:
            fl(name); failed.append(name)
    if failed:
        wrn(f"{len(failed)} failed: {', '.join(failed)}")
    else:
        ok(f"{len(REQS)} packages")
    return True

def install_polaris():
    step("Polaris Agent")
    src = Path(__file__).parent.resolve()

    if (src / "core").exists():
        r = run(f"{pip()} install -e {src} -q")
    else:
        r = run(f"{pip()} install polaris-agent -q")

    if r.returncode != 0:
        wrn(f"Install note: {r.stderr[:200] if r.stderr else ''}")

    # CLI entry
    bindir = Path.home() / ".local" / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    cli = bindir / APP

    if sys.platform == "win32":
        content = f'@echo off\r\nset POLARIS_HOME={HOME}\r\n"{py()}" -m cli.polaris_cli %*\r\n'
        cli = bindir / f"{APP}.bat"
    else:
        content = f'#!/bin/bash\nexport POLARIS_HOME="{HOME}"\nexec {py()} -m cli.polaris_cli "$@"\n'

    cli.write_text(content)
    cli.chmod(0o755)
    ok(f"CLI: {cli}")

    # PATH
    if str(bindir) not in os.environ.get("PATH", ""):
        rc = Path.home() / (".zshrc" if "zsh" in os.environ.get("SHELL", "") else ".bashrc")
        marker = "# Polaris"
        try:
            if marker not in (rc.read_text() if rc.exists() else ""):
                with open(rc, "a") as f:
                    f.write(f"\n{marker}\nexport PATH=\"{bindir}:$PATH\"\n")
                ok(f"Added PATH to {rc.name}")
        except Exception:
            pass
    return True

def setup_env():
    step("Config")
    env = HOME / ".env"
    if env.exists():
        ok(".env exists"); return
    src = Path(__file__).parent / ".env.example"
    if src.exists():
        shutil.copy(src, env)
    else:
        env.write_text("# Polaris Agent\nOPENAI_API_KEY=\nLLM_MODEL=gpt-4o\n")
    ok(f"Created: {env}")

def launch():
    step("Launching...\n")
    cli = Path(__file__).parent / "cli" / "polaris_cli.py"
    if cli.exists():
        os.execve(py(), [py(), str(cli)], os.environ)
    else:
        os.execve(py(), [py(), "-m", "cli.polaris_cli"], os.environ)

# ── Main ────────────────────────────────────────────────────────────────

def main():
    import argparse
    p = argparse.ArgumentParser(description="Polaris Agent — One-command setup")
    p.add_argument("--no-launch", action="store_true")
    p.add_argument("--upgrade", action="store_true")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    print(f"\n{c('c','╭──────────────────────────────────╮')}")
    print(f"{c('c','│')}   {c('y','★')} {c('g','Polaris Agent')} — One-Command    {c('c','│')}")
    print(f"{c('c','╰──────────────────────────────────╯')}\n")

    if not check_python(): sys.exit(1)
    if not check_pip(): sys.exit(1)
    check_platform()
    create_dirs()
    if not setup_venv(force=args.upgrade or args.force): sys.exit(1)
    install_deps()
    install_polaris()
    setup_env()

    print(f"\n{c('g','╭──────────────────────────────────╮')}")
    print(f"{c('g','│')}   ✓ Ready! Run '{APP}' to start  {c('g','│')}")
    print(f"{c('g','╰──────────────────────────────────╯')}\n")

    if not args.no_launch:
        launch()

if __name__ == "__main__":
    main()
