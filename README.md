# DeepResearch on LangGraph

**English** | [简体中文](README.zh-CN.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://img.shields.io/badge/CI-pending-lightgrey.svg)](#)
[![Backend: FastAPI + LangGraph](https://img.shields.io/badge/backend-FastAPI%20%2B%20LangGraph-009688.svg)](#)
[![Frontend: Vue 3 + Vite](https://img.shields.io/badge/frontend-Vue%203%20%2B%20Vite-42b883.svg)](#)

> A fully local-friendly deep research and report-generation assistant built on
> [LangGraph](https://langchain-ai.github.io/langgraph/). Submit a topic, watch
> the agent plan, search across multiple backends in parallel, and stream a
> structured Markdown report to your browser via Server-Sent Events.

---

## ✨ Features

- **LangGraph StateGraph pipeline** — `plan → research → report → persist`,
  with parallel fan-out across sub-tasks.
- **Five search backends** — `duckduckgo`, `tavily`, `perplexity`, `searxng`,
  and `advanced` (fan-out across the other four with per-backend isolation).
- **Local-first LLM** — works with [Ollama](https://ollama.com/) and
  LMStudio out of the box; also supports any OpenAI-compatible endpoint.
- **Streaming UI** — Vue 3 + Vite frontend consumes SSE and shows todo
  progress, sources, and the final report live.
- **Persistent notes** — final reports are written to `backend/notes/`
  as Markdown files with a `notes_index.json` catalog.
- **Quality foundation** — pytest harness, ruff, and CI on every push.

---

## 🏗 Architecture

```
        ┌──────────┐
        │  START   │
        └────┬─────┘
             ▼
        ┌──────────┐
        │  plan    │   LLM decomposes topic into 3–5 sub-tasks
        └────┬─────┘
             ▼
   ┌───── research (Send fan-out, parallel) ─────┐
   │  search  →  stream summary                  │
   │  (tavily / ddg / searxng / perplexity)      │
   └──────────────────┬──────────────────────────┘
                      ▼
                ┌──────────┐
                │  report  │   synthesize structured Markdown
                └────┬─────┘
                     ▼
                ┌──────────┐
                │ persist  │   write to backend/notes/*.md
                └────┬─────┘
                     ▼
                   END
```

Each node emits a typed SSE event; the frontend renders todo progress,
sources, and the final report incrementally.

---

## 🚀 Quick Start

### 1. Clone

```bash
git clone https://github.com/<your-org>/helloagents-deepresearch.git
cd helloagents-deepresearch
```

### 2. Backend

```bash
cd backend
uv sync
cp .env.example .env
# Edit .env — at minimum set LLM_PROVIDER, LLM_MODEL_ID, LLM_BASE_URL,
# and (optionally) TAVILY_API_KEY / PERPLEXITY_API_KEY / SEARXNG_URL.
uv run uvicorn main:app --reload
```

The default `SEARCH_API=duckduckgo` needs **no API key** — you can run a
real end-to-end research loop with only a local LLM configured.

### 3. Frontend

```bash
cd frontend
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

---

## 🧪 Search Backend Matrix

| Backend      | API key required | Local-first | Notes                                          |
|--------------|------------------|-------------|------------------------------------------------|
| `duckduckgo` | No               | Yes         | Default. Good baseline.                        |
| `tavily`     | Yes              | No          | High quality, paid tier.                       |
| `perplexity` | Yes              | No          | Synthesized answers + citations.               |
| `searxng`    | No (self-host)   | Yes         | Defaults to `http://localhost:8888`.           |
| `advanced`   | Mixed            | Mixed       | Fans out across the four above.                |

Set `SEARCH_API` in `.env` to pick the default backend. The frontend exposes
the same five options per request.

---

## ⚙️ Configuration

All runtime settings come from environment variables via
`Configuration.from_env()` in `backend/src/config.py`. See
[`backend/.env.example`](backend/.env.example) for the full list.

Key variables:

| Variable            | Default              | Purpose                                              |
|---------------------|----------------------|------------------------------------------------------|
| `SEARCH_API`        | `duckduckgo`         | Default search backend for the frontend dropdown.    |
| `LLM_PROVIDER`      | `custom`             | `ollama`, `lmstudio`, or any OpenAI-compatible URL.  |
| `LLM_MODEL_ID`      | _(none)_             | Model name passed to the provider.                   |
| `LLM_BASE_URL`      | _(none)_             | Provider endpoint.                                   |
| `LLM_API_KEY`       | _(none)_             | Provider API key (often unused for local).           |
| `LLM_TIMEOUT`       | `60`                 | LLM request timeout in seconds.                      |
| `HOST` / `PORT`     | `0.0.0.0` / `8000`   | FastAPI bind address.                                |
| `CORS_ORIGINS`      | `http://localhost:5173,http://localhost:3000` | Comma-separated allowlist. |
| `LOG_LEVEL`         | `INFO`               | loguru level.                                        |

---

## 🧰 Development

```bash
cd backend
uv run ruff check src tests
uv run pytest                # 8 passed
```

The integration test under `tests/integration/test_api.py` exercises the SSE
protocol end-to-end with the LLM and search layers monkeypatched, so it
runs offline in under a second.

Pre-commit hooks:

```bash
./scripts/install_hooks.sh
```

---

## 🗺 Roadmap

See [ROADMAP.md](ROADMAP.md) for what's next. Highlights:

- Concurrent backend fan-out in `advanced` search.
- ReAct agent node so the LLM can pick `note_tool` / `search_tool`.
- Locale-aware prompts (English / 中文 / 日本語).
- Stable HTTP runtime API for IDE / web embedding.

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues, PRs, and Discussions are
welcome. Use the issue templates under `.github/ISSUE_TEMPLATE/`.

## 🔐 Security

See [SECURITY.md](SECURITY.md). Please report vulnerabilities privately
rather than via public issues.

## 📝 License

[MIT](LICENSE) — see the file for full text.

## 🙏 Acknowledgements

- [LangGraph](https://langchain-ai.github.io/langgraph/) and the
  [LangChain](https://www.langchain.com/) ecosystem.
- [Tavily](https://tavily.com/), [Perplexity](https://www.perplexity.ai/),
  [SearXNG](https://searxng.org/), and [DuckDuckGo](https://duckduckgo.com/).
- [Vue 3](https://vuejs.org/) and [Vite](https://vitejs.dev/).
