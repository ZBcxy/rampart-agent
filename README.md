<div align="center">

[English](#english) | [中文](#中文)

<img src="https://raw.githubusercontent.com/ZBcxy/rampart-agent/main/assets/logo.svg?v=3" alt="Rampart Agent" width="800">

<p>
  <img src="https://img.shields.io/badge/version-1.1.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/python-3.11+-green" alt="Python">
  <img src="https://img.shields.io/badge/license-Apache%202.0-orange" alt="License">
  <img src="https://img.shields.io/badge/protocols-MCP%20%7C%20A2A-purple" alt="Protocols">
  <img src="https://img.shields.io/badge/tests-139%20passed-brightgreen" alt="Tests">
</p>

</div>

---

<h2 id="english">English</h2>

## What is Rampart?

Rampart is a complete agent framework that works out of the box. Named for the defensive fortification that protects and empowers — it is your steadfast AI companion through complexity, with built-in alignment guards, policy engines, and comprehensive safety mechanisms.

**Three ways to use it:**

```bash
rampart "summarize this codebase"       # Single-shot — one answer, done
echo "..." | rampart                    # Pipe — works in scripts
rampart                                 # Interactive REPL — full conversation
```

---

## Quick Start

```bash
# 1. Install (pick one)
npm install -g rampart-agent     # npm (recommended)
pip install rampart-agent        # PyPI
pipx install rampart-agent       # pipx (isolated)

# 2. Configure (interactive — 30 seconds)
rampart init

# 3. Go
rampart "Hello! What can you do?"
```

### More install options

```bash
# Docker
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... ghcr.io/zbcxy/rampart-agent:latest
docker compose up -d

# One-command curl
curl -sSL https://raw.githubusercontent.com/ZBcxy/rampart-agent/main/install.py | python3
```

### Zero config with Ollama

```bash
ollama pull qwen3:8b
rampart          # ✦ Auto-detected Ollama! Model: qwen3:8b
```

---

## Lifecycle

```
┌─ Install ──────────────────────────────────────────────┐
│ pip install rampart-agent                              │
│ rampart init          → Interactive setup wizard       │
│ rampart login         → Save API keys                  │
└────────────────────────────────────────────────────────┘
                          │
┌─ Everyday use ─────────────────────────────────────────┐
│ rampart "fix this bug"        Single-shot              │
│ cat log.txt | rampart         Pipe / stdin             │
│ rampart                       Interactive REPL         │
│ rampart exec task.txt         Execute task file        │
│ rampart --model gpt-4o        Override model           │
│ rampart --approval-mode L2    Override autonomy        │
└────────────────────────────────────────────────────────┘
                          │
┌─ Manage ───────────────────────────────────────────────┐
│ rampart config               Show all config           │
│ rampart config set KEY VAL   Change a setting          │
│ rampart profiles use work    Switch profile            │
│ rampart sessions resume ...   Continue a conversation  │
│ rampart mcp add NAME CMD     Add an MCP server         │
│ rampart doctor               Diagnose issues           │
│ rampart update               Self-update               │
│ rampart logout               Remove credentials        │
└────────────────────────────────────────────────────────┘
```

---

## Commands

### Run

| Command | Description |
|---------|-------------|
| `rampart "prompt"` | Single-shot, non-interactive |
| `echo "..." \| rampart` | Pipe / stdin mode |
| `rampart` | Interactive REPL with session history |
| `rampart exec <file>` | Execute a task file |
| `rampart --model <name>` | Override model for this session |
| `rampart --approval-mode L0-L4` | Override autonomy level |

### Setup & Auth

| Command | Description |
|---------|-------------|
| `rampart init` | Interactive setup wizard |
| `rampart login` | Securely save API keys to config |
| `rampart logout` | Remove stored credentials |
| `rampart doctor` | Environment diagnostics |

### Config

| Command | Description |
|---------|-------------|
| `rampart config` | Show all configuration with categories |
| `rampart config get <key>` | Get a single value |
| `rampart config set <key> <val>` | Set and persist a value |
| `rampart config unset <key>` | Revert to default |
| `rampart config reset` | Reset all to defaults |
| `rampart config path` | Show config file path (`~/.rampart/config.json`) |
| `rampart config export --profile <name>` | Export current config as a named profile |

### Profiles

| Command | Description |
|---------|-------------|
| `rampart profiles list` | List named profiles |
| `rampart profiles use <name>` | Switch to a profile |

### Sessions

| Command | Description |
|---------|-------------|
| `rampart sessions list` | List recent sessions |
| `rampart sessions resume <id>` | Resume a conversation |

### MCP

| Command | Description |
|---------|-------------|
| `rampart mcp add <name> "<cmd>"` | Register an MCP server |
| `rampart mcp list` | List registered servers |
| `rampart mcp remove <name>` | Remove a server |

### Maintenance

| Command | Description |
|---------|-------------|
| `rampart update` | Self-update via pip |
| `rampart doctor` | Full environment diagnostics |
| `rampart --logo` | Display brand logo |
| `rampart --version` | Version info |

---

## REPL Commands

Inside the interactive REPL:

| Command | Description |
|---------|-------------|
| `exit`, `quit`, `q` | Exit (session auto-saved) |
| `help` | Show help |
| `/help` | Show slash commands |
| `/config` | Show configuration |
| `/model gpt-4o` | Change model |
| `/autonomy L2` | Change autonomy level |
| `/doctor` | Run diagnostics |
| `/sessions` | List sessions |
| `version` | Show version |
| `clear` | Clear screen |
| `config` | Show configuration |

---

## Autonomy Levels

| Level | Name | Behavior |
|-------|------|----------|
| L0 | Manual | Suggests only, never acts |
| L1 | Assisted | Acts after explicit confirmation |
| L2 | Supervised | Acts autonomously, reports |
| L3 | Autonomous | Acts within policy bounds |
| L4 | Full | Complete authority |

---

## Configuration

Config priority:

```
CLI flags > env vars > .rampart/config.local.json > .rampart/config.json > ~/.rampart/config.json > defaults
    →                        →                          →                      →
  session              project-local              project (committed)       global
                       (gitignored)
```

Three config files, three scopes:

| File | Scope | Git | Use |
|------|-------|-----|-----|
| `~/.rampart/config.json` | Global | — | API keys, default model, personal settings |
| `.rampart/config.json` | Project | Commit | Team model choice, project env vars |
| `.rampart/config.local.json` | Project | Ignore | Personal overrides per project |

### Key variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MODEL` | `gpt-4o` | Model name |
| `LLM_PROVIDER` | `openai` | openai / anthropic |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `RAMPART_AUTONOMY` | `L2` | Autonomy level |
| `RAMPART_MAX_STEPS` | `20` | Max OODA iterations |
| `LOCAL_LLM_PROVIDER` | — | ollama / openai_compatible |
| `LOCAL_LLM_MODEL` | — | Local model name |
| `SERVER_PORT` | `8000` | Gateway port |
| `JWT_SECRET` | — | JWT signing secret (required for API) |
| `EMBEDDING_PROVIDER` | `openai` | Embedding backend |

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      ⬡ Rampart Agent                     │
├──────────────────────────────────────────────────────────┤
│ CLI (rampart)     │ Gateway (FastAPI)   │ SDK (Python)   │
├────────────────────┼─────────────────────┼────────────────┤
│ ┌───────┐ ┌───────┐│ ┌───────┐ ┌───────┐│ ┌────────────┐│
│ │Planner│ │Executor││ │Planner│ │Executor││ │Multi-Agent ││
│ │OODA + │ │DAG +  ││ │OODA + │ │DAG +  ││ │Blackboard +││
│ │LLM    │ │Retry  ││ │LLM    │ │Retry  ││ │Coordinator ││
│ └───────┘ └───────┘│ └───────┘ └───────┘│ └────────────┘│
│ ┌───────┐ ┌───────┐│ ┌───────┐ ┌───────┐│ ┌────────────┐│
│ │Memory │ │Align  ││ │Memory │ │Align  ││ │ 26 Tools   ││
│ │Working│ │Guard +││ │Working│ │Guard +││ │file / web /││
│ │Semantic│ │Policy ││ │Semantic│ │Policy ││ │code / data/││
│ │Episodic│ │Engine ││ │Episodic│ │Engine ││ │system      ││
│ └───────┘ └───────┘│ └───────┘ └───────┘│ └────────────┘│
├────────────────────┴─────────────────────┴────────────────┤
│ Protocols:  MCP Server/Client  │  A2A Server/Client       │
└──────────────────────────────────────────────────────────┘
```

---

## Security

Rampart includes multiple layers of security:

- **JWT Authentication** — Bearer token based, HS256 with configurable secret
- **Security Headers** — CSP, HSTS, X-Frame-Options, X-Content-Type-Options on all responses
- **Rate Limiting** — Per-user and per-agent request throttling
- **Input Validation** — Pydantic schema validation on all API inputs
- **Alignment Guard** — Policy-based prompt and tool execution filtering
- **CORS Whitelisting** — Configurable origin restrictions
- **Error Sanitization** — No stack traces in production error responses

---

## Protocols

### MCP (Model Context Protocol)

Rampart is both an **MCP Server** and **MCP Client**.

**As Server** — expose 26 tools to any MCP-compatible client:

```json
{
  "mcpServers": {
    "rampart": {
      "command": "python",
      "args": ["-m", "mcp.server", "--stdio"]
    }
  }
}
```

**As Client** — consume external MCP tools:

```bash
rampart mcp add filesystem "npx -y @modelcontextprotocol/server-filesystem ."
```

### A2A (Agent-to-Agent Protocol)

```python
from protocols.a2a import A2AServer, AgentCard

card = AgentCard(
    name="Rampart Agent",
    description="Fortify Your Intelligence — Autonomous Agent Framework",
    url="https://my-rampart.example.com",
)
server = A2AServer(agent_card=card, tool_registry=registry)
```

---

## SDK

```python
# Synchronous
from sdk.client import RampartClient, Message

with RampartClient("http://localhost:8000") as client:
    response = client.chat([
        Message(role="user", content="Analyze Q3 sales data")
    ])
    print(response.choices[0].message.content)

# Asynchronous
from sdk.client import AsyncRampartClient

async with AsyncRampartClient() as client:
    async for chunk in client.chat_stream(messages):
        print(chunk)
```

---

## Tools (26 built-in)

| Category | Count | Tools |
|----------|:-----:|-------|
| File | 9 | read, write, list, delete, search, info, move, copy, mkdir |
| Web | 4 | search, fetch, http_request, url_encode |
| Code | 4 | python_exec, code_analyze, json_format, regex_test |
| Data | 4 | text_process, csv_parse, calc, data_transform |
| System | 5 | system_info, shell_exec, env_var, time_now, disk_usage |

---

## Local Models

| Backend | Setup | Models |
|---------|-------|--------|
| Ollama | `ollama pull qwen3:8b` | qwen3, llama3.1, mistral, deepseek-r1 |
| vLLM | `vllm serve ...` | Any HF model |
| llama.cpp | `llama-server ...` | GGUF format |

Rampart auto-detects running Ollama instances on first launch.

---

## Development

```bash
git clone git@github.com:ZBcxy/rampart-agent.git
cd rampart-agent
python -m venv venv && source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
pytest tests/ -v
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for system design and [DEVELOPMENT.md](DEVELOPMENT.md) for detailed contribution guide.

---

## License

Apache 2.0 © Rampart Team

---

<h2 id="中文">中文</h2>

## 什么是 Rampart？

Rampart（壁垒）是一个开箱即用的完整智能体框架。其名取自防御工事——它既保护又赋能，是你在复杂场景下坚如磐石的 AI 伙伴，内置对齐守卫、策略引擎和全面的安全机制。

**三种使用方式：**

```bash
rampart "帮我总结这个代码库"         # 单次问答
echo "..." | rampart                 # 管道模式，适合脚本
rampart                              # 交互式 REPL，完整对话
```

---

## 快速开始

```bash
# 1. 安装（三选一）
npm install -g rampart-agent     # npm（推荐）
pip install rampart-agent        # PyPI
pipx install rampart-agent       # pipx（隔离环境）

# 2. 配置（交互式，30 秒）
rampart init

# 3. 开始使用
rampart "你好！你能做什么？"
```

### 更多安装方式

```bash
# Docker
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... ghcr.io/zbcxy/rampart-agent:latest
docker compose up -d

# 一行命令
curl -sSL https://raw.githubusercontent.com/ZBcxy/rampart-agent/main/install.py | python3
```

### 零配置使用 Ollama

```bash
ollama pull qwen3:8b
rampart          # ✦ 自动检测到 Ollama！模型：qwen3:8b
```

---

## 生命周期

```
┌─ 安装 ────────────────────────────────────────────────┐
│ pip install rampart-agent                             │
│ rampart init          → 交互式设置向导                │
│ rampart login         → 保存 API 密钥                 │
└───────────────────────────────────────────────────────┘
                          │
┌─ 日常使用 ────────────────────────────────────────────┐
│ rampart "修复这个 bug"       单次执行                  │
│ cat log.txt | rampart        管道/标准输入             │
│ rampart                      交互式 REPL              │
│ rampart exec task.txt        执行任务文件              │
│ rampart --model gpt-4o       覆盖模型                  │
│ rampart --approval-mode L2   覆盖自主级别              │
└───────────────────────────────────────────────────────┘
                          │
┌─ 管理 ────────────────────────────────────────────────┐
│ rampart config               显示全部配置              │
│ rampart config set KEY VAL   修改配置                  │
│ rampart profiles use work    切换配置集                │
│ rampart sessions resume ...   继续对话                 │
│ rampart mcp add NAME CMD     添加 MCP 服务器           │
│ rampart doctor               诊断环境问题              │
│ rampart update               自我更新                  │
│ rampart logout               清除凭据                  │
└───────────────────────────────────────────────────────┘
```

---

## 命令参考

### 运行

| 命令 | 说明 |
|------|------|
| `rampart "prompt"` | 单次执行，非交互 |
| `echo "..." \| rampart` | 管道模式 |
| `rampart` | 交互式 REPL，带会话历史 |
| `rampart exec <file>` | 执行任务文件 |
| `rampart --model <name>` | 覆盖本次会话的模型 |
| `rampart --approval-mode L0-L4` | 覆盖自主级别 |

### 配置

| 命令 | 说明 |
|------|------|
| `rampart config` | 显示所有配置 |
| `rampart config get <key>` | 获取单个值 |
| `rampart config set <key> <val>` | 设置并持久化 |
| `rampart config unset <key>` | 恢复默认值 |

### MCP

| 命令 | 说明 |
|------|------|
| `rampart mcp add <name> "<cmd>"` | 注册 MCP 服务器 |
| `rampart mcp list` | 列出已注册服务器 |
| `rampart mcp remove <name>` | 移除服务器 |

---

## 自主级别

| 级别 | 名称 | 行为 |
|------|------|------|
| L0 | 手动 | 仅建议，不执行 |
| L1 | 辅助 | 确认后执行 |
| L2 | 监督 | 自主执行，事后报告 |
| L3 | 自主 | 在策略边界内行动 |
| L4 | 完全 | 完全授权 |

---

## 安全

Rampart 内置多层安全防护：

- **JWT 认证** — Bearer Token，HS256 算法，可配置密钥
- **安全响应头** — 所有响应附带 CSP、HSTS、X-Frame-Options、X-Content-Type-Options
- **限流** — 按用户和 Agent 的请求频率控制
- **输入验证** — 所有 API 输入经 Pydantic 模式验证
- **对齐守卫** — 基于策略的提示词和工具执行过滤
- **CORS 白名单** — 可配置的来源限制
- **错误脱敏** — 生产环境错误响应不含堆栈追踪

---

## 协议

### MCP（模型上下文协议）

Rampart 同时是 **MCP 服务端** 和 **MCP 客户端**。

**作为服务端** — 向任何 MCP 兼容客户端暴露 26 个工具：

```json
{
  "mcpServers": {
    "rampart": {
      "command": "python",
      "args": ["-m", "mcp.server", "--stdio"]
    }
  }
}
```

**作为客户端** — 使用外部 MCP 工具：

```bash
rampart mcp add filesystem "npx -y @modelcontextprotocol/server-filesystem ."
```

---

## SDK

```python
# 同步
from sdk.client import RampartClient, Message

with RampartClient("http://localhost:8000") as client:
    response = client.chat([
        Message(role="user", content="分析 Q3 销售数据")
    ])
    print(response.choices[0].message.content)
```

---

## 开发

```bash
git clone git@github.com:ZBcxy/rampart-agent.git
cd rampart-agent
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -e ".[dev]"
pytest tests/ -v
```

详见 [ARCHITECTURE.md](ARCHITECTURE.md)（系统设计）和 [DEVELOPMENT.md](DEVELOPMENT.md)（贡献指南）。

---

## 许可证

Apache 2.0 © Rampart Team
