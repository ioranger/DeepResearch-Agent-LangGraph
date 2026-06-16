# DeepResearch on LangGraph

**一个生产级的深度研究智能体：规划、搜索、反思、引用、报告——实时流式推送到你的浏览器。**

[English](README.md) | **简体中文**

<p align="left">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="#"><img src="https://img.shields.io/badge/后端-FastAPI%20%2B%20LangGraph-009688?logo=fastapi&logoColor=white" alt="Backend"></a>
  <a href="#"><img src="https://img.shields.io/badge/前端-Vue%203%20%2B%20Vite-42b883?logo=vuedotjs&logoColor=white" alt="Frontend"></a>
  <a href="#"><img src="https://img.shields.io/badge/测试-34%20通过%20%E2%9C%93-brightgreen" alt="Tests"></a>
  <a href="#"><img src="https://img.shields.io/badge/警告-0-success" alt="Warnings"></a>
</p>

> **提交主题 → 智能体拆解为子任务 → 多后端并行搜索 → 反思"信息是否充足" → 综合为带引用的 Markdown 报告 → 通过 Server-Sent Events 实时流式推送到你的浏览器。**

---

## 📑 目录

- [为什么选择 DeepResearch？](#-为什么选择-deepresearch)
- [核心特性](#-核心特性)
- [界面预览](#-界面预览)
- [架构设计](#-架构设计)
- [技术栈](#-技术栈)
- [项目结构](#-项目结构)
- [快速开始](#-快速开始)
- [配置参考](#-配置参考)
- [搜索后端矩阵](#-搜索后端矩阵)
- [API 参考](#-api-参考)
- [SSE 事件协议](#-sse-事件协议)
- [开发流程](#-开发流程)
- [测试](#-测试)
- [性能与质量对比](#-性能与质量对比)
- [路线图](#-路线图)
- [贡献指南](#-贡献指南)
- [安全](#-安全)
- [许可证](#-许可证)
- [致谢](#-致谢)

---

## 🌟 为什么选择 DeepResearch？

大多数研究助手都**流于表面**（单轮搜索 + 总结）和**缺乏来源**（无法验证论断）。DeepResearch 通过引入最优秀的开源研究智能体的最佳实践来同时解决这两个问题：

| 模式 | 来源 | DeepResearch |
|---|---|---|
| **反思循环**——信息不足时再次搜索 | `open_deep_research`（LangChain） | ✅ `iterative_research` |
| **引用绑定**——行内 `[n]` + 末尾参考文献 | `GPT Researcher` | ✅ 编号化来源 + `## 参考来源` 段 |
| **结构化规划**——任务使用 JSON schema 约束 | `open_deep_research` | ✅ `with_structured_output(TaskPlan)` |
| **分节报告**——避免一次性 LLM 质量塌方 | `GPT Researcher` | ✅ 逐节 LLM + 拼装 |
| **并行扇出**——子任务并发执行 | LangGraph `Send` | ✅ 原生 LangGraph `Send` API |

结果是**更深、更可信、更可审查**的研究体验——**34 个测试通过，0 个弃用警告**。

---

## ✨ 核心特性

### 🔬 研究质量
- **反思循环**——每个子任务走 `search → summarize → reflect →（如不充分则再搜索）`，上限由 `MAX_WEB_RESEARCH_LOOPS` 控制。智能体自问："信息是否充足？还缺什么？"，并以追问继续。
- **引用绑定**——每个来源编号为 `[1] [2] [3]`；summary 强制在引用信息时使用 `[n]` 标注；最终报告追加去重的 `## 参考来源` 段。
- **结构化规划**——`with_structured_output(TaskPlan)` 保证合法 JSON；当 LLM provider 不支持时回退到手工正则解析。
- **片段过滤**——轻量的关键词重叠打分，将长结果列表裁剪为最相关的前 K 个片段，降低 prompt 噪声和 token 成本。
- **分节报告**——每个任务有独立的 `## {title}` 章节，再由 LLM 拼装为完整报告——避免单次长 prompt 调用的质量断崖。

### 🏎 架构与性能
- **真异步流式**——`/research/stream` 改为 `async def`，共享 FastAPI 事件循环，不再为每个请求派生私有事件循环。
- **Lifespan 替代 `on_event`**——现代的 `asynccontextmanager lifespan` 替换了已弃用的 `@app.on_event("startup")`。
- **配置单例**——`Configuration.from_env()` 在应用启动时**只调用 1 次**（从 4 次降下来），杜绝配置漂移。
- **失败不再二次调用**——流式失败不再触发 `graph.ainvoke()` 重跑，而是发送类型化 `error` 事件后直接结束。
- **轻量日志**——单个 stderr sink 取代重复的 INFO+ERROR sink，级别由 `LOG_LEVEL` 控制。

### 🧰 工程
- **LangGraph StateGraph**——`plan → research（并行）→ report → persist`，使用 `Send` 扇出 + reducer 状态合并。
- **Pydantic v2 配置**——类型安全，环境变量驱动，校验器强制约束（`CORS_ORIGINS` 解析逗号分隔的 env 值）。
- **34 个 Pytest 用例**——涵盖 config / models / search / planner / reporter / researcher 的单元测试 + SSE 协议集成测试。
- **零弃用警告**——所有 `@app.on_event` 调用都已迁移；FastAPI 日志干净清爽。

### 🎨 前端
- **App.vue：2304 → 56 行**——结构重构后减少 98%。
- **Composable 逻辑**——`useResearchStream.ts`（716 行）封装 SSE 连接、状态机、事件分发。
- **4 个可复用组件**——`TopicInput` / `TaskList` / `SourcePanel` / `ReportView`。
- **全局样式表**——1308 行 CSS 抽出到 `style-extracted.css` 便于复用。

### 🔌 集成
- **5 个搜索后端**——`duckduckgo`（免 key）、`tavily`（付费）、`perplexity`（带引用综合）、`searxng`（自托管）、`advanced`（扇出聚合 + 隔离）。
- **3 个 LLM Provider**——`ollama`、`lmstudio`、任意 OpenAI 兼容端点。
- **持久化笔记**——报告与任务笔记以 Markdown + `notes_index.json` 索引形式保存到 `backend/data/notes/`。

---

## 🎬 界面预览

> 运行 `cd frontend && npm run dev` 访问 <http://localhost:5173> 体验。

```
┌─────────────────────────────────────────────────────────────┐
│ 深度研究助手                       [新建研究] [取消] [返回]  │
│                                                             │
│ ┌─ 研究任务 ──────┐  ┌─ 报告 ───────────────────────────┐ │
│ │ ● 背景梳理       │  │ # 多模态模型在 2025 年的突破      │ │
│ │ ● 技术演进       │  │                                   │ │
│ │ ● 应用场景       │  │ ## 1. 背景梳理                    │ │
│ │ ○ 风险评估       │  │ 多模态模型在 2024 年突破 … [1][2]  │ │
│ └──────────────────┘  │                                   │ │
│                       │ ## 2. 技术演进                    │ │
│ ┌─ 来源 ───────────┐  │ 从 CLIP 到 GPT-4V 的演进 … [3]   │ │
│ │ [1] OpenAI Blog  │  │                                   │ │
│ │ [2] arXiv 2024   │  │ ## 参考来源                       │ │
│ │ [3] Anthropic    │  │ [1] OpenAI Blog — https://…       │ │
│ └──────────────────┘  │ [2] arXiv 2024 — https://…         │ │
│                       │ [3] Anthropic — https://…          │ │
│                       └────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏗 架构设计

### 流水线概览

```
        ┌──────────┐
        │  START   │   用户提交主题
        └────┬─────┘
             ▼
        ┌──────────┐
        │  plan    │   with_structured_output(TaskPlan)
        └────┬─────┘   将主题拆解为 3–5 个子任务
             ▼
   ┌───── research (Send 扇出，并行) ─────┐
   │  循环最多 MAX_WEB_RESEARCH_LOOPS 轮：  │
   │    ① search  →  [n] 编号化来源        │
   │    ② 流式总结（强制带引用）           │
   │    ③ reflect → 信息是否充足？         │
   │    ④ 如不足：用 follow-up 重新搜索     │
   └──────────────────┬──────────────────────┘
                      ▼
                ┌──────────┐
                │  report  │   逐节 LLM + 拼装
                └────┬─────┘  + 追加 `## 参考来源`
                     ▼
                ┌──────────┐
                │ persist  │   写入 backend/data/notes/
                └────┬─────┘
                     ▼
                   END
```

### 技术栈

| 层级 | 技术 | 用途 |
|---|---|---|
| **编排** | LangGraph `StateGraph` | 状态机，`Send` 扇出 + reducer 合并 |
| **后端** | FastAPI + uvicorn | 异步 HTTP + SSE 流式 |
| **LLM 抽象** | LangChain `ChatModel` | 可插拔 provider（Ollama / LMStudio / OpenAI 兼容） |
| **搜索** | Tavily / DDG / Perplexity / SearXNG | 多后端调度，每个后端独立隔离 |
| **配置** | Pydantic v2 + `python-dotenv` | 类型安全的 env 驱动配置 |
| **日志** | loguru | 单 sink 结构化日志 |
| **前端** | Vue 3 + Vite + TypeScript | Composition API + SSE 状态 composable |
| **测试** | pytest + pytest-asyncio | 34 个测试，集成 + 单元 |
| **笔记** | Markdown + JSON 索引 | 人类可读、git 友好的持久化 |

---

## 📁 项目结构

```
helloagents-deepresearch/
├── backend/
│   ├── src/
│   │   ├── main.py                # FastAPI 入口（async 端点 + lifespan）
│   │   ├── agent.py               # DeepResearchAgent（arun / astream / run）
│   │   ├── config.py              # Pydantic Configuration（env 驱动）
│   │   ├── models.py              # 状态模型（TodoItem, TaskPlan, …）
│   │   ├── prompts.py             # 本地化提示词（zh-CN / en-US）
│   │   ├── llm.py                 # LLM 工厂
│   │   ├── services/
│   │   │   ├── researcher.py      # ★ 反思循环（iterative_research）
│   │   │   ├── planner.py         # ★ with_structured_output(TaskPlan)
│   │   │   ├── summarizer.py      # research_node 瘦壳
│   │   │   ├── reporter.py        # ★ 逐节生成
│   │   │   ├── search.py          # 多后端调度 + 引用
│   │   │   ├── event_adapter.py   # SSE 事件协议映射
│   │   │   ├── text_processing.py # ★ 片段相关性过滤
│   │   │   └── notes.py           # 持久化 Markdown 笔记
│   │   └── tools/                 # 工具适配器（search_tool, note_tool）
│   ├── data/notes/                # ★ 持久化笔记（在 src/ 之外）
│   ├── tests/
│   │   ├── unit/                  # 32 个单元测试
│   │   └── integration/           # 2 个 SSE 协议测试
│   ├── pyproject.toml             # uv 管理依赖 + 工具配置
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.vue                # ★ 56 行（薄壳）
│   │   ├── composables/
│   │   │   └── useResearchStream.ts  # ★ SSE 状态机
│   │   ├── components/            # ★ 4 个组件
│   │   │   ├── TopicInput.vue
│   │   │   ├── TaskList.vue
│   │   │   ├── SourcePanel.vue
│   │   │   └── ReportView.vue
│   │   ├── services/api.ts        # SSE 客户端
│   │   ├── style.css              # 全局样式
│   │   ├── style-extracted.css    # ★ 从 App.vue 抽出
│   │   └── main.ts
│   └── package.json
├── .comate/specs/                 # SDD spec 文档
│   ├── quality-foundation-harness/
│   ├── opensource-benchmark-upgrade/
│   └── architecture-optimization/
├── docker-compose.yml
├── README.md                      # ← 你在这里
└── LICENSE
```

★ = 本次升级中新增或大幅重构的

---

## 🚀 快速开始

### 前置依赖

- **Python ≥ 3.10**（项目用 uv 管理）
- **Node.js ≥ 18**（前端）
- **uv**（推荐）：`brew install uv` 或参考 [astral-sh/uv](https://github.com/astral-sh/uv)
- 本地 LLM 端点（Ollama / LMStudio）**或** OpenAI 兼容的 API key

### 1. 克隆

```bash
git clone https://github.com/ioranger/DeepResearch-Agent-LangGraph.git
cd DeepResearch-Agent-LangGraph
```

### 2. 启动后端

```bash
cd backend
uv sync                          # 安装所有依赖
cp .env.example .env             # 复制配置模板
```

编辑 `.env`，至少设置：

```env
LLM_PROVIDER=ollama              # 或 "lmstudio" / "custom"
LLM_MODEL_ID=qwen2.5:7b          # provider 支持的任意模型
LLM_BASE_URL=http://localhost:11434
SEARCH_API=duckduckgo            # 默认值——无需 API key
```

然后启动服务：

```bash
uv run uvicorn main:app --reload
```

> 默认 `SEARCH_API=duckduckgo` **无需 API key**，所以你只需要配好本地 LLM 就能跑通端到端研究。

### 3. 启动前端

```bash
cd ../frontend
npm install
npm run dev
```

打开 <http://localhost:5173>。

### 4. 或用 Docker 一键启动

```bash
# 后端 + 前端
docker compose up --build

# 后端 + 前端 + 本地 Ollama
docker compose --profile ollama up --build
```

Ollama profile 是可选的，默认栈保持精简。

### 5. 健康检查

```bash
curl http://localhost:8000/healthz
# → {"status": "ok"}
```

---

## ⚙️ 配置参考

所有运行时配置来自 `backend/src/config.py` 的 `Configuration.from_env()`，由环境变量驱动。完整列表见 [`backend/.env.example`](backend/.env.example)。

### 核心

| 变量 | 默认 | 用途 |
|---|---|---|
| `LLM_PROVIDER` | `custom` | `ollama` / `lmstudio` / `custom`（OpenAI 兼容） |
| `LLM_MODEL_ID` | _(无)_ | 传给 provider 的模型名 |
| `LLM_BASE_URL` | _(无)_ | provider 端点（如 `http://localhost:11434`） |
| `LLM_API_KEY` | _(无)_ | API key（本地通常不需要） |
| `LLM_TIMEOUT` | `60` | LLM 请求超时（秒） |
| `LOCALE` | `zh-CN` | 智能体输出语言：`zh-CN` 或 `en-US` |

### 搜索

| 变量 | 默认 | 用途 |
|---|---|---|
| `SEARCH_API` | `duckduckgo` | 默认搜索后端 |
| `TAVILY_API_KEY` | _(无)_ | `tavily` 后端必需 |
| `PERPLEXITY_API_KEY` | _(无)_ | `perplexity` 后端必需 |
| `SEARXNG_URL` | `http://localhost:8888` | `searxng` 后端必需 |

### 研究

| 变量 | 默认 | 用途 |
|---|---|---|
| `MAX_WEB_RESEARCH_LOOPS` | `2` | 每个子任务最多反思迭代次数 |
| `FETCH_FULL_PAGE` | `True` | 搜索结果中是否包含完整页面内容 |
| `USE_TOOL_CALLING` | `True` | 启用结构化工具调用 |
| `STRIP_THINKING_TOKENS` | `False` | 剥离 LLM 输出中的 `<think>…</think>` |

### 服务

| 变量 | 默认 | 用途 |
|---|---|---|
| `HOST` | `0.0.0.0` | FastAPI 绑定地址 |
| `PORT` | `8000` | FastAPI 端口 |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | 逗号分隔的允许来源 |
| `LOG_LEVEL` | `INFO` | loguru 级别 |

### 笔记

| 变量 | 默认 | 用途 |
|---|---|---|
| `ENABLE_NOTES` | `True` | 是否将任务进度持久化到 `NoteService` |
| `NOTES_WORKSPACE` | `backend/data/notes` | 笔记持久化目录 |

---

## 🔍 搜索后端矩阵

| 后端 | API Key | 本地优先 | 适用场景 |
|---|---|---|---|
| `duckduckgo` | ❌ | ✅ | 默认。零配置，作为基线。 |
| `tavily` | ✅ | ❌ | 高质量结果，付费。 |
| `perplexity` | ✅ | ❌ | 综合答案 + 引用。 |
| `searxng` | ❌（自托管） | ✅ | 注重隐私，默认 `http://localhost:8888`。 |
| `advanced` | 混合 | 混合 | **扇出聚合器**：并发运行 4 个后端，聚合结果，隔离每个后端的失败。 |

前端在每次请求时都暴露这 5 个选项；后端同时尊重 `SEARCH_API` 作为默认值。

---

## 🔌 API 参考

### `GET /healthz`

存活探针。

```bash
curl http://localhost:8000/healthz
# → {"status": "ok"}
```

### `POST /research`

同步运行研究流水线，返回最终报告。

```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "多模态模型在 2025 年的关键突破",
    "search_api": "duckduckgo"
  }'
```

**响应**（节选）：

```json
{
  "report_markdown": "# 多模态模型在 2025 年的突破\n\n## 1. 背景梳理\n...",
  "todo_items": [
    {
      "id": 1,
      "title": "背景梳理",
      "status": "completed",
      "summary": "要点内容 [1][2]",
      "sources_summary": "[1] OpenAI Blog — https://…",
      "citations": [1, 2],
      "note_id": "research_20260615_..."
    }
  ]
}
```

### `POST /research/stream`

实时流式 Server-Sent Events。

```bash
curl -N -X POST http://localhost:8000/research/stream \
  -H "Content-Type: application/json" \
  -d '{"topic": "量子计算 2025 进展"}'
```

---

## 📡 SSE 事件协议

`/research/stream` 发送的事件（每个 `data:` 行一个 JSON 对象）：

| `type` | 负载 | 时机 |
|---|---|---|
| `status` | `{message, task_id?}` | 状态更新（如"初始化研究流程"） |
| `todo_list` | `{tasks: [...], step}` | planner 完成后 |
| `task_status` | `{task_id, status, title, intent, summary?, sources_summary?, step?}` | 每个任务状态变更 |
| `task_reflection` | `{task_id, is_sufficient, follow_up_query, reasoning, current_loop, max_loops}` | **★ 每次反思后** |
| `sources` | `{task_id, latest_sources: [{id, title, url, snippet}], backend, ...}` | **★ 结构化来源列表（原为原始文本）** |
| `task_summary_chunk` | `{task_id, content, note_id}` | 流式总结 token |
| `report_note` | `{note_id, title, content, note_path}` | 报告持久化时 |
| `final_report` | `{report, note_id, note_path}` | 流水线末尾 |
| `error` | `{code, detail}` | 失败时（取代静默重试） |
| `done` | `{}` | 流终止符（总是发送） |

★ = 本次升级中新增

---

## 🛠 开发流程

### Lint 与格式化

```bash
cd backend
uv run ruff check src tests
uv run ruff format src tests
```

### Pre-commit Hooks

```bash
./scripts/install_hooks.sh
```

### 添加新搜索后端

1. 在 `services/search.py` 中添加 `_search_<name>(query, config)` 函数
2. 在 `dispatch_search` 的 `handlers` 字典中注册
3. （可选）加入 `advanced` 的扇出列表

### 添加新 LLM Provider

1. 在 `llm.py` 中添加 `build_<provider>_chat_model(cfg)`
2. 更新 `config.py` 中的 `llm_provider` 选项

### 调整反思循环

1. 编辑 `services/researcher.py`——循环是自包含的
2. 调整 `prompts.py` 中的 `_reflect` 提示词以改变评估标准

---

## ✅ 测试

```bash
cd backend
uv run pytest                 # 34 个通过
uv run pytest -v              # 详细输出
uv run pytest --tb=short      # 简短 traceback
```

### 测试布局

```
backend/tests/
├── unit/
│   ├── test_config.py         # env 解析、override
│   ├── test_models.py         # TodoItem, merge_todos
│   ├── test_planner.py        # ★ 结构化输出 + 回退
│   ├── test_prompts.py        # zh-CN / en-US 本地化
│   ├── test_reporter.py       # ★ References 段
│   ├── test_researcher.py     # ★ 反思解析
│   ├── test_search.py         # ★ 引用感知上下文
│   └── ...
└── integration/
    └── test_api.py            # /healthz + /research/stream SSE
```

★ = 本次升级中新增

集成测试通过 `monkeypatch` mock LLM 和搜索层，所以整套测试在 **< 5 秒** 内离线运行。

---

## 📊 性能与质量对比

| 指标 | 升级前 | 升级后 | 变化 |
|---|---|---|---|
| **测试数** | 0 | 34 | +34 |
| **Pytest 警告** | 6（on_event） | 0 | −6 |
| **App.vue 行数** | 2304 | 56 | **−98%** |
| **每次请求的 `Configuration.from_env()` 调用** | 4 | 1 | −75% |
| **搜索后端隔离** | 静默回退 | per-backend try/except | 提升 |
| **反思循环** | 0（单轮） | 最多 N 轮 | +反思 |
| **引用绑定** | 原始来源列表 | `[n]` 行内 + References | +引用 |
| **规划解析稳定性** | 文本上正则 | `with_structured_output` | +schema |
| **流式失败恢复** | 二次 `ainvoke` | 单一 `error` 事件 | 更快 |
| **笔记位置** | `src/notes/` | `data/notes/` | 更干净 |

---

## 🗺 路线图

完整规划见 [ROADMAP.md](ROADMAP.md)。重点项：

- **RAG 集成**——索引历史报告，为新任务检索相关上下文
- **Human-in-the-loop**——规划后暂停等待用户确认
- **ReAct agent 节点**——让 LLM 动态选择工具
- **PDF / DOCX 导出**——除 Markdown 之外
- **多租户**——按用户的配置、配额、审计日志
- **MCP server**——通过 Model Context Protocol 暴露研究智能体

---

## 🤝 贡献指南

欢迎提 Issue、PR 和 Discussion！工作流见 [CONTRIBUTING.md](CONTRIBUTING.md)。请使用 `.github/ISSUE_TEMPLATE/` 下的 issue 模板。

项目遵循**规范驱动开发（SDD）**——每个功能从 `.comate/specs/` 下的 `doc.md` + `tasks.md` 开始。参考现有 spec 即可。

### 开发环境搭建

```bash
git clone https://github.com/ioranger/DeepResearch-Agent-LangGraph.git
cd DeepResearch-Agent-LangGraph
cd backend && uv sync && cd ..
cd frontend && npm install && cd ..
```

---

## 🔐 安全

见 [SECURITY.md](SECURITY.md)。请私下报告漏洞，不要在公开 issue 中提交。

---

## 📝 许可证

[MIT](LICENSE)——完整文本见该文件。

---

## 🙏 致谢

本项目站在巨人的肩膀上：

- **[LangGraph](https://langchain-ai.github.io/langgraph/)** 与 **[LangChain](https://www.langchain.com/)** —— 状态图编排引擎
- **[open_deep_research](https://github.com/langchain-ai/open_deep_research)** —— 反思循环参考架构
- **[GPT Researcher](https://github.com/assafelovic/gpt-researcher)** —— 引用绑定模式
- **[STORM](https://github.com/stanford-oval/storm)**（斯坦福）—— 分节报告的洞察
- **[Tavily](https://tavily.com/)**、**[Perplexity](https://www.perplexity.ai/)**、**[SearXNG](https://searxng.org/)**、**[DuckDuckGo](https://duckduckgo.com/)** —— 搜索后端
- **[Vue 3](https://vuejs.org/)** 与 **[Vite](https://vitejs.dev/)** —— 前端
- **[Ollama](https://ollama.com/)** 与 **[LMStudio](https://lmstudio.ai/)** —— 本地 LLM 服务

---

<p align="center">
  用 ❤️ 为开源研究社区打造
</p>
