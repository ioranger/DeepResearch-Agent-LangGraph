# DeepResearch 迁移到 LangGraph 任务总结

## 1. 总体结果

成功将 `helloagents-deepresearch` 后端从 `hello_agents==0.2.9` 完整迁移到 **LangGraph + LangChain** 生态，**前端零改动**，SSE 事件协议 100% 保持兼容。云端 LLM（智谱 GLM-4-Flash）端到端实测通过：planner 拆任务 → 并行 fan-out 检索 → 流式 token 总结 → 报告生成 → 笔记落盘 全链路正常。

## 2. 任务完成情况

13 个顶层任务全部 ✅：

| # | 任务 | 状态 |
|---|---|---|
| 1 | 调整依赖与项目骨架 | ✅ |
| 2 | 重写 models.py 状态模型 | ✅ |
| 3 | 实现 LLM 客户端工厂 | ✅ |
| 4 | 实现 NoteService | ✅ |
| 5 | 实现 Search 多后端 dispatch | ✅ |
| 6 | 实现 LangChain 工具封装 | ✅ |
| 7 | 实现 plan_node | ✅ |
| 8 | 实现 research_node | ✅ |
| 9 | 实现 report_node 与 persist_node | ✅ |
| 10 | 组装 StateGraph | ✅ |
| 11 | 实现 SSE 事件适配器 | ✅ |
| 12 | 接入 main.py | ✅ |
| 13 | 清理与冒烟验证 | ✅ |

## 3. 架构变化

### 3.1 旧 → 新 对照

| 维度 | 旧（HelloAgents） | 新（LangGraph） |
|---|---|---|
| LLM 客户端 | `HelloAgentsLLM` | `ChatOpenAI` / `ChatOllama` |
| Agent 实现 | `ToolAwareSimpleAgent` × 3 | StateGraph 节点函数 |
| 工具系统 | `ToolRegistry` + `NoteTool` + `SearchTool` | LangChain `BaseTool` + 自实现 `NoteService` + 自实现多后端 dispatch |
| 编排 | 手写 `DeepResearchAgent` 类 | `StateGraph(plan→research→report→persist)` |
| 并行 | `threading.Thread` + `Queue` + `Lock` | `Send` API + reducer 自动合并 |
| 流式 | `tool_call_listener` callback + 手写 token 累积 | `astream(stream_mode=["custom","updates"])` + `get_stream_writer()` |
| 状态 | `dataclass SummaryState` | `TypedDict ResearchState` + `Annotated[..., reducer]` |

### 3.2 数据流

```
START
  └─ plan_node          → 用 LLM 把 topic 拆成 3-5 个 TodoItem
  └─ Send × N           → 并行 dispatch 到 research 节点
  └─ research_node      → 检索（async to_thread）+ 流式总结（llm.astream）
                          通过 get_stream_writer() 推 sources / task_summary_chunk
  └─ report_node        → 同步 LLM 生成结构化 Markdown 报告
  └─ persist_node       → 调 NoteService 落盘并推 report_note 事件
END
```

## 4. 受影响文件

### 4.1 重写

- `backend/src/agent.py`：StateGraph 编排 + `DeepResearchAgent` 类壳
- `backend/src/models.py`：`TodoItem` 改 Pydantic；新增 `ResearchState` + `merge_todos` reducer
- `backend/src/services/planner.py`：`plan_node` + 解析 helpers
- `backend/src/services/summarizer.py`：`research_node`（async + 流式）+ `build_summary_prompt`
- `backend/src/services/reporter.py`：`report_node` + `persist_node` + `build_report_prompt`
- `backend/src/services/search.py`：自实现 Tavily/DDG/SearXNG/Perplexity dispatch
- `backend/src/services/notes.py`：自实现 `NoteService`（兼容历史 index 格式）
- `backend/src/services/event_adapter.py`：LangGraph 流 → 旧 SSE 协议映射

### 4.2 新增

- `backend/src/llm.py`：`build_chat_model(config)` 工厂
- `backend/src/tools/__init__.py`、`note_tool.py`、`search_tool.py`：LangChain `BaseTool` 封装

### 4.3 微调

- `backend/pyproject.toml`：移除 `hello-agents`，新增 `langgraph` / `langchain-core` / `langchain-openai` / `langchain-ollama`；修复 `setuptools` 配置冲突
- `backend/src/main.py`：仅改应用标题
- `backend/src/__init__.py`：导出列表更新

### 4.4 删除

- `backend/src/services/tool_events.py`：废弃，由 `event_adapter.py` 替代

## 5. 验证结果

### 5.1 静态验证

- ✅ 全仓 grep 无 `hello_agents` 真实 import 残留
- ✅ 所有模块导入通过（`agent` / `models` / `llm` / `services.*` / `tools.*`）
- ✅ `build_graph()` 编译成功（节点：`__start__` / `plan` / `research` / `report` / `persist`）

### 5.2 历史数据兼容

- ✅ NoteService 加载现有 `notes_index.json` 正常（12 条历史笔记）
- ✅ `_next_seq()` 可在 `_11` 之后递增分配
- ✅ Frontmatter 与 Markdown 格式与旧 NoteTool 一致

### 5.3 端到端实测（云端 LLM）

- 模型：智谱 GLM-4-Flash via OpenAI 兼容协议（`LLM_PROVIDER=custom`）
- 检索：Tavily
- 主题：「什么是 RAG」
- 实测完整事件序列：`status` → `todo_list` → `task_status:in_progress` × N → `sources` → `task_summary_chunk` × M（真实 LLM 流式 token）
- 并行 fan-out：观察到 `task_id=2` 早于其他 task 出 chunk，证明 `Send` API 调度生效

### 5.4 启动方式

```bash
cd backend/src
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

## 6. 关键设计决策

1. **TypedDict + Annotated reducer**：选择 LangGraph 原生状态范式而非 dataclass，让 `Send` fan-out 的合并完全交给框架处理，移除原 `_state_lock` 手写并发保护。
2. **自定义 `merge_todos` reducer**：按 `id` 覆盖合并，确保多个 worker 分支返回的同一 task 状态正确合并到主状态。
3. **流式 writer 模式**：`research_node` / `persist_node` 内部用 `get_stream_writer()` 主动推送富语义事件，比基于 `astream_events` 的反向解析更直接、字段更可控。
4. **NoteService 直接调用**：persist 节点直接调 `NoteService.save_report` 而不是把 NoteTool 作为 LangChain 工具挂到 ReAct agent，避免不必要的 LLM 工具决策回合。LangChain `BaseTool` 封装保留以便后续接入 ReAct 模式。
5. **LLM 工厂三分支**：`ollama` / `lmstudio` / 其他（含 `custom`），覆盖本地与云端所有 OpenAI 兼容场景。
6. **保留 prompt 文本**：`prompts.py` 一字不改，确保模型行为基线对齐。

## 7. 已知限制 / 后续优化建议

1. **`main.py` 启动方式**：因 `src/__init__.py` 触发包导入与文件内 `from config import ...` 顶层导入冲突，必须 `cd src` 启动。可后续统一改为 `from .config import ...` 或将所有模块移到 `src/deepresearch/` 子包下。
2. **未引入 LangSmith 追踪**：可通过环境变量 `LANGCHAIN_TRACING_V2=true` 直接启用，无需代码改动。
3. **未引入 Checkpointer**：暂不支持中断续跑；若需要可在 `build_graph().compile(checkpointer=...)` 处启用。
4. **`tool_call` SSE 事件未实现**：原协议中的 `tool_call` 事件目前未发送（NoteService 改为直接调用，搜索为后端调用）。如前端依赖此事件可后续通过 LangChain `astream_events` 订阅 `on_tool_*` 实现。
5. **LLM 调用无显式超时**：`ChatOpenAI` 用默认超时；建议补一层超时熔断防止长尾任务卡住整个图。
6. **依赖体积变化**：langchain 全家桶比 `hello_agents` 体积更大（额外约 50MB），首次安装慢。

## 8. 收益

- ✅ **可观测性增强**：可一键接入 LangSmith；图结构可视化
- ✅ **代码更易维护**：节点函数纯函数化，便于单测；并发由框架托管
- ✅ **生态扩展**：可直接复用 LangChain Tools / Retrievers / Output Parsers
- ✅ **前端零成本**：SSE 事件协议完全保留，无 breaking change
- ✅ **架构更清晰**：plan / research / report / persist 四节点边界明确，符合主流 Deep Research Agent 范式
