[English](#english) | [中文](#中文)

---

<h2 id="english">English</h2>

## Architecture Overview

Rampart Agent follows a modular, layered architecture designed for extensibility and safety.

```
┌──────────────────────────────────────────────────────────────┐
│                      ENTRY POINTS                             │
│  CLI (rampart)    │  Gateway (FastAPI)    │  SDK (Python)    │
├──────────────────────────────────────────────────────────────┤
│                      CORE ENGINE                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Planner  │  │ Executor │  │  Memory  │  │  Align   │    │
│  │ OODA +   │  │ DAG +    │  │ Working  │  │ Guard +  │    │
│  │ LLM      │  │ Retry    │  │ Semantic │  │ Policy   │    │
│  │          │  │          │  │ Episodic │  │ Engine   │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
├──────────────────────────────────────────────────────────────┤
│                      MODULES                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Tools   │  │   MCP    │  │   A2A    │  │  SDK     │    │
│  │ (26)     │  │ Server + │  │ Server + │  │ Client + │    │
│  │          │  │ Client   │  │ Client   │  │ Async    │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
├──────────────────────────────────────────────────────────────┤
│                   INFRASTRUCTURE                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Cache   │  │  Config  │  │  Tracer  │  │ Metrics  │    │
│  │ Response │  │ Manager  │  │  Span    │  │ Collector│    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└──────────────────────────────────────────────────────────────┘
```

## Key Components

### Planner (OODA Loop)

The core decision-making engine follows the OODA (Observe, Orient, Decide, Act) loop:

1. **Observe** — Gather data from tools, memory, and context
2. **Orient** — Analyze observations, synthesize understanding
3. **Decide** — Choose actions based on policy and confidence thresholds
4. **Act** — Execute tools, record outcomes

Each phase uses LLM-generated prompts from the PromptManager (zero hardcoded prompts).

### Executor

- **DAG Executor** — Executes tool calls as directed acyclic graphs with dependency resolution
- **Retry Executor** — Wraps DAG execution with configurable retry logic (exponential backoff)
- **Code Harness** — Sandboxed Python code execution with validation
- **Sandbox Manager** — Isolated execution environments per agent session

### Memory System

Three-tier memory architecture:

| Tier | Type | Persistence | Purpose |
|------|------|-------------|---------|
| Working | In-process list | Session | Current context, recent actions |
| Semantic | Embedding vectors | Milvus/Redis | Long-term knowledge retrieval |
| Episodic | Structured records | Redis | Past experience, conversation history |

### Alignment Guard

- **AlignGuard** — Regex + LLM-based input/output validation
- **PolicyEngine** — Per-tool authorization based on autonomy level
- **ToolAuthorizer** — Permission checks before every tool execution
- **ConfirmationHandler** — Human-in-the-loop for dangerous operations

### Protocols

- **MCP** (Model Context Protocol) — Bidirectional: expose tools as server, consume external MCP tools as client
- **A2A** (Agent-to-Agent) — Agent discovery via AgentCard, task delegation, result handoff

### Multi-Agent

- **Blackboard** — Shared state space for multi-agent coordination
- **Coordinator** — Task decomposition and delegation across agent instances

## Data Flow

```
User Input → CLI / Gateway / SDK
    → AlignGuard.check_input()
    → Planner.generate_plan()
    → OODA Loop (observe → orient → decide → act)
        → ContextSelector selects relevant context per phase
        → PromptManager renders phase-specific prompt
        → LLM call → EntropyAuditor checks uncertainty
        → ToolAuthorizer + ConfirmationHandler gate tool execution
        → FailureClassifier categorizes errors
        → WorkingMemory records outcomes
    → AgentResult with steps, tool calls, summary
    → AlignGuard.check_output()
    → Response to user
```

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| OODA over ReAct | Structured phases enable better auditing, intervention points |
| DAG over linear execution | Parallel tool execution reduces latency |
| PromptManager over hardcoded | Themeable, testable, version-controllable prompts |
| In-memory + Redis/Milvus | Low latency for working memory, scalability for semantic |
| Pydantic validation everywhere | Type safety, auto-generated OpenAPI docs |
| Litellm as LLM abstraction | Single interface for 100+ providers |

## Security Architecture

```
Request → Rate Limiter → Auth (JWT) → Input Validation → AlignGuard → Tool Auth → Response (Sanitized) + Security Headers
```

---

<h2 id="中文">中文</h2>

## 架构概览

Rampart Agent 采用模块化分层架构，兼顾可扩展性和安全性。

## 核心组件

### 规划器（OODA 循环）

核心决策引擎遵循 OODA（观察-定位-决策-行动）循环：

1. **观察** — 从工具、记忆和上下文中收集数据
2. **定位** — 分析观察结果，综合理解
3. **决策** — 基于策略和置信度阈值选择行动
4. **行动** — 执行工具，记录结果

每个阶段使用 PromptManager 生成的 LLM 提示词（零硬编码）。

### 执行器

- **DAG 执行器** — 以有向无环图方式执行工具调用，支持依赖解析
- **重试执行器** — 封装 DAG 执行，带可配置重试逻辑（指数退避）
- **代码沙箱** — 带验证的沙箱化 Python 代码执行

### 记忆系统

三级记忆架构：工作记忆（会话级，内存）→ 语义记忆（知识检索，向量）→ 情景记忆（经验记录）

### 对齐守卫

多层安全：AlignGuard（输入/输出验证）→ PolicyEngine（自主级别授权）→ ToolAuthorizer（工具权限检查）→ ConfirmationHandler（危险操作人工确认）

### 协议

- **MCP** — 双向：作为服务端暴露 26 个工具，作为客户端调用外部 MCP 工具
- **A2A** — 智能体发现、任务委托与结果交接

### 数据流

用户输入 → AlignGuard 检查 → 规划器生成计划 → OODA 循环 → 上下文选择 → 提示词渲染 → LLM 调用 → 工具授权 → 执行 → 结果返回

## 设计决策

| 决策 | 理由 |
|------|------|
| OODA 而非 ReAct | 结构化阶段便于审计和人工介入 |
| DAG 而非线性执行 | 并行工具调用降低延迟 |
| PromptManager | 可定制、可测试、可版本控制的提示词 |
| 内存+Redis/Milvus | 工作记忆低延迟，语义记忆可扩展 |
| 全 Pydantic 验证 | 类型安全，自动生成 OpenAPI 文档 |

## 安全架构

请求 → 限流器 → 认证(JWT) → 输入验证 → AlignGuard → 工具授权 → 响应(脱敏) + 安全响应头
