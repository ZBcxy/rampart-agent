# ✦ Polaris Agent — npm Package

This is the **npm distribution wrapper** for [Polaris Agent](https://github.com/ZBcxy/polaris-agent).  
It bootstraps the Python package and provides the `polaris` CLI command.

The real package lives at: [`polaris-agent` on PyPI](https://pypi.org/project/polaris-agent/)

## Install

```bash
npm install -g polaris-agent
```

This will:
1. Check for Python 3.11+
2. Run `pip install polaris-agent`
3. Link the `polaris` command globally

## Uninstall

```bash
npm uninstall -g polaris-agent
```

This will:
1. Run `pip uninstall polaris-agent`
2. Ask whether to keep your config/data (`~/.polaris/`)
3. Clean up shell PATH entries

## Usage

```bash
polaris init      # First-time setup
polaris           # Start interactive agent
polaris "prompt"  # Single-shot mode
echo "..." | polaris  # Pipe mode
```

## Alternative Install Methods

```bash
# PyPI (direct)
pip install polaris-agent

# pipx (isolated)
pipx install polaris-agent

# Docker
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... ghcr.io/zbcxy/polaris-agent:latest

# curl one-liner
curl -sSL https://raw.githubusercontent.com/ZBcxy/polaris-agent/main/install.py | python3
```

## License

Apache 2.0 — see [main repo](https://github.com/ZBcxy/polaris-agent)
