# CHANGELOG

## v1.1.0 (2026-06-18) — Complete Lifecycle

### Brand & Identity
- ✦ New brand mark: four-pointed star with Big Dipper narrative
- Terminal logo: 3 styles (default 北斗七星叙事风 / minimal 极简符号风 / box 星空主题风)
- SVG logo for GitHub, PyPI, documentation (`assets/logo.svg`)
- Tagline: "Navigate Complexity with AI"
- Unified naming across all files (README, pyproject, Docker, CLI, gateway, A2A, env)

### Lifecycle CLI (like Claude Code / OpenClaw / Codex)
- **Single-shot mode:** `polaris "prompt"` — non-interactive execution
- **Pipe/stdin mode:** `echo "..." | polaris` — works in scripts
- **Interactive REPL:** readline history, session auto-save, slash commands
- **polaris init** — interactive 4-step setup wizard (Provider → Model → Autonomy → Save)
- **polaris login / logout** — API key management
- **polaris doctor** — full environment diagnostics (Python, Ollama, API keys, PATH, disk)
- **polaris update** — self-update via pip
- **polaris config** — CRUD operations (`get/set/unset/reset/path`)
- **polaris profiles** — named config profiles (`list/use`)
- **polaris sessions** — session history (`list/resume`)
- **polaris mcp** — MCP server management (`add/list/remove`)
- **polaris exec <file>** — execute task files
- **polaris --model / --approval-mode** — runtime overrides
- **Slash commands:** `/help`, `/config`, `/model`, `/autonomy`, `/doctor`, `/sessions`

### Configuration System
- New `core/config_manager.py`: JSON-based config manager (zero external deps)
- Config priority: CLI args > env vars > `~/.polaris/config.json` > `.env` > defaults
- Ollama auto-discovery on first launch
- Named config profiles (`~/.polaris/profiles/`)

### Install Lifecycle
- Rewrite `install.py`: install, upgrade, uninstall (`--keep-data`), verify, doctor
- Colored terminal output, structured stages
- Auto-PATH configuration

### Documentation
- README completely rewritten with full lifecycle documentation
- Command reference, REPL guide, protocol examples, SDK usage
- Feature comparison table vs LangGraph, CrewAI, AutoGPT, Claude Code

### Misc
- A2A protocol types: brand defaults + type fixes
- Gateway API: brand update + version bump
- Dockerfile: updated labels
- Removed pyyaml dependency (switched to stdlib json)

---

## v1.1.0-alpha (2026-06-11) — Polaris Agent

### Breaking
- Renamed: BeiJiXing Agent → Polaris Agent
- CLI: `beijixing` → `polaris`, config: `~/.beijixing` → `~/.polaris`

### New
- LLM-powered OODA Agent with PromptManager (zero hardcoded prompts)
- 26 executable tools across 5 categories with ToolRegistry
- MCP Server + Client (v2025-11-25): tools, resources, prompts, tasks, icons
- A2A Server + Client (v1.0): Agent Cards, task lifecycle, SSE streaming
- Multi-agent blackboard + role-based coordinator
- Embedding semantic memory (OpenAI, SentenceTransformers, hybrid search)
- Retry executor with circuit breaker + dead letter queue
- 5-rule alignment guard, L0-L4 policy engine, tool authorization, HITL
- Observability: JSON logging, span tracing, metrics
- Eval framework: assertion + LLM-as-judge
- LLM response cache: memory + Redis
- RAG pipeline: ingest → chunk → embed → retrieve
- Python SDK: sync + async client
- Docker: multi-stage, multi-arch (amd64/arm64), docker-compose with Redis
- New Polaris star ASCII art logo (3 styles)

### Fixed
- Critical: `timedelta` import in working_memory.py
- All orphan modules wired into agent core
- CLI and Gateway call real Agent instead of demo stubs

### Tests
- 139 passed (96 unit + 43 integration)

## v0.1.0
- Initial skeleton: OODA loop, DAG executor, memory stubs, FastAPI gateway
