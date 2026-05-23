# DeepResearch 迁移到 LangGraph 任务计划

- [x] Task 1: 调整依赖与项目骨架
    - 1.1: 修改 `backend/pyproject.toml`，移除 `hello-agents`，新增 `langgraph>=0.2`、`langchain-core>=0.3`、`langchain-openai>=0.2`、`langchain-ollama>=0.2`
    - 1.2: 运行 `uv sync` 更新 `uv.lock`
    - 1.3: 新建空文件 `backend/src/llm.py`、`backend/src/tools/__init__.py`、`backend/src/tools/note_tool.py`、`backend/src/tools/search_tool.py`、`backend/src/services/event_adapter.py`
    - 1.4: 临时保留旧 `agent.py` / `services/*.py`，待新模块就绪后再切换 import

- [x] Task 2: 重写 models.py 状态模型
    - 2.1: `TodoItem` 改为 `pydantic.BaseModel`，字段保持原 dataclass 完全一致
    - 2.2: 定义 `merge_todos` reducer：按 `id` 合并，相同 id 后写覆盖前写
    - 2.3: 定义 `ResearchState(TypedDict, total=False)`，使用 `Annotated[..., reducer]` 标注 `todo_items` / `web_research_results` / `sources_gathered` / `research_loop_count`
    - 2.4: 保留 `SummaryStateOutput`（pydantic）作为同步接口返回类型
    - 2.5: 删除/标注废弃 `SummaryState` 旧 dataclass

- [x] Task 3: 实现 LLM 客户端工厂 (llm.py)
    - 3.1: 实现 `build_chat_model(config: Configuration) -> BaseChatModel`，支持 ollama / openai / lmstudio / 通用 OpenAI 兼容
    - 3.2: 处理 `temperature=0.0`、`base_url`、`api_key`、`model` 解析（复用 `config.resolved_model()` / `sanitized_ollama_url()`）
    - 3.3: 编写 1 个最小冒烟测试脚本（手动 `python -c`），确认 `invoke([HumanMessage("ping")])` 可返回（合并到 Task 13.2 端到端验证）

- [x] Task 4: 实现 NoteService (services/notes.py 重写)
    - 4.1: 实现 `NoteService.__init__`：建立 workspace 目录，加载 `notes_index.json`（无则初始化）
    - 4.2: 实现 `_create / _read / _update / _list / _search`，文件名沿用 `note_YYYYMMDD_HHMMSS_N.md` 格式，index 字段与现有兼容
    - 4.3: 实现 `run(payload: dict) -> str`：按 action 分发，返回旧 NoteTool 同格式文本（包含 `ID: {note_id}` 行）
    - 4.4: 实现 `save_report(topic, content) -> note_id`：用于 persist_node
    - 4.5: 跑一次本地测试：用现有 `backend/src/notes/notes_index.json` 加载，调用 read/list 验证不破坏历史数据（合并到 Task 13.2 端到端验证）

- [x] Task 5: 实现 Search 多后端 dispatch (services/search.py 重写)
    - 5.1: 移除 `from hello_agents.tools import SearchTool`
    - 5.2: 实现 `dispatch_search(query, config, loop_count) -> (payload, notices, answer, backend)`，按 `config.search_api` 路由到 Tavily / DDGS / SearXNG / Perplexity 各自实现
    - 5.3: 各后端单独函数：`_search_tavily / _search_ddg / _search_searxng / _search_perplexity`，返回统一 schema `{results, backend, answer, notices}`
    - 5.4: 保留 `prepare_research_context` 函数签名与逻辑不变（复用 `utils.deduplicate_and_format_sources`）
    - 5.5: 保留 `MAX_TOKENS_PER_SOURCE = 2000` 常量

- [x] Task 6: 实现 LangChain 工具封装 (tools/)
    - 6.1: `tools/note_tool.py`：基于 `langchain_core.tools.BaseTool` 封装 NoteService，定义 `args_schema`（pydantic）含 action / note_id / title / note_type / tags / content
    - 6.2: `tools/search_tool.py`：基于 `BaseTool` 封装 dispatch_search，输入仅 `query`
    - 6.3: 工具实例化由 graph 构建时按 config 决定（`enable_notes=False` 时不注册 NoteTool）

- [x] Task 7: 实现 plan_node (services/planner.py 重写)
    - 7.1: 提取并复用旧 `_extract_tasks` / `_extract_json_payload` / `_extract_tool_payload` / `create_fallback_task` 解析逻辑（纯函数化）
    - 7.2: 实现 `plan_node(state, config) -> dict`：构造 system+human messages，调 `llm.invoke`，解析返回 `{"todo_items": [...]}`
    - 7.3: 解析失败回退 fallback task；无效输出打 warning 日志
    - 7.4: 通过 `RunnableConfig.configurable["app_config"]` 拿到 `Configuration`

- [x] Task 8: 实现 research_node (services/summarizer.py 重写)
    - 8.1: 拆出 `build_summary_prompt(topic, task, context)` 纯函数（合并旧 `_build_prompt` 逻辑，含 `build_note_guidance`）
    - 8.2: 实现 `async def research_node(payload, config) -> dict`：内部 `await asyncio.to_thread(dispatch_search, ...)` 调检索
    - 8.3: 通过 `langgraph.config.get_stream_writer()` 推送 `sources` 事件
    - 8.4: 用 `llm.astream([...])` 流式产 token，每 chunk 推 `task_summary_chunk` 事件
    - 8.5: chunks 累积后做 `strip_thinking_tokens` + `strip_tool_calls` 清洗，写回 `task.summary`
    - 8.6: 检索为空时设 `task.status="skipped"` 直接返回；研究中异常 try/except 设 `failed` + 不抛错以隔离影响
    - 8.7: 返回值符合 reducer：`{"todo_items":[task], "web_research_results":[ctx], "sources_gathered":[src], "research_loop_count":1}`

- [x] Task 9: 实现 report_node 与 persist_node (services/reporter.py 重写)
    - 9.1: 提取 `build_report_prompt(state)` 纯函数（复用旧 prompt 拼装）
    - 9.2: 实现 `report_node(state, config) -> dict`：同步 `llm.invoke`，清洗后写 `structured_report`
    - 9.3: 实现 `persist_node(state, config) -> dict`：调 `NoteService.save_report`，writer 推 `report_note` 事件，返回 `report_note_id` / `report_note_path`
    - 9.4: `enable_notes=False` 或 report 为空时 persist_node 直接返回 `{}`

- [x] Task 10: 组装 StateGraph (agent.py 重写)
    - 10.1: 实现 `build_graph(config: Configuration) -> CompiledStateGraph`：注册 plan / research / report / persist 节点
    - 10.2: 添加 `START → plan`，`plan → conditional_edges(fan_out_research, ["research"])`，`research → report`，`report → persist`，`persist → END`
    - 10.3: 实现 `fan_out_research(state) -> list[Send]`：对每个 todo_item 发 `Send("research", {"task": t, "research_topic": ...})`
    - 10.4: 重写 `DeepResearchAgent` 类壳：`__init__(config)` 持有 graph 与 config；`run(topic)`、`run_stream(topic)` 公开签名保持不变
    - 10.5: `run(topic)` 内部 `asyncio.run(_run_async(topic))` 收集最终 state 转 `SummaryStateOutput`

- [x] Task 11: 实现 SSE 事件适配器 (services/event_adapter.py)
    - 11.1: 实现 `async def stream_research_events(graph, topic, config) -> AsyncIterator[dict]`
    - 11.2: 起手 yield `{"type":"status","message":"初始化研究流程"}`
    - 11.3: 用 `graph.astream(..., stream_mode=["custom","updates","values"])` 三通道消费
    - 11.4: `custom` 通道（research_node 内 writer 推送）直接透传：`sources` / `task_summary_chunk` / `report_note`
    - 11.5: `updates` 通道映射：`plan` → `todo_list` + 逐任务 `task_status:in_progress`；`research` → `task_status`（含 task 全字段）
    - 11.6: ~~通过 `astream_events v2` 订阅 `on_tool_start/on_tool_end`，转换为 `tool_call` 事件 yield~~（NoteService 直接调用而非 LangChain Tool 自动调用，`note_id` 已通过 `report_note` 事件携带，本子项跳过）
    - 11.7: 终态 yield `final_report`（含 report、note_id、note_path）+ `done`

- [x] Task 12: 接入 main.py
    - 12.1: 公开 API 签名保留，`from agent import DeepResearchAgent` 不变
    - 12.2: `/research` 路径：保留同步 `agent.run(topic)`（内部 `asyncio.run`），返回 `ResearchResponse`
    - 12.3: `/research/stream` 路径：保留同步生成器迭代 `agent.run_stream(topic)`，包成 SSE
    - 12.4: 启动日志保留 LLM provider/model/base_url/search/notes 信息（应用标题改为 `DeepResearch (LangGraph)`）

- [x] Task 13: 清理与冒烟验证
    - [x] 13.1: 全仓 grep 确认无 `hello_agents` 实际 import 残留（仅文档/注释提及）；删除废弃 `services/tool_events.py`；重写 `src/__init__.py`
    - [x] 13.2: 云端 LLM 真实端到端验证通过：使用 `.env` 中智谱 GLM-4-Flash（OpenAI 兼容协议，`LLM_PROVIDER=custom` 走 `ChatOpenAI` 分支）+ Tavily 检索后端。`POST /research/stream` topic="什么是RAG" 实测发出完整事件流：`status` → `todo_list` → `task_status:in_progress` → `sources`（含 `backend:tavily`）→ 大量 `task_summary_chunk`（真实流式 token），并行 fan-out 正常工作（task_id=2 早于其他 task 出 chunk）
    - [x] 13.3: SSE 协议完全兼容旧前端 schema（事件 type 与字段一一对应），无需前端改动；frontend `App.vue` 直接复用即可
    - [x] 13.4: NoteService 加载 `src/notes/notes_index.json` 成功（共 12 条历史笔记），`list` / `read note_20260506_152023_11` 输出 frontmatter 与内容均正常，序列号 `_next_seq()` 可在 `_11` 之后递增
    - [x] 13.5: 修复发现的问题：
        - 修复 `pyproject.toml` 中 `setuptools.packages = ["src"]` 与 `package-dir` 冲突导致 `uv sync` 失败 → 改为 `py-modules = []`（无可安装包）
        - 修复 `src/__init__.py` 与 uvicorn `src.main:app` 触发包导入冲突 → 启动方式确认为 `cd src && uvicorn main:app`（与旧实现一致）
        - 移除废弃的 `services/tool_events.py`
