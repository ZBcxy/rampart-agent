[English](#english) | [中文](#中文)

---

<h2 id="english">English</h2>

## Prerequisites

- Python 3.11+
- pip / pipx / npm (for installation)
- (Optional) Docker for containerized deployment
- (Optional) Redis / Milvus for persistent memory

## Local Development Setup

```bash
# Clone
git clone git@github.com:ZBcxy/rampart-agent.git
cd rampart-agent

# Virtual environment
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Verify
rampart --version
```

## Project Structure

```
rampart-agent/
├── assets/                  # Logo SVG
├── cli/                     # CLI interface
│   ├── rampart_cli.py       #   Full lifecycle CLI
│   └── init_wizard.py       #   Interactive setup wizard
├── core/                    # Engine
│   ├── agent.py             #   Integrated OODA agent
│   ├── planner/             #   OODA loop, LLM planner, confidence
│   ├── executor/            #   DAG executor, retry, sandbox
│   ├── memory/              #   Working, semantic, episodic memory
│   ├── align/               #   Alignment guard, policy engine
│   ├── prompts/             #   Prompt manager + templates
│   ├── config_manager.py    #   Layered config system
│   ├── logo.py              #   Terminal brand identity
│   ├── observability.py     #   Structured logging + tracing
│   ├── cache.py             #   Response cache
│   ├── context_selector.py  #   Dynamic context selection
│   ├── entropy_audit.py     #   LLM output uncertainty audit
│   ├── failure_attribution.py # Root cause classification
│   └── intervention.py      #   Human intervention logging
├── gateway/                 # FastAPI REST API
│   ├── main.py              #   App factory + middleware
│   ├── config.py            #   Pydantic settings
│   ├── api/v1/              #   REST endpoints
│   ├── middlewares/         #   Error, rate limiter, logging, security headers
│   └── security/            #   JWT auth, authorization
├── tools/                   # 26 executable tools + registry
├── mcp/                     # MCP Server & Client
├── protocols/a2a/           # A2A Server & Client
├── multi_agent/             # Blackboard + Coordinator
├── sdk/                     # Python SDK (sync + async)
├── skills/                  # Agent skills (RAG, ...)
├── tests/                   # Unit + integration tests
├── scripts/                 # Utility scripts
├── docs/                    # Screenshots
├── npm/                     # npm distribution wrapper
├── install.py               # One-command lifecycle manager
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Running Tests

```bash
# All tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# With coverage
pytest tests/ -v --cov --cov-report=term-missing

# Specific test file
pytest tests/unit/test_agent.py -v
```

## Code Style

- **Line length**: 120 characters
- **Formatter**: Black
- **Import sorting**: isort (Black profile)
- **Type checking**: mypy (strict mode)
- **Linting**: flake8

```bash
# Format
black .
isort .

# Type check
mypy core/

# Lint
flake8 core/ gateway/ tools/
```

## Environment Variables

Key variables in `.env`:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes* | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | Yes* | — | Anthropic API key |
| `LLM_MODEL` | No | `gpt-4o` | Model name |
| `LLM_PROVIDER` | No | `openai` | LLM provider |
| `JWT_SECRET` | Yes (API) | — | JWT signing secret |
| `RAMPART_HOME` | No | `~/.rampart` | Config & data directory |
| `REDIS_HOST` | No | `localhost` | Redis for memory |
| `SERVER_PORT` | No | `8000` | API gateway port |

*One of OPENAI_API_KEY or ANTHROPIC_API_KEY is required, depending on LLM_PROVIDER.

## API Development

```bash
# Start gateway
python -m uvicorn gateway.main:app --reload

# OpenAPI docs
open http://localhost:8000/docs

# Health check
curl http://localhost:8000/v1/health
```

## Docker

```bash
# Build
docker build -t rampart-agent .

# Run
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... rampart-agent

# Compose
docker compose up -d
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Write tests for your changes
4. Run the full test suite: `pytest tests/ -v`
5. Format code: `black . && isort .`
6. Commit: `git commit -m "feat: add my feature"`
7. Push and open a Pull Request

---

<h2 id="中文">中文</h2>

## 环境要求

- Python 3.11+
- pip / pipx / npm（安装用）
- （可选）Docker 容器化部署
- （可选）Redis / Milvus 持久化记忆

## 本地开发

```bash
# 克隆
git clone git@github.com:ZBcxy/rampart-agent.git
cd rampart-agent

# 虚拟环境
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows

# 安装开发依赖
pip install -e ".[dev]"

# 验证
rampart --version
```

## 运行测试

```bash
pytest tests/ -v                     # 全部测试
pytest tests/unit/ -v                # 仅单元测试
pytest tests/ -v --cov --cov-report=term-missing  # 含覆盖率
```

## 代码风格

- 行长度：120 字符
- 格式化：Black
- 导入排序：isort（Black 配置）
- 类型检查：mypy（严格模式）

```bash
black . && isort .          # 格式化
mypy core/                  # 类型检查
flake8 core/ gateway/ tools/  # 代码检查
```

## 环境变量

| 变量 | 必填 | 默认 | 说明 |
|------|------|------|------|
| `OPENAI_API_KEY` | 是* | — | OpenAI API 密钥 |
| `JWT_SECRET` | 是（API） | — | JWT 签名密钥 |
| `LLM_MODEL` | 否 | `gpt-4o` | 模型名称 |

*取决于 LLM_PROVIDER 需要 OPENAI_API_KEY 或 ANTHROPIC_API_KEY 之一。

## 贡献指南

1. Fork 仓库
2. 创建功能分支：`git checkout -b feat/my-feature`
3. 为改动编写测试
4. 运行完整测试：`pytest tests/ -v`
5. 格式化代码：`black . && isort .`
6. 提交：`git commit -m "feat: add my feature"`
7. 推送并发起 Pull Request
