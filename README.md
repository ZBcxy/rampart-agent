# Polaris Agent

> Autonomous Multi-Agent Framework — OODA Loop + DAG Executor + Blackboard Coordination

![Version](https://img.shields.io/badge/version-1.1.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-Apache%202.0-orange)
![Protocols](https://img.shields.io/badge/protocols-MCP%20%7C%20A2A-purple)
![Tests](https://img.shields.io/badge/tests-139%20passed-brightgreen)
[![CI](https://github.com/ZBcxy/polaris-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/ZBcxy/polaris-agent/actions/workflows/ci.yml)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Polaris Agent                         │
├─────────────────────────────────────────────────────────┤
│  CLI (polaris)  │  Gateway (FastAPI)  │  SDK (Python)   │
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │ Planner  │  │ Executor │  │     Multi-Agent       │  │
│  │ OODA +   │  │ DAG +    │  │ Blackboard +          │  │
│  │ LLM      │  │ Retry    │  │ Coordinator           │  │
│  └──────────┘  └──────────┘  └──────────────────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │ Memory   │  │ Align    │  │     26 Tools          │  │
│  │ Working  │  │ Guard +  │  │ file/web/code/data/   │  │
│  │ Semantic │  │ Policy   │  │ system                │  │
│  │ Episodic │  │ Engine   │  │                       │  │
│  └──────────┘  └──────────┘  └──────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│  Protocols:  MCP Server/Client  │  A2A Server/Client   │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 一条命令安装
curl -sSL https://raw.githubusercontent.com/ZBcxy/polaris-agent/main/install.py | python3

# 或手动克隆
git clone git@github.com:ZBcxy/polaris-agent.git
cd polaris-agent
pip install -e .
polaris

# Docker (ghcr.io, 零配置)
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... ghcr.io/zbcxy/polaris-agent:latest
# 或 docker compose
docker compose up -d
```

## Supported Protocols

### MCP (Model Context Protocol) — v2025-11-25

Polaris is both an **MCP Server** and **MCP Client**.

**As Server** — expose 26 tools to MCP-compatible clients (Claude Code, Continue, Zed):

```json
{
  "mcpServers": {
    "polaris": {
      "command": "python",
      "args": ["-m", "mcp.server", "--stdio"]
    }
  }
}
```

Supported MCP methods: `initialize`, `ping`, `tools/list`, `tools/call`, `resources/list`, `prompts/list`, `tasks/get`, `tasks/cancel`, `tasks/list`, `tasks/result`

**As Client** — consume external MCP tools:

```python
from mcp import MCPClient
client = MCPClient()
await client.connect_stdio("filesystem", "npx", ["-y", "@modelcontextprotocol/server-filesystem", "."])
result = await client.call_tool("read_file", {"path": "/tmp/data.txt"})
```

### A2A (Agent-to-Agent Protocol) — v1.0

Polaris can discover and collaborate with other A2A agents.

**As Server** — publish Agent Card at `/.well-known/agent-card.json`:

```python
from protocols.a2a import A2AServer, AgentCard

card = AgentCard(
    name="Polaris Agent",
    description="Autonomous multi-agent framework",
    url="https://my-polaris.example.com",
)
server = A2AServer(agent_card=card, tool_registry=registry)
```

**As Client** — discover and delegate to remote agents:

```python
from protocols.a2a import A2AClient

client = A2AClient()
card = await client.discover_agent("https://other-agent.example.com")
task = await client.send_task(card.url, "Analyze Q3 sales data")
```

A2A methods: `tasks/send`, `tasks/sendSubscribe`, `tasks/get`, `tasks/cancel`, `tasks/list`

## Configuration

### Environment Variables

#### LLM Provider

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key | For OpenAI |
| `OPENAI_API_BASE` | Custom OpenAI-compatible endpoint | Optional |
| `ANTHROPIC_API_KEY` | Anthropic API key | For Claude |
| `LLM_MODEL` | Model name | `gpt-4o` |
| `LLM_PROVIDER` | Provider (openai/anthropic) | auto-detect |
| `LLM_TEMPERATURE` | Sampling temperature | `0.3` |
| `LLM_MAX_TOKENS` | Max tokens/response | `2000` |

#### Server (Gateway)

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVER_HOST` | Gateway bind address | `0.0.0.0` |
| `SERVER_PORT` | Gateway port | `8000` |
| `JWT_SECRET` | JWT signing secret | auto-generated |
| `TOKEN_EXPIRE_HOURS` | JWT expiry hours | `24` |
| `RATE_LIMIT_USER` | Requests/min per user | `100` |
| `CORS_ALLOW_ORIGINS` | CORS origins | `["*"]` |

#### Agent Runtime

| Variable | Description | Default |
|----------|-------------|---------|
| `POLARIS_HOME` | Config/data directory | `~/.polaris` |
| `POLARIS_LOG_LEVEL` | Log level | `INFO` |
| `POLARIS_AUTONOMY` | Autonomy level (L0-L4) | `L2` |
| `POLARIS_MAX_STEPS` | Max OODA iterations | `20` |

#### Memory & Embedding

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_HOST` | Redis host for caching | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `MILVUS_HOST` | Milvus host | `localhost` |
| `MILVUS_PORT` | Milvus port | `19530` |
| `EMBEDDING_PROVIDER` | openai / sentence_transformers | `openai` |
| `EMBEDDING_MODEL` | Embedding model | `text-embedding-3-small` |

### .env File Format

```bash
# LLM
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o
LLM_TEMPERATURE=0.3

# Server
SERVER_PORT=8000
JWT_SECRET=your-production-secret-here

# Agent
POLARIS_AUTONOMY=L3
POLARIS_MAX_STEPS=30

# Memory
EMBEDDING_PROVIDER=openai
```

## CLI Usage

```bash
polaris                          # Interactive mode
polaris --logo                   # ASCII art logo
polaris --logo --style minimal   # Minimal logo
polaris --logo --style box       # Box-style logo
polaris --version                # Version info
polaris --config                 # Show configuration
polaris --modules                # List modules
polaris upgrade                  # Check for updates
```

## API Endpoints

### Gateway REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/health` | Health check |
| `POST` | `/v1/chat/completions` | Chat completion |
| `POST` | `/v1/chat/stream` | Streaming chat (SSE) |
| `GET` | `/v1/agents` | List agents |
| `GET` | `/v1/agents/{id}` | Agent details |
| `POST` | `/v1/tasks` | Create task |
| `GET` | `/v1/tasks/{id}` | Task status |

### A2A Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/.well-known/agent-card.json` | Agent discovery |
| `POST` | `/` | JSON-RPC |
| `GET` | `/tasks/{id}/stream` | SSE streaming |

## SDK Usage

```python
# Synchronous
from sdk.client import PolarisClient, Message

with PolarisClient("http://localhost:8000") as client:
    response = client.chat([
        Message(role="user", content="Analyze Q3 sales data")
    ])
    print(response.choices[0].message.content)

# Asynchronous
from sdk.client import AsyncPolarisClient

async with AsyncPolarisClient() as client:
    async for chunk in client.chat_stream(messages):
        print(chunk)
```

## Tools API

```python
from tools.registry import ToolRegistry

registry = ToolRegistry()
registry.register_all()

# Execute any tool
result = registry.execute("file_read", path="/tmp/data.txt")
result = registry.execute("web_search", query="latest AI news")
result = registry.execute("python_exec", code="result = sum(range(100))")

# LLM-compatible schemas
openai_funcs = registry.get_openai_functions()
anthropic_tools = registry.get_anthropic_tools()
```

## Agent API

```python
import asyncio
from core.agent import LLMAgent
from core.planner.llm_planner import LLMPlannerConfig

agent = LLMAgent(config=LLMPlannerConfig(
    model="gpt-4o", provider="openai", api_key="sk-...",
))

result = asyncio.run(agent.run("Create a sales report from /tmp/sales.csv"))

# Streaming
async for event in agent.run_stream("Analyze the logs"):
    print(event)
```

## Autonomy Levels

| Level | Name | Behavior |
|-------|------|----------|
| L0 | Manual | Suggests only, never acts |
| L1 | Assisted | Acts after explicit user confirmation |
| L2 | Supervised | Acts autonomously, reports actions |
| L3 | Autonomous | Acts freely within policy bounds |
| L4 | Full | Complete decision-making authority |

## Alignment Pipeline

1. **Content Safety** — blocks harmful content generation
2. **PII Detection** — prevents personal information leakage
3. **Prompt Injection** — detects jailbreak attempts
4. **Code Execution Safety** — blocks dangerous code
5. **Policy Engine** — enforces autonomy level + resource limits

## Built-in Tools (26)

| Category | Count | Tools |
|----------|:-----:|-------|
| File | 9 | read, write, list, delete, search, info, move, copy, mkdir |
| Web | 4 | search, fetch, http_request, url_encode |
| Code | 4 | python_exec, code_analyze, json_format, regex_test |
| Data | 4 | text_process, csv_parse, calc, data_transform |
| System | 5 | system_info, shell_exec, env_var, time_now, disk_usage |

## Development

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v        # 139 tests
```

## Project Structure

```
.
├── core/                   # Engine: planner, executor, memory, align, agent
├── gateway/                # FastAPI gateway with REST API
├── tools/                  # 26 executable tools + registry
├── mcp/                    # MCP Server & Client
├── protocols/a2a/          # A2A Server & Client
├── multi_agent/            # Blackboard + Coordinator
├── sdk/                    # Python SDK (sync + async)
├── cli/                    # CLI interface
└── tests/                  # 139 tests (unit + integration)
```

## vs. Production Frameworks

| Feature | Polaris | LangGraph | CrewAI | AutoGPT | Claude Code |
|---------|:-------:|:---------:|:------:|:-------:|:-----------:|
| OODA Loop | ✅ | ❌ | ❌ | ❌ | ❌ |
| Circuit Breaker | ✅ | ❌ | ❌ | ❌ | ❌ |
| Blackboard | ✅ | ❌ | ❌ | ❌ | ❌ |
| MCP + A2A | ✅ | ❌ | ❌ | ❌ | ✅ |
| Alignment Guard | ✅ | ❌ | ❌ | ❌ | ✅ |
| Tool Auth | ✅ | ❌ | ❌ | ❌ | ❌ |
| Observability | ✅ | ✅ | ❌ | ❌ | ✅ |
| Evals | ✅ | ✅ | ❌ | ❌ | ❌ |
| RAG | ✅ | ✅ | ❌ | ❌ | ❌ |
| Prompt Mgmt | ✅ | ✅ | ❌ | ❌ | ❌ |
| LLM Cache | ✅ | ✅ | ❌ | ❌ | ✅ |
| Streaming | ✅ | ✅ | ✅ | ❌ | ✅ |
| 3-Tier Memory | ✅ | ❌ | ✅ | ✅ | ❌ |
| 26 Tools | ✅ | ✅ | ✅ | ✅ | ✅ |
| Docker | ✅ | ✅ | ✅ | ✅ | ✅ |

## License

Apache 2.0
