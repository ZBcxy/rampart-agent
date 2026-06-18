# Product Hunt Launch Kit — ✦ Polaris Agent

## 基本信息

| 字段 | 内容 |
|------|------|
| **Product Name** | Polaris Agent |
| **Tagline** | An OODA-powered CLI agent — local models, full lifecycle, 26 tools. `npm i -g` ready. |
| **Website** | https://github.com/ZBcxy/polaris-agent |
| **npm** | https://www.npmjs.com/package/polaris-agent |
| **Topics** | Developer Tools, CLI, AI, Open Source, Productivity |
| **Pricing** | Free / Open Source (Apache 2.0) |

---

## 页面截图（5 张）

按 Product Hunt gallery 顺序：

| # | 文件 | 内容 | 命令 |
|---|------|------|------|
| 1 | `docs/screenshots/01-logo.png` | 北斗七星叙事风 Logo + 启动画面 | `polaris --logo` |
| 2 | `docs/screenshots/02-doctor.png` | 一键环境诊断 | `polaris doctor` |
| 3 | `docs/screenshots/03-config.png` | 配置管理面板 | `polaris config` |
| 4 | `docs/screenshots/04-help.png` | 完整命令参考 | `polaris --help` |

---

## Tagline（60 字符限制）

**主选：**
```
✦ Polaris Agent — Navigate Complexity with AI
```

**备选（A/B 测试）：**
```
An OODA-powered CLI agent that works out of the box
```
```
The agent CLI with full lifecycle — local models, zero config
```

---

## Description（260 字符限制）

```
✦ OODA Loop engine + 26 tools + MCP + A2A. Single-shot, pipe, or interactive
REPL. Auto-detects Ollama — zero API key needed. Session history, named profiles,
self-update, one-command diagnostics. Full lifecycle like Claude Code, but
runs on local models. npm i -g polaris-agent && polaris init — 30 seconds.
```

---

## Gallery 图片说明（每张图配一句 caption）

1. **Logo / Splash** — "Big Dipper → Polaris. Every agent needs a North Star."
2. **Doctor** — "One command to diagnose everything: Python, Ollama, API keys, PATH, disk."
3. **Config** — "Full config control. Set, get, export profiles. No .env hunting."
4. **Help** — "Single-shot, pipe, REPL, sessions, profiles, MCP, update — one CLI."

---

## Maker's Comment

Product Hunt 发布后立刻作为第一个评论发出：

---

```
Hey Product Hunt! ✦ Maker here.

I got tired of agent frameworks that required 10 config steps, or had great
CLI but cloud-only, or worked locally but had no lifecycle commands.

**Polaris is the CLI agent I wanted to use myself:**

✦ It has three modes — like Claude Code
  polaris "analyze this bug"       # single-shot
  cat errors.log | polaris         # pipe mode for scripts
  polaris                          # interactive REPL + sessions

✦ Zero config for local models
  If Ollama is running, Polaris finds it. No .env, no export, no config file.
  ollama pull qwen3:8b && polaris    # that's it.

✦ Built-in lifecycle — everything you'd expect from a mature CLI
  polaris init          30-second setup wizard
  polaris doctor        diagnose your environment in one command
  polaris profiles      work vs personal configs
  polaris sessions      resume conversations later
  polaris update        self-update
  polaris mcp add       register MCP servers
  polaris config set    change any setting, persisted instantly

✦ OODA Loop engine
  Observe → Orient → Decide → Act. The only agent framework with this
  architecture. Fighter-pilot-grade decision cycles.

✦ Protocol-native
  MCP Server (26 tools exposed to Claude Code / Continue / Zed)
  MCP Client (consume external tools)
  A2A (Agent-to-Agent discovery and delegation)

**Comparison:**
| Feature | Polaris | Claude Code | LangGraph | CrewAI | Codex |
|---------|:-----:|:-----:|:-----:|:-----:|:-----:|
| Single-shot mode | ✓ | ✓ | - | - | ✓ |
| Pipe / stdin | ✓ | ✓ | - | - | ✓ |
| Session history | ✓ | ✓ | ✓ | - | ✓ |
| Self-update | ✓ | ✓ | - | - | ✓ |
| Config profiles | ✓ | - | - | - | - |
| Local model auto-detect | ✓ | - | - | - | - |
| MCP Server+Client | ✓ | ✓ | - | - | - |
| A2A Protocol | ✓ | - | - | - | - |
| OODA Loop | ✓ | - | - | - | - |

**Get started in 30 seconds:**
```bash
npm i -g polaris-agent     # or: pip install polaris-agent
polaris init               # interactive wizard — pick your LLM
polaris "Hello, world!"    # you're running
```

Apache 2.0. 139 tests. 17.7k Python. Full source on GitHub.
Star if you find it useful. PRs welcome. Happy to answer questions!

✦ Navigate Complexity with AI
```

---

## Maker Comment 精简版（如果觉得太长）

```
✦ Polaris Agent — maker here.

What makes it different:
① Full lifecycle CLI (single-shot / pipe / REPL / sessions / profiles / MCP)
② Auto-detects Ollama — zero config for local models
③ OODA Loop engine — the only agent framework with this architecture
④ MCP Server + Client + A2A — protocol-native

30 seconds to start:
  npm i -g polaris-agent && polaris init && polaris "Hello!"

Apache 2.0. Would love your feedback!
```

---

## 发布时间 & 节奏

| 时间 | 动作 |
|------|------|
| **周一 22:00 CST** | Product Hunt 提交审核（选 "Coming Soon"） |
| **周二 22:00 CST** | 正式上线 → 立刻发 Maker Comment |
| **周二 22:15** | HN Show HN + Reddit r/LocalLLaMA 发帖，文末带 PH 链接 |
| **周二 22:30** | Twitter 发 demo 截图，带 PH 链接 |
| **周二 22:30 - 24:00** | 逐条回复 Product Hunt 评论区 |
| **周三全天** | 回复 GitHub Issues / Reddit 评论 |
| **周四** | V2EX 中文介绍 + 总结 PH 成绩 |

**关键原则：**
- PH 前 4 小时决定排名 —— Maker 必须在场逐条回复
- 不要在 PH 评论里 spam 链接 —— 只回答问题
- Reddit / HN 帖子里带 PH 链接但不过度推销 —— "Also on Product Hunt today if you prefer that format"

---

## 社交预热帖

**提前 2 天（Twitter）：**
```
Shipping something open-source this week.
If you've ever wished Claude Code could run on local models... ✦
```

**提前 1 天（Twitter/Reddit）：**
```
Tomorrow ✦ A CLI agent that:
• Works like Claude Code (single-shot / pipe / REPL / sessions)
• Runs on Ollama with zero config
• Has an OODA loop engine
• Is npm i -g away
```
