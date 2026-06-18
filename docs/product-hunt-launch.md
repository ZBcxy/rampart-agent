# Product Hunt Launch — Polaris Agent

## 基本信息

| 字段 | 内容 |
|------|------|
| **Product Name** | Polaris Agent |
| **Tagline** | A complete CLI agent that works out of the box — local models, full lifecycle, 26 tools |
| **Website** | https://github.com/ZBcxy/polaris-agent |
| **Topics** | Developer Tools, CLI, Artificial Intelligence, Open Source, Productivity |
| **Pricing** | Free / Open Source (Apache 2.0) |

---

## Tagline（60 字符限制）

```
✦ Polaris Agent — Navigate Complexity with AI
```

备选：
```
The CLI agent with Claude Code's lifecycle + Ollama's freedom
```

---

## Description（260 字符限制）

```
Polaris is the agent CLI that does everything you expect — single-shot answers,
pipe mode for scripts, interactive REPL with session history, and a full
lifecycle of config / profiles / MCP / update / doctor. Auto-detects Ollama
for zero-API-key local runs. OODA Loop engine + 26 built-in tools. npm i -g.
```

---

## Maker’s First Comment（最重要，发布后第一时间发）

This is the long-form comment that tells the story:

---

```
Hey Product Hunt! ✦ Maker here.

I built Polaris because I was tired of AI agent frameworks that either required
50 lines of config to start, or had great local model support but no CLI, or
had a nice CLI but locked you into a single cloud provider.

**What Polaris does differently:**

1. Full lifecycle — not just "type a prompt"
   polaris "fix this bug"          # single-shot, like `claude "..."` or `codex`
   cat log.txt | polaris           # pipe mode — works in scripts
   polaris                         # interactive REPL with readline history
   polaris sessions resume last    # pick up where you left off
   polaris --output-format json    # structured output for automation

2. Zero config for local models
   If Ollama is running, Polaris auto-detects it on first launch.
   No .env, no export, no config file. Just `polaris`.

3. Built-in lifecycle management
   polaris init       # interactive setup wizard (30 seconds)
   polaris config     # show/change any setting
   polaris profiles   # work profile vs personal profile
   polaris doctor     # diagnose Python, Ollama, API keys, PATH, disk
   polaris update     # self-update
   polaris mcp add    # register MCP servers

4. OODA Loop engine
   Observe → Orient → Decide → Act. The same decision cycle used by
   fighter pilots. Polaris is the only agent framework with a native
   OODA loop architecture.

5. Protocol-native
   MCP Server: expose 26 tools to Claude Code, Continue, Zed
   MCP Client: consume external MCP tools
   A2A: Agent-to-Agent discovery and delegation

**Quick comparison:**
| Feature | Polaris | Claude Code | LangGraph | CrewAI |
|---------|:-----:|:-----:|:-----:|:-----:|
| Single-shot | ✓ | ✓ | - | - |
| Pipe mode | ✓ | ✓ | - | - |
| Sessions | ✓ | ✓ | ✓ | - |
| Self-update | ✓ | ✓ | - | - |
| Config profiles | ✓ | - | - | - |
| Ollama auto-detect | ✓ | - | - | - |
| MCP Server+Client | ✓ | ✓ | - | - |
| OODA Loop | ✓ | - | - | - |

**Get started:**
```bash
npm i -g polaris-agent    # or pip install polaris-agent
polaris init              # 30-second setup wizard
polaris "Hello!"          # done!
```

It's Apache 2.0, 139 tests passing, 17.7k lines of Python.
Would love your feedback, issues, and PRs!

✦ Navigate Complexity with AI
```

---

## Media Assets

### 截图 1: 终端启动画面（北斗七星叙事风 Logo）

```
Command: polaris --logo

Content: Full default logo with Big Dipper → Polaris constellation,
         "POLARIS" brand text, tagline, and info panel
```

### 截图 2: polaris doctor 诊断输出

```
Command: polaris doctor

Content: Environment diagnostics showing Python version, Ollama status,
         API key status, PATH check, disk space — all in colored panels
```

### 截图 3: 配置管理

```
Command: polaris config

Content: Full configuration display with categorized sections
         (LLM Provider / Local LLM / Agent Runtime / Server / Memory)
```

### 截图 4: 帮助信息

```
Command: polaris --help

Content: Full lifecycle command reference with colored output
```

### Demo GIF（如果有条件）

```
1. polaris init (30s wizard)
2. polaris "What is the OODA loop?" (single-shot)
3. echo "summarize: ..." | polaris (pipe mode)
4. polaris sessions list → polaris sessions resume ...
```

---

## 发布时间建议

- **日期**: 周二或周三（Product Hunt 流量最高）
- **时间**: 北京时间晚上 10:00 = Pacific 7:00 AM = Eastern 10:00 AM
- **预热**: 提前 2 天在 Twitter/Reddit 发预告
- **首小时**: Maker comment + 回复每一条评论
- **首日**: 在 Hacker News / Reddit 交叉发布链接

---

## 社交联动

发布当天同时在以下渠道发帖，互相引流：

| 时间 | 渠道 | 内容 |
|------|------|------|
| T-2d | Twitter/X | "Shipping something this week. It starts with ✦" |
| T-0 | Product Hunt | Launch |
| T+1h | HN Show HN | "Show HN: Polaris Agent — CLI agent with full lifecycle" |
| T+1h | r/LocalLLaMA | "Polaris Agent — local-first CLI agent, auto-detects Ollama" |
| T+2h | Twitter/X | 发 demo GIF + PH 链接 |
| T+1d | V2EX | 中文介绍 + PH 回顾 |
