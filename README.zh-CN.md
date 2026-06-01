# DeepResearch on LangGraph（中文）

[English](README.md) | **简体中文**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://img.shields.io/badge/CI-pending-lightgrey.svg)](#)
[![Backend: FastAPI + LangGraph](https://img.shields.io/badge/backend-FastAPI%20%2B%20LangGraph-009688.svg)](#)
[![Frontend: Vue 3 + Vite](https://img.shields.io/badge/frontend-Vue%203%20%2B%20Vite-42b883.svg)](#)

> 基于 [LangGraph](https://langchain-ai.github.io/langgraph/) 的全本地可运行深度研究与报告生成助手。提交一个主题，看 Agent 拆题、并行多后端搜索，并通过 Server-Sent Events 流式输出一份结构化的 Markdown 报告。

---

## ✨ 特性

- **LangGraph StateGraph 流水线** — `plan → research → report → persist`，子任务并行扇出。
- **五种搜索后端** — `duckduckgo`、`tavily`、`perplexity`、`searxng`，以及 `advanced`（在上述四种之间扇出，单后端异常隔离）。
- **本地优先的 LLM** — 开箱即用支持 [Ollama](https://ollama.com/) 和 LMStudio，也兼容任何 OpenAI-compatible 接口。
- **流式 UI** — Vue 3 + Vite 前端通过 SSE 消费事件，实时展示 todo 进度、来源与最终报告。
- **持久化笔记** — 最终报告以 Markdown 文件落到 `backend/notes/`，并维护 `notes_index.json` 索引。
- **质量基座** — pytest 测试套件、ruff lint、每次 push 自动跑 CI。

---

## 🏗 架构

```
        ┌──────────┐
        │  START   │
        └────┬─────┘
             ▼
        ┌──────────┐
        │  plan    │   LLM 把主题拆成 3–5 个子任务
        └────┬─────┘
             ▼
   ┌───── research (Send 扇出，并行) ─────┐
   │  search  →  流式摘要                  │
   │  (tavily / ddg / searxng / perplexity) │
   └──────────────────┬──────────────────┘
                      ▼
                ┌──────────┐
                │  report  │   合成结构化 Markdown
                └────┬─────┘
                     ▼
                ┌──────────┐
                │ persist  │   写入 backend/notes/*.md
                └────┬─────┘
                     ▼
                   END
```

每个节点都会发出一类带类型的 SSE 事件，前端据此增量渲染 todo 进度、来源、最终报告。

---

## 🚀 快速开始

### 1. 克隆

```bash
git clone https://github.com/ioranger/DeepResearch-Agent-LangGraph.git
cd DeepResearch-Agent-LangGraph
```

### 2. 后端

```bash
cd backend
uv sync
cp .env.example .env
# 编辑 .env，至少设置 LLM_PROVIDER、LLM_MODEL_ID、LLM_BASE_URL，
# 可选设置 TAVILY_API_KEY / PERPLEXITY_API_KEY / SEARXNG_URL
uv run uvicorn main:app --reload
```

默认 `SEARCH_API=duckduckgo` **不需要任何 API Key** —— 只要本地 LLM 配好，就能跑通完整的端到端研究流程。

### 3. 前端

```bash
cd frontend
npm install
npm run dev
```

打开 <http://localhost:5173>。

### 4. 或用 Docker 一键起

```bash
# 仅 backend + frontend
docker compose up --build

# backend + frontend + 本地 Ollama
docker compose --profile ollama up --build
```

Ollama 用 profile 控制，默认 stack 保持精简。

---

## 🧪 搜索后端矩阵

| 后端          | 是否需要 API Key | 是否本地优先 | 说明                                          |
|--------------|------------------|-------------|------------------------------------------------|
| `duckduckgo` | 否               | 是          | 默认。基础够用。                              |
| `tavily`     | 是               | 否          | 高质量、有付费档位。                          |
| `perplexity` | 是               | 否          | 合成式回答 + 引用。                            |
| `searxng`    | 否（自托管）     | 是          | 默认 `http://localhost:8888`。                |
| `advanced`   | 混合             | 混合        | 在上述四种之间扇出，结果聚合。                |

通过 `.env` 中的 `SEARCH_API` 选择默认后端，前端下拉框提供同样的五种选项。

---

## ⚙️ 配置

所有运行时设置都通过 `backend/src/config.py` 中的 `Configuration.from_env()` 读取。完整列表见 [`backend/.env.example`](backend/.env.example)。

关键变量：

| 变量                | 默认值                                     | 用途                                              |
|---------------------|---------------------------------------------|----------------------------------------------------|
| `SEARCH_API`        | `duckduckgo`                                | 前端下拉框的默认搜索后端。                          |
| `LLM_PROVIDER`      | `custom`                                    | `ollama`、`lmstudio` 或任意 OpenAI 兼容 URL。       |
| `LLM_MODEL_ID`      | _(空)_                                      | 传给提供方的模型名。                                |
| `LLM_BASE_URL`      | _(空)_                                      | 提供方接口地址。                                    |
| `LLM_API_KEY`       | _(空)_                                      | 提供方 API Key（本地模型通常不用）。                |
| `LLM_TIMEOUT`       | `60`                                        | LLM 请求超时（秒）。                                |
| `HOST` / `PORT`     | `0.0.0.0` / `8000`                          | FastAPI 绑定地址。                                  |
| `CORS_ORIGINS`      | `http://localhost:5173,http://localhost:3000` | 逗号分隔的 origin 白名单。                        |
| `LOG_LEVEL`         | `INFO`                                      | loguru 日志级别。                                   |

---

## 🧰 开发

```bash
cd backend
uv run ruff check src tests
uv run pytest                # 8 passed
```

`tests/integration/test_api.py` 中的集成测试覆盖 SSE 协议端到端，LLM 与搜索层均通过 monkeypatch 替换，因此无需真实 API Key 即可在不到一秒内完成验证。

pre-commit 钩子：

```bash
./scripts/install_hooks.sh
```

---

## 🗺 路线图

详见 [ROADMAP.md](ROADMAP.md)。重点：

- `advanced` 搜索后端并发扇出。
- ReAct agent 节点，让 LLM 自主选择 `note_tool` / `search_tool`。
- 提示词本地化（English / 中文 / 日本語）。
- 稳定版 HTTP Runtime API，便于嵌入 IDE 和 Web。

---

## 🤝 贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。欢迎提 issue、PR 和 Discussion。使用 `.github/ISSUE_TEMPLATE/` 下的模板。

## 🔐 安全

见 [SECURITY.md](SECURITY.md)。请私下报告漏洞，不要在公开 issue 中提。

## 📝 许可证

[MIT](LICENSE)。

## 🙏 致谢

- [LangGraph](https://langchain-ai.github.io/langgraph/) 和 [LangChain](https://www.langchain.com/) 生态。
- [Tavily](https://tavily.com/)、[Perplexity](https://www.perplexity.ai/)、[SearXNG](https://searxng.org/)、[DuckDuckGo](https://duckduckgo.com/)。
- [Vue 3](https://vuejs.org/) 和 [Vite](https://vitejs.dev/)。
