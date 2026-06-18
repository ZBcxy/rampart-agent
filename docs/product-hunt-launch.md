# Product Hunt Launch Kit — ✦ Polaris Agent

---

## 页面信息

| 字段 | 内容 |
|------|------|
| **Name** | Polaris Agent |
| **Tagline** | A complete CLI agent — local models, full lifecycle, `npm i -g` ready |
| **Website** | https://github.com/ZBcxy/polaris-agent |
| **npm** | https://www.npmjs.com/package/polaris-agent |
| **Topics** | Developer Tools · CLI · AI · Open Source |
| **Pricing** | Free / Apache 2.0 |

---

## Tagline（60 字符限制）

```
✦ Polaris Agent — Navigate Complexity with AI
```

---

## Description（260 字符）

```
✦ OODA Loop + 26 tools + MCP + A2A. Single-shot, pipe, or interactive REPL.
Auto-discovers Ollama — zero API key for local runs. Sessions, profiles,
self-update, one-command diagnostics. Full lifecycle CLI like Claude Code.
npm i -g polaris-agent && polaris init   — 30 seconds to launch.
```

---

## Gallery（5 张截图）

| # | 文件 | 标题 | Caption |
|---|------|------|---------|
| 1 | `01-logo.png` | Big Dipper → Polaris | Every agent needs a North Star ✦ |
| 2 | `02-doctor.png` | One-command diagnostics | Python, Ollama, API keys, PATH, disk — all in one |
| 3 | `03-config.png` | Configuration, sorted | Set, get, export profiles. No .env hunting. |
| 4 | `04-help.png` | Full lifecycle | Single-shot · pipe · REPL · sessions · profiles · MCP · update |

---

## Maker Comment（发布后第一时间发）

```
Hey Product Hunt! ✦ Maker here.

AI agents are everywhere, but most are either cloud-only black boxes
or require 50 lines of YAML to configure. I wanted something different.

Polaris is the agent CLI I actually enjoy using:

① It has all three modes — like a mature tool
   polaris "fix this bug"       # single-shot
   cat errors.log | polaris     # pipe mode
   polaris                      # interactive REPL with sessions

② Zero config for local models
   If Ollama is running, Polaris finds it. No env vars needed.
   ollama pull qwen3:8b && polaris   — that's literally it.

③ Built-in lifecycle management
   polaris init         30s setup wizard
   polaris doctor       diagnose your whole environment
   polaris profiles     work vs personal configs
   polaris sessions     resume conversations later
   polaris update       self-update
   polaris mcp add      register MCP servers

④ OODA Loop engine
   Observe → Orient → Decide → Act. Fighter-pilot decision cycles.
   The only agent framework built on this architecture.

⑤ Protocol-native
   MCP Server: expose 26 tools to Claude Code / Continue / Zed
   MCP Client: consume external MCP tools
   A2A: Agent-to-Agent discovery and delegation

Quick comparison:
| Feature | Polaris | Claude Code | LangGraph | CrewAI | Codex |
|---------|:-----:|:-----:|:-----:|:-----:|:-----:|
| Single-shot | ✓ | ✓ | - | - | ✓ |
| Pipe mode | ✓ | ✓ | - | - | ✓ |
| Session history | ✓ | ✓ | ✓ | - | ✓ |
| Self-update | ✓ | ✓ | - | - | ✓ |
| Config profiles | ✓ | - | - | - | - |
| Ollama auto-detect | ✓ | - | - | - | - |
| MCP Server+Client | ✓ | ✓ | - | - | - |
| OODA Loop | ✓ | - | - | - | - |

Get started:
  npm i -g polaris-agent && polaris init && polaris "Hello!"

Apache 2.0 · 139 tests · 17.7k Python · github.com/ZBcxy/polaris-agent
Star = appreciated. PRs = welcome. Questions = I'm here all day.

✦ Navigate Complexity with AI
```

---

## 发布节奏

| 时间 (CST) | 动作 |
|-------------|------|
| 周一 22:00 | PH 提交 Coming Soon 页面 |
| **周二 22:00** | 正式上线 → 立即发 Maker Comment |
| 周二 22:15 | HN Show HN + Reddit r/LocalLLaMA |
| 周二 22:30 | Twitter 发截图 + PH 链接 |
| 周二 22-24 | 逐条回复 PH 评论 |
| 周三 | 回复 GitHub Issues / Reddit |
| 周四 | V2EX 中文总结 |

---

## 预热帖

**T-2（Twitter）：**
> Shipping something open-source this week. ✦

**T-1（Twitter/Reddit）：**
> Tomorrow: an agent CLI that works like Claude Code, runs on Ollama with
> zero config, and has an OODA loop. npm i -g away.
