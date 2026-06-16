# DeepResearch on LangGraph

**A production-grade deep-research agent that plans, searches, reflects, cites, and reports — fully streamed to your browser.**

[简体中文](README.zh-CN.md) | **English**

<p align="left">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="#"><img src="https://img.shields.io/badge/Backend-FastAPI%20%2B%20LangGraph-009688?logo=fastapi&logoColor=white" alt="Backend"></a>
  <a href="#"><img src="https://img.shields.io/badge/Frontend-Vue%203%20%2B%20Vite-42b883?logo=vuedotjs&logoColor=white" alt="Frontend"></a>
  <a href="#"><img src="https://img.shields.io/badge/Tests-34%20passed%20%E2%9C%93-brightgreen" alt="Tests"></a>
  <a href="#"><img src="https://img.shields.io/badge/Warnings-0-success" alt="Warnings"></a>
</p>

> **Submit a topic → watch the agent decompose it into sub-tasks → search across multiple
> backends in parallel → reflect on what's missing → synthesize a citation-bound Markdown
> report → streamed to your browser in real time via Server-Sent Events.**

---

## 📑 Table of Contents

- [Why DeepResearch?](#-why-deepresearch)
- [Key Features](#-key-features)
- [Demo Screenshots](#-demo-screenshots)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [Configuration Reference](#-configuration-reference)
- [Search Backend Matrix](#-search-backend-matrix)
- [API Reference](#-api-reference)
- [SSE Event Protocol](#-sse-event-protocol)
- [Development Workflow](#-development-workflow)
- [Testing](#-testing)
- [Performance & Quality Comparison](#-performance--quality-comparison)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [Security](#-security)
- [License](#-license)
- [Acknowledgements](#-acknowledgements)

---

## 🌟 Why DeepResearch?

Most research assistants are **shallow** (one round of search → one summary) and
**unsourced** (no way to verify claims). DeepResearch fixes both by adopting the
patterns that made the best open-source research agents successful:

| Pattern | Source | DeepResearch |
|---|---|---|
| **Reflection loop** — re-search when info is insufficient | `open_deep_research` (LangChain) | ✅ `iterative_research` |
| **Citation binding** — inline `[n]` + References list | `GPT Researcher` | ✅ Numbered sources + References section |
| **Structured planning** — JSON schema for tasks | `open_deep_research` | ✅ `with_structured_output(TaskPlan)` |
| **Section-by-section reports** — avoid one-shot LLM degradation | `GPT Researcher` | ✅ Per-section LLM + assembly |
| **Parallel fan-out** — sub-tasks run concurrently | LangGraph `Send` | ✅ Native LangGraph `Send` API |

The result is a **deeper, more credible, more inspectable** research experience —
with **34 tests passing** and **0 deprecation warnings**.

---

## ✨ Key Features

### 🔬 Research Quality
- **Reflection Loop** — Each sub-task goes `search → summarize → reflect → (re-search if insufficient)`, capped by `MAX_WEB_RESEARCH_LOOPS`. The agent asks itself: *"Is this information sufficient? What's still missing?"* and continues with a follow-up query.
- **Citation Binding** — Every source is numbered `[1] [2] [3]`; summaries force-anchor claims with `[n]`; the final report appends a deduplicated `## 参考来源` section.
- **Structured Planning** — `with_structured_output(TaskPlan)` guarantees valid JSON; falls back to manual regex parsing if the LLM provider doesn't support it.
- **Snippet Filtering** — Lightweight keyword-overlap scoring trims long result lists to the top-K most relevant snippets, reducing prompt noise and token cost.
- **Section-by-Section Reports** — Each task gets its own `## {title}` section, then an LLM stitches them into a coherent whole — avoiding the quality cliff of single-shot long prompts.

### 🏎 Architecture & Performance
- **True Async Streaming** — `/research/stream` is `async def`, sharing the FastAPI event loop instead of forking a private one per request.
- **Lifespan over `on_event`** — Modern `asynccontextmanager lifespan` replaces the deprecated `@app.on_event("startup")`.
- **Configuration Singleton** — `Configuration.from_env()` is called **once** at app boot (down from 4x), eliminating config drift.
- **No Secondary Invocation on Failure** — Stream failures no longer trigger a `graph.ainvoke()` retry; they emit a typed `error` event and close.
- **Lightweight Logger** — One stderr sink instead of duplicate INFO+ERROR sinks, level controlled by `LOG_LEVEL`.

### 🧰 Engineering
- **LangGraph StateGraph** — `plan → research (parallel) → report → persist` with `Send` fan-out and reducer-based state merging.
- **Pydantic v2 Configuration** — Type-safe, environment-driven, validator-enforced (`CORS_ORIGINS` parses comma-separated env values).
- **34 Pytest Cases** — Unit tests for config / models / search / planner / reporter / researcher + integration tests for the SSE protocol.
- **Zero Deprecation Warnings** — All `@app.on_event` calls migrated; FastAPI logs are clean.

### 🎨 Frontend
- **App.vue: 2304 → 56 lines** — A 98% reduction via structural refactor.
- **Composable Logic** — `useResearchStream.ts` (716 lines) encapsulates SSE connection, state machine, and event dispatch.
- **4 Reusable Components** — `TopicInput` / `TaskList` / `SourcePanel` / `ReportView`.
- **Global Stylesheet** — 1308 lines of CSS extracted to `style-extracted.css` for reuse.

### 🔌 Integration
- **5 Search Backends** — `duckduckgo` (no key), `tavily` (paid), `perplexity` (synthesized answers), `searxng` (self-hosted), `advanced` (fan-out aggregator with per-backend isolation).
- **3 LLM Providers** — `ollama`, `lmstudio`, and any OpenAI-compatible endpoint.
- **Persistent Notes** — Reports and task notes are saved as Markdown with a `notes_index.json` catalog in `backend/data/notes/`.

---

## 🎬 Demo Screenshots

> Run `cd frontend && npm run dev` and visit <http://localhost:5173> to see it live.

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

## 🏗 Architecture

### Pipeline Overview

```
        ┌──────────┐
        │  START   │   user submits a topic
        └────┬─────┘
             ▼
        ┌──────────┐
        │  plan    │   with_structured_output(TaskPlan)
        └────┬─────┘   decomposes topic into 3–5 sub-tasks
             ▼
   ┌───── research (Send fan-out, parallel) ─────┐
   │  loop up to MAX_WEB_RESEARCH_LOOPS:        │
   │    ① search  →  [n]-numbered sources      │
   │    ② stream summary (citations required)   │
   │    ③ reflect → is_sufficient?             │
   │    ④ if not: re-search with follow-up      │
   └──────────────────┬──────────────────────────┘
                      ▼
                ┌──────────┐
                │  report  │   per-section LLM + assembly
                └────┬─────┘  + append `## 参考来源`
                     ▼
                ┌──────────┐
                │ persist  │   write to backend/data/notes/
                └────┬─────┘
                     ▼
                   END
```

### Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Orchestration** | LangGraph `StateGraph` | State machine with `Send` fan-out + reducer merging |
| **Backend** | FastAPI + uvicorn | Async HTTP + SSE streaming |
| **LLM Abstraction** | LangChain `ChatModel` | Pluggable providers (Ollama / LMStudio / OpenAI-compatible) |
| **Search** | Tavily / DDG / Perplexity / SearXNG | Multi-backend dispatch with per-backend isolation |
| **Config** | Pydantic v2 + `python-dotenv` | Type-safe env-driven configuration |
| **Logging** | loguru | Single-sink structured logs |
| **Frontend** | Vue 3 + Vite + TypeScript | Composition API + composable for SSE state |
| **Testing** | pytest + pytest-asyncio | 34 tests, integration + unit |
| **Notes** | Markdown + JSON index | Human-readable, git-friendly persistence |

---

## 📁 Project Structure

```
helloagents-deepresearch/
├── backend/
│   ├── src/
│   │   ├── main.py                # FastAPI entry (async endpoints + lifespan)
│   │   ├── agent.py               # DeepResearchAgent (arun / astream / run)
│   │   ├── config.py              # Pydantic Configuration (env-driven)
│   │   ├── models.py              # State models (TodoItem, TaskPlan, …)
│   │   ├── prompts.py             # Localized prompts (zh-CN / en-US)
│   │   ├── llm.py                 # LLM factory
│   │   ├── services/
│   │   │   ├── researcher.py      # ★ Reflection loop (iterative_research)
│   │   │   ├── planner.py         # ★ with_structured_output(TaskPlan)
│   │   │   ├── summarizer.py      # research_node thin shell
│   │   │   ├── reporter.py        # ★ section-by-section generation
│   │   │   ├── search.py          # multi-backend dispatch + citation
│   │   │   ├── event_adapter.py   # SSE event protocol mapper
│   │   │   ├── text_processing.py # ★ snippet relevance filter
│   │   │   └── notes.py           # persistent Markdown notes
│   │   └── tools/                 # tool adapters (search_tool, note_tool)
│   ├── data/notes/                # ★ persistent notes (outside src/)
│   ├── tests/
│   │   ├── unit/                  # 32 unit tests
│   │   └── integration/           # 2 SSE protocol tests
│   ├── pyproject.toml             # uv-managed deps + tool config
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.vue                # ★ 56 lines (thin shell)
│   │   ├── composables/
│   │   │   └── useResearchStream.ts  # ★ SSE state machine
│   │   ├── components/            # ★ 4 components
│   │   │   ├── TopicInput.vue
│   │   │   ├── TaskList.vue
│   │   │   ├── SourcePanel.vue
│   │   │   └── ReportView.vue
│   │   ├── services/api.ts        # SSE client
│   │   ├── style.css              # global styles
│   │   ├── style-extracted.css    # ★ extracted from App.vue
│   │   └── main.ts
│   └── package.json
├── .comate/specs/                 # SDD spec artifacts
│   ├── quality-foundation-harness/
│   ├── opensource-benchmark-upgrade/
│   └── architecture-optimization/
├── docker-compose.yml
├── README.md                      # ← you are here
└── LICENSE
```

★ = added or significantly refactored in the recent upgrade wave

---

## 🚀 Quick Start

### Prerequisites

- **Python ≥ 3.10** (project is uv-managed)
- **Node.js ≥ 18** (for the frontend)
- **uv** (recommended): `brew install uv` or see [astral-sh/uv](https://github.com/astral-sh/uv)
- A local LLM endpoint (Ollama / LMStudio) **or** an OpenAI-compatible API key

### 1. Clone

```bash
git clone https://github.com/ioranger/DeepResearch-Agent-LangGraph.git
cd DeepResearch-Agent-LangGraph
```

### 2. Backend

```bash
cd backend
uv sync                          # install all deps
cp .env.example .env             # copy config template
```

Edit `.env` and set at minimum:

```env
LLM_PROVIDER=ollama              # or "lmstudio" / "custom"
LLM_MODEL_ID=qwen2.5:7b          # any model your provider supports
LLM_BASE_URL=http://localhost:11434
SEARCH_API=duckduckgo            # default — needs no API key
```

Then start the server:

```bash
uv run uvicorn main:app --reload
```

> The default `SEARCH_API=duckduckgo` needs **no API key**, so you can run a real
> end-to-end research loop with only a local LLM configured.

### 3. Frontend

```bash
cd ../frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

### 4. Or run everything in Docker

```bash
# Backend + frontend only
docker compose up --build

# Backend + frontend + local Ollama profile
docker compose --profile ollama up --build
```

The Ollama profile is opt-in so the default stack stays small.

### 5. Verify

```bash
curl http://localhost:8000/healthz
# → {"status": "ok"}
```

---

## ⚙️ Configuration Reference

All runtime settings come from environment variables via `Configuration.from_env()`
in `backend/src/config.py`. See [`backend/.env.example`](backend/.env.example) for
the full list.

### Core

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `custom` | `ollama` / `lmstudio` / `custom` (OpenAI-compatible) |
| `LLM_MODEL_ID` | _(none)_ | Model name passed to the provider |
| `LLM_BASE_URL` | _(none)_ | Provider endpoint (e.g. `http://localhost:11434`) |
| `LLM_API_KEY` | _(none)_ | API key (often unused for local) |
| `LLM_TIMEOUT` | `60` | LLM request timeout (seconds) |
| `LOCALE` | `zh-CN` | Agent output locale: `zh-CN` or `en-US` |

### Search

| Variable | Default | Purpose |
|---|---|---|
| `SEARCH_API` | `duckduckgo` | Default search backend |
| `TAVILY_API_KEY` | _(none)_ | Required for `tavily` backend |
| `PERPLEXITY_API_KEY` | _(none)_ | Required for `perplexity` backend |
| `SEARXNG_URL` | `http://localhost:8888` | Required for `searxng` backend |

### Research

| Variable | Default | Purpose |
|---|---|---|
| `MAX_WEB_RESEARCH_LOOPS` | `2` | Max reflection iterations per sub-task |
| `FETCH_FULL_PAGE` | `True` | Include full page content in search results |
| `USE_TOOL_CALLING` | `True` | Enable structured tool calls |
| `STRIP_THINKING_TOKENS` | `False` | Strip `<think>…</think>` from LLM output |

### Server

| Variable | Default | Purpose |
|---|---|---|
| `HOST` | `0.0.0.0` | FastAPI bind address |
| `PORT` | `8000` | FastAPI port |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated allowlist |
| `LOG_LEVEL` | `INFO` | loguru level |

### Notes

| Variable | Default | Purpose |
|---|---|---|
| `ENABLE_NOTES` | `True` | Persist task progress to `NoteService` |
| `NOTES_WORKSPACE` | `backend/data/notes` | Directory for note persistence |

---

## 🔍 Search Backend Matrix

| Backend | API Key | Local-First | Best For |
|---|---|---|---|
| `duckduckgo` | ❌ | ✅ | Default. Zero-config, solid baseline. |
| `tavily` | ✅ | ❌ | High-quality results, paid tier. |
| `perplexity` | ✅ | ❌ | Synthesized answers with citations. |
| `searxng` | ❌ (self-host) | ✅ | Privacy-focused, defaults to `http://localhost:8888`. |
| `advanced` | mixed | mixed | **Fan-out aggregator**: runs all 4 backends concurrently, aggregates results, isolates per-backend failures. |

The frontend exposes the same five options per request; the backend also respects
`SEARCH_API` as the default.

---

## 🔌 API Reference

### `GET /healthz`

Liveness probe.

```bash
curl http://localhost:8000/healthz
# → {"status": "ok"}
```

### `POST /research`

Run a research pipeline synchronously, return the final report.

```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "多模态模型在 2025 年的关键突破",
    "search_api": "duckduckgo"
  }'
```

**Response** (truncated):

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

Run with real-time Server-Sent Events.

```bash
curl -N -X POST http://localhost:8000/research/stream \
  -H "Content-Type: application/json" \
  -d '{"topic": "量子计算 2025 进展"}'
```

---

## 📡 SSE Event Protocol

Events sent by `/research/stream` (one JSON object per `data:` line):

| `type` | Payload | When |
|---|---|---|
| `status` | `{message, task_id?}` | Status updates (e.g. "初始化研究流程") |
| `todo_list` | `{tasks: [...], step}` | After planner completes |
| `task_status` | `{task_id, status, title, intent, summary?, sources_summary?, step?}` | Per task state change |
| `task_reflection` | `{task_id, is_sufficient, follow_up_query, reasoning, current_loop, max_loops}` | **★ After each reflection pass** |
| `sources` | `{task_id, latest_sources: [{id, title, url, snippet}], backend, ...}` | **★ Structured source list (was raw text)** |
| `task_summary_chunk` | `{task_id, content, note_id}` | Streaming summary tokens |
| `report_note` | `{note_id, title, content, note_path}` | When report is persisted |
| `final_report` | `{report, note_id, note_path}` | At the end of the pipeline |
| `error` | `{code, detail}` | On failure (replaces silent retries) |
| `done` | `{}` | Stream terminator (always emitted) |

★ = new in recent upgrade wave

---

## 🛠 Development Workflow

### Linting & Formatting

```bash
cd backend
uv run ruff check src tests
uv run ruff format src tests
```

### Pre-commit Hooks

```bash
./scripts/install_hooks.sh
```

### Adding a New Search Backend

1. Add a `_search_<name>(query, config)` function in `services/search.py`.
2. Register it in the `handlers` dict inside `dispatch_search`.
3. (Optional) Add to `advanced`'s fan-out list.

### Adding a New LLM Provider

1. Add a `build_<provider>_chat_model(cfg)` in `llm.py`.
2. Update `llm_provider` choices in `config.py`.

### Adding a New Reflection Iteration Behavior

1. Edit `services/researcher.py` — the loop is self-contained.
2. Adjust the `_reflect` prompt in `prompts.py` for new evaluation criteria.

---

## ✅ Testing

```bash
cd backend
uv run pytest                 # 34 passed
uv run pytest -v              # verbose
uv run pytest --tb=short      # short tracebacks
```

### Test Layout

```
backend/tests/
├── unit/
│   ├── test_config.py         # env parsing, overrides
│   ├── test_models.py         # TodoItem, merge_todos
│   ├── test_planner.py        # ★ structured output + fallback
│   ├── test_prompts.py        # zh-CN / en-US localization
│   ├── test_reporter.py       # ★ References section
│   ├── test_researcher.py     # ★ reflection parsing
│   ├── test_search.py         # ★ citation-aware context
│   └── ...
└── integration/
    └── test_api.py            # /healthz + /research/stream SSE
```

★ = added in the recent upgrade wave

The integration tests mock the LLM and search layers via `monkeypatch`,
so the whole suite runs in **< 5 seconds** offline.

---

## 📊 Performance & Quality Comparison

| Metric | Before Upgrade | After Upgrade | Change |
|---|---|---|---|
| **Test count** | 0 | 34 | +34 |
| **Pytest warnings** | 6 (on_event) | 0 | −6 |
| **App.vue lines** | 2304 | 56 | **−98%** |
| **`Configuration.from_env()` calls per request** | 4 | 1 | −75% |
| **Search backend isolation** | silent fallback | per-backend try/except | improved |
| **Reflection loops** | 0 (single-pass) | up to N | +reflection |
| **Citation binding** | raw sources list | `[n]` inline + References | +citations |
| **Planner parse stability** | regex on text | `with_structured_output` | +schema |
| **Stream failure recovery** | secondary `ainvoke` | single `error` event | faster |
| **Notes location** | `src/notes/` | `data/notes/` | cleaner tree |

---

## 🗺 Roadmap

See [ROADMAP.md](ROADMAP.md) for the full picture. Highlights:

- **RAG integration** — Index past reports, retrieve related context for new tasks
- **Human-in-the-loop** — Pause after planning for user confirmation
- **ReAct agent node** — Let the LLM pick tools dynamically
- **PDF / DOCX export** — Beyond Markdown
- **Multi-tenant** — Per-user config, quotas, audit log
- **MCP server** — Expose the research agent over Model Context Protocol

---

## 🤝 Contributing

We welcome issues, PRs, and Discussions! See [CONTRIBUTING.md](CONTRIBUTING.md) for
the workflow. Use the issue templates under `.github/ISSUE_TEMPLATE/`.

The project follows **Spec-Driven Development** — every feature starts with a
`doc.md` + `tasks.md` in `.comate/specs/`. See existing specs for examples.

### Development Setup

```bash
git clone https://github.com/ioranger/DeepResearch-Agent-LangGraph.git
cd DeepResearch-Agent-LangGraph
cd backend && uv sync && cd ..
cd frontend && npm install && cd ..
```

---

## 🔐 Security

See [SECURITY.md](SECURITY.md). Please report vulnerabilities privately
rather than via public issues.

---

## 📝 License

[MIT](LICENSE) — see the file for full text.

---

## 🙏 Acknowledgements

This project stands on the shoulders of giants:

- **[LangGraph](https://langchain-ai.github.io/langgraph/)** & **[LangChain](https://www.langchain.com/)** — The state-graph orchestration engine
- **[open_deep_research](https://github.com/langchain-ai/open_deep_research)** — Reference architecture for reflection loops
- **[GPT Researcher](https://github.com/assafelovic/gpt-researcher)** — Citation binding patterns
- **[STORM](https://github.com/stanford-oval/storm)** (Stanford) — Section-by-section generation insights
- **[Tavily](https://tavily.com/)**, **[Perplexity](https://www.perplexity.ai/)**, **[SearXNG](https://searxng.org/)**, **[DuckDuckGo](https://duckduckgo.com/)** — Search backends
- **[Vue 3](https://vuejs.org/)** & **[Vite](https://vitejs.dev/)** — Frontend
- **[Ollama](https://ollama.com/)** & **[LMStudio](https://lmstudio.ai/)** — Local LLM serving

---

<p align="center">
  Made with ❤️ for the open-source research community
</p>
