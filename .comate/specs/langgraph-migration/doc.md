# DeepResearch 迁移到 LangGraph 设计文档

## 1. 目标与范围

将 `helloagents-deepresearch` 后端从 `hello_agents` 框架完整迁移到 **LangGraph + LangChain** 生态：

- **替换**：`HelloAgentsLLM` / `ToolAwareSimpleAgent` / `ToolRegistry` / `NoteTool` / `SearchTool` / `tool_call_listener` 全部移除。
- **采用**：`langgraph.graph.StateGraph` + `langchain_core` 消息体系 + `langchain_openai` / `langchain_ollama` LLM 客户端 + LangChain `BaseTool` / 直接 SDK 调搜索 + 自实现 NoteService。
- **保留**：FastAPI 入口、SSE 事件协议（前端零改动）、Notes 文件落盘格式、Prompt 文本内容、`Configuration` 字段、并行执行语义。
- **代码组织**：原地重写 `backend/src/`，删除 `hello_agents` 依赖。

## 2. 整体架构

### 2.1 旧架构（HelloAgents）

```
DeepResearchAgent (orchestrator)
  ├─ HelloAgentsLLM (统一 LLM 客户端)
  ├─ ToolAwareSimpleAgent × 3 (planner / reporter / summarizer factory)
  ├─ ToolRegistry + NoteTool + SearchTool
  ├─ ToolCallTracker (tool_call_listener hook)
  └─ Services: PlanningService / SummarizationService / ReportingService / dispatch_search

并行：threading.Thread × N + queue.Queue
流式：agent.stream_run() token-level + tool_event_sink callback
```

### 2.2 新架构（LangGraph）

```
StateGraph(state_schema=ResearchState)
  ├─ Node "plan"        → 调 planner LLM，写回 todo_items
  ├─ Conditional Edge   → Send(...) fan-out 到 "research"
  ├─ Node "research"    → 单 task 子图：search + summarize（带流式）
  ├─ Node "report"      → 调 reporter LLM，生成最终报告
  └─ Node "persist"     → NoteService.save_report()

LLM:    LangChain BaseChatModel（ChatOpenAI / ChatOllama / OpenAI 兼容）
工具:   LangChain BaseTool（NoteTool 自实现 + SearchTool 自实现 hybrid 多后端）
事件:   astream_events v2 + custom_event 钩子 → SSE 适配器映射
并发:   LangGraph Send API + 内置 fan-out（无需手写 threading）
```

### 2.3 节点流程图

```
START → plan ─(Send×N)─→ research ─(reduce)─→ report → persist → END
```

`research` 节点内部是一个小型 ReAct 循环：调用 `search_tool`（必调）→ 调 `note_tool`（可选）→ LLM 生成 summary。**不使用** `create_react_agent` 预构建组件，全部由 StateGraph 显式编排，便于事件捕获。

## 3. 状态模型 (state schema)

`ResearchState` 使用 `TypedDict + Annotated` 定义 reducer：

```python
class ResearchState(TypedDict, total=False):
    research_topic: str
    todo_items: Annotated[list[TodoItem], merge_todos]   # 自定义 reducer：按 id 合并
    web_research_results: Annotated[list[str], operator.add]
    sources_gathered: Annotated[list[str], operator.add]
    research_loop_count: Annotated[int, operator.add]
    structured_report: str
    report_note_id: str | None
    report_note_path: str | None
```

`merge_todos` reducer 用于 fan-out 时把每个 worker 返回的单 task 状态合并回主状态：按 `id` 替换同 id 项。

`TodoItem` 保留原 dataclass 字段（id/title/intent/query/status/summary/sources_summary/notices/note_id/note_path/stream_token），改为 `pydantic.BaseModel` 便于序列化。

## 4. 受影响文件清单

### 4.1 删除/重写

| 文件 | 操作 | 说明 |
|---|---|---|
| `backend/src/agent.py` | **重写** | 用 LangGraph StateGraph 替换 DeepResearchAgent，保留 `run` / `run_stream` 公开签名 |
| `backend/src/services/planner.py` | **重写** | 改为 LangGraph node 函数 `plan_node(state)` + 解析逻辑保留 |
| `backend/src/services/summarizer.py` | **重写** | 改为 `summarize_node(state)` + LangChain `astream` 流式 token |
| `backend/src/services/reporter.py` | **重写** | 改为 `report_node(state)` |
| `backend/src/services/search.py` | **重写** | 移除 `hello_agents.SearchTool`，自实现多后端 dispatch（Tavily SDK / DDGS / SearXNG / Perplexity） |
| `backend/src/services/notes.py` | **重写** | 自实现 NoteService（Markdown 落盘 + index.json 维护） |
| `backend/src/services/tool_events.py` | **重写** | 改为 LangGraph 事件适配器，订阅 `astream_events` 输出 SSE 事件 |
| `backend/pyproject.toml` | **修改** | 移除 `hello-agents`，新增 `langgraph` / `langchain-core` / `langchain-openai` / `langchain-ollama` |

### 4.2 保留/微调

| 文件 | 操作 | 说明 |
|---|---|---|
| `backend/src/main.py` | **微调** | `DeepResearchAgent` 实例化与调用签名保持一致；SSE 事件 yield 不变 |
| `backend/src/models.py` | **微调** | `SummaryState` 改为 LangGraph `TypedDict`；`TodoItem` 改 Pydantic；保留 `SummaryStateOutput` |
| `backend/src/config.py` | **保留** | 字段不变；`use_tool_calling` 改为始终 True 由 LangGraph 决定 |
| `backend/src/prompts.py` | **保留** | Prompt 文本完全不变 |
| `backend/src/utils.py` | **保留** | `strip_thinking_tokens` / `format_sources` / `deduplicate_and_format_sources` 复用 |
| `backend/src/services/text_processing.py` | **保留** | `strip_tool_calls` 仍用于清洗 LLM 输出 |
| `frontend/**` | **零改动** | SSE 事件类型完全兼容 |

## 5. 关键实现细节

### 5.1 LLM 客户端工厂（替换 `_init_llm`）

```python
# backend/src/llm.py（新增）
def build_chat_model(config: Configuration) -> BaseChatModel:
    provider = (config.llm_provider or "").strip().lower()
    model = config.resolved_model()
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=model,
            base_url=config.sanitized_ollama_url().rstrip("/v1"),
            temperature=0.0,
        )
    # openai / lmstudio / 其他 OpenAI 兼容
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=model,
        base_url=config.llm_base_url or config.lmstudio_base_url,
        api_key=config.llm_api_key or "EMPTY",
        temperature=0.0,
    )
```

### 5.2 工具定义（LangChain BaseTool）

```python
# backend/src/tools/note_tool.py
class NoteTool(BaseTool):
    name = "note"
    description = "管理研究笔记：create/read/update/list/search"
    args_schema = NoteToolArgs  # action / note_id / title / note_type / tags / content
    def _run(self, **kwargs) -> str:
        return self._service.run(kwargs)  # 调用 NoteService

# backend/src/tools/search_tool.py
class SearchTool(BaseTool):
    name = "search"
    description = "网络检索"
    def _run(self, query: str, **kwargs) -> dict:
        return dispatch_search(query, self._config, ...)
```

### 5.3 Plan 节点

```python
def plan_node(state: ResearchState, config: RunnableConfig) -> dict:
    cfg = config["configurable"]["app_config"]
    llm = build_chat_model(cfg)
    prompt = todo_planner_instructions.format(
        current_date=datetime.now().strftime("%Y-%m-%d"),
        research_topic=state["research_topic"],
    )
    messages = [
        SystemMessage(todo_planner_system_prompt.strip()),
        HumanMessage(prompt),
    ]
    resp = llm.invoke(messages)
    tasks = _extract_tasks(resp.content)  # 复用旧 JSON / TOOL_CALL 解析
    todo_items = [TodoItem(id=i+1, **t) for i, t in enumerate(tasks)] or [_fallback(state)]
    return {"todo_items": todo_items}
```

### 5.4 Fan-out 到 research（Send API）

```python
def fan_out_research(state: ResearchState) -> list[Send]:
    return [Send("research", {"task": t, "research_topic": state["research_topic"]})
            for t in state["todo_items"]]

graph.add_conditional_edges("plan", fan_out_research, ["research"])
```

### 5.5 Research 节点（单 task 流式）

```python
async def research_node(payload: dict, config: RunnableConfig) -> dict:
    task: TodoItem = payload["task"]
    cfg = config["configurable"]["app_config"]

    # 1. 检索（同步）
    search_payload, notices, answer, backend = await asyncio.to_thread(
        dispatch_search, task.query, cfg, 0
    )
    sources_summary, context = prepare_research_context(search_payload, answer, cfg)

    # 通过 custom event 推 sources 事件（LangGraph 原生捕获）
    writer = get_stream_writer()  # langgraph.config.get_stream_writer
    writer({"type": "sources", "task_id": task.id,
            "latest_sources": sources_summary, "raw_context": context,
            "backend": backend})

    # 2. 总结（流式 token）
    llm = build_chat_model(cfg)
    prompt = build_summary_prompt(state_research_topic, task, context)
    chunks: list[str] = []
    async for chunk in llm.astream([SystemMessage(task_summarizer_instructions),
                                     HumanMessage(prompt)]):
        text = chunk.content or ""
        chunks.append(text)
        writer({"type": "task_summary_chunk", "task_id": task.id, "content": text})

    summary = strip_tool_calls(strip_thinking_tokens("".join(chunks)))
    task.summary = summary.strip() or "暂无可用信息"
    task.status = "completed"
    task.sources_summary = sources_summary
    task.notices = notices

    return {
        "todo_items": [task],         # 由 merge_todos reducer 合并
        "web_research_results": [context],
        "sources_gathered": [sources_summary],
        "research_loop_count": 1,
    }
```

### 5.6 Report + Persist 节点

```python
def report_node(state, config) -> dict:
    cfg = config["configurable"]["app_config"]
    llm = build_chat_model(cfg)
    prompt = build_report_prompt(state)   # 复用旧逻辑
    resp = llm.invoke([SystemMessage(report_writer_instructions), HumanMessage(prompt)])
    report = strip_tool_calls(strip_thinking_tokens(resp.content))
    return {"structured_report": report}

def persist_node(state, config) -> dict:
    cfg = config["configurable"]["app_config"]
    note_service = NoteService(cfg.notes_workspace)
    if not cfg.enable_notes or not state.get("structured_report"):
        return {}
    note_id = note_service.save_report(state["research_topic"], state["structured_report"])
    writer = get_stream_writer()
    writer({"type": "report_note", "note_id": note_id, "title": ..., "content": ...})
    return {"report_note_id": note_id, "report_note_path": str(...)}
```

### 5.7 SSE 事件协议保留（关键适配层）

新 `services/tool_events.py` 改造为 **LangGraph 事件适配器**：

```python
# backend/src/services/event_adapter.py（重写自 tool_events.py）
async def stream_research_events(graph, topic, config) -> AsyncIterator[dict]:
    yield {"type": "status", "message": "初始化研究流程"}

    # 使用 stream_mode=["custom", "updates"] 同时拿到自定义事件和节点更新
    async for stream_mode, payload in graph.astream(
        {"research_topic": topic},
        config={"configurable": {"app_config": config}},
        stream_mode=["custom", "updates"],
    ):
        if stream_mode == "custom":
            # research_node 内 writer() 推的事件，已经是 SSE 格式，直接透传
            yield payload
        elif stream_mode == "updates":
            # 节点完成更新，映射成 todo_list / task_status
            for node_name, node_output in payload.items():
                if node_name == "plan":
                    yield {"type": "todo_list",
                           "tasks": [t.model_dump() for t in node_output["todo_items"]]}
                elif node_name == "research":
                    task = node_output["todo_items"][0]
                    yield {"type": "task_status", "task_id": task.id,
                           "status": task.status, "title": task.title,
                           "summary": task.summary, ...}
                elif node_name == "persist":
                    pass  # report_note 已通过 custom 推送

    # 最终事件
    final_state = await graph.aget_state(...)
    yield {"type": "final_report",
           "report": final_state.values["structured_report"], ...}
    yield {"type": "done"}
```

工具调用事件（`type: "tool_call"`）通过订阅 LangChain `astream_events` 中的 `on_tool_start` / `on_tool_end` 转换得到（与 `dispatch_search` 调用、`NoteTool` 调用一一对应）。

### 5.8 NoteService（自实现）

```python
# backend/src/services/notes.py（重写）
class NoteService:
    def __init__(self, workspace: str):
        self.root = Path(workspace); self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "notes_index.json"
    def run(self, payload: dict) -> str:
        action = payload["action"]
        return getattr(self, f"_{action}")(payload)
    def _create(self, p) -> str: ...   # 写 {note_id}.md + 更新 index
    def _read(self, p) -> str: ...
    def _update(self, p) -> str: ...
    def _list(self, p) -> str: ...
    def _search(self, p) -> str: ...
    def save_report(self, topic, content) -> str: ...
```

文件命名沿用 `note_YYYYMMDD_HHMMSS_N.md` 格式，`index.json` schema 与现有保持一致以兼容历史数据。

### 5.9 并行与并发安全

LangGraph Send API 默认并行 dispatch，节点内若同步阻塞需用 `await asyncio.to_thread(...)`（如 `dispatch_search`）。状态 reducer 由 LangGraph 保证线程安全，**移除原 `_state_lock`**。

## 6. 边界与异常处理

| 场景 | 处理 |
|---|---|
| Planner 输出无法解析 | 复用 `_extract_tasks` 多策略解析 + `create_fallback_task` 兜底（由 plan_node 内部完成） |
| 检索无结果 | research_node 标记 `task.status = "skipped"`，发 `task_status` 事件，跳过总结 |
| LLM 流式中断 | `try/finally` 内累积 `chunks`，最终 summary 至少为已收到部分；任务状态 `completed` 但 summary 可能为空，回退 "暂无可用信息" |
| 单 task 异常 | LangGraph 节点抛错会中断整图；包一层 try/except 在 research_node 内部，异常时 yield `task_status: failed` 并返回空增量，不影响其他任务 |
| Notes 关闭 (`enable_notes=False`) | NoteTool 不注册到 graph，persist_node 直接 return |
| 历史 Note 兼容 | NoteService 启动读取既有 `notes_index.json`，保持 ID 单调递增 |

## 7. 数据流路径

```
HTTP /research/stream
   └─ main.py: stream_research_events(graph, topic, config)
        └─ graph.astream(stream_mode=["custom","updates"])
             ├─ plan_node           → updates: {plan: {todo_items}} → "todo_list"
             ├─ Send×N → research_node (parallel)
             │     ├─ dispatch_search()                → custom: "sources"
             │     ├─ llm.astream()                    → custom: "task_summary_chunk" ×N
             │     └─ return {todo_items:[task]}       → updates: → "task_status"
             ├─ report_node          → updates: {report: {structured_report}}
             └─ persist_node         → custom: "report_note"
   ← yield "final_report" / "done"
```

## 8. 预期成果

1. `pyproject.toml` 不再依赖 `hello-agents`，依赖换为 `langgraph>=0.2`、`langchain-core`、`langchain-openai`、`langchain-ollama`、`tavily-python`、`ddgs`。
2. 后端启动后 `POST /research` 与 `POST /research/stream` 行为对前端不可见地保持一致：报告内容质量等同、SSE 事件类型与字段完全兼容。
3. 代码总行数预计减少 15%（移除手写 threading/queue/listener，由 LangGraph 接管）。
4. 单条研究端到端耗时基本持平（LLM 调用是瓶颈），但可观测性增强（LangSmith 可直接接入）。
5. 通过 `uv run python -m src.main` 启动，原 README/启动脚本无需修改。

## 9. 不在本次范围

- 引入 LangSmith 追踪（可后续单独配置环境变量启用）。
- 引入 Checkpointer（暂不支持中断恢复，保持无状态）。
- 前端改动。
- 增加 reflection / self-critique 循环。
- 评估集 / 自动化测试新增。
