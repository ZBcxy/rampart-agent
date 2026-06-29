# ✦ Rampart Agent — npm Package

This is the **npm distribution wrapper** for [Rampart Agent](https://github.com/ZBcxy/rampart-agent).  
It bootstraps the Python package and provides the `rampart` CLI command.

The real package lives at: [`rampart-agent` on PyPI](https://pypi.org/project/rampart-agent/)

## Install

```bash
npm install -g rampart-agent
```

This will:
1. Check for Python 3.11+
2. Run `pip install rampart-agent`
3. Link the `rampart` command globally

## Uninstall

```bash
npm uninstall -g rampart-agent
```

This will:
1. Run `pip uninstall rampart-agent`
2. Ask whether to keep your config/data (`~/.rampart/`)
3. Clean up shell PATH entries

## Usage

```bash
rampart init      # First-time setup
rampart           # Start interactive agent
rampart "prompt"  # Single-shot mode
echo "..." | rampart  # Pipe mode
```

## Alternative Install Methods

```bash
# PyPI (direct)
pip install rampart-agent

# pipx (isolated)
pipx install rampart-agent

# Docker
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... ghcr.io/zbcxy/rampart-agent:latest

# curl one-liner
curl -sSL https://raw.githubusercontent.com/ZBcxy/rampart-agent/main/install.py | python3
```

## License

Apache 2.0 — see [main repo](https://github.com/ZBcxy/rampart-agent)
