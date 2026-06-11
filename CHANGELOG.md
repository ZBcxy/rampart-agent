# CHANGELOG

## v1.1.0 (2026-06-11) — Polaris Agent

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
