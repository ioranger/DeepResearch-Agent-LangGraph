# Deep Research 项目架构优化（architecture-optimization）

## 1. 背景与目标

项目已完成 LangGraph 迁移（plan → research 并行 → report → persist）和质量基建（pytest harness、配置统一、advanced 搜索聚合）。本阶段聚焦**架构层面的结构性问题**：异步链路、应用生命周期、模块边界、数据落盘位置、前端单体组件。

目标：在不改变对外 API（`/research`、`/research/stream` SSE 协议）的前提下，消除架构债，提升并发能力与可维护性。

## 2. 问题清单与技术方案

### 2.1 P0：流式链路"假异步"——同步桥接阻塞事件循环

**现状**（`backend/src/agent.py` 的 `run_stream` + `backend/src/main.py` 的 `stream_research`）：

- `run_stream` 为每个请求 `asyncio.new_event_loop()`，用 `loop.run_until_complete(agen.__anext__())` 把异步流硬转成同步迭代器
- FastAPI 端点 `stream_research` 是 `def`（同步），跑在线程池里，每个流式请求独占一个线程 + 一个私有事件循环
- 并发请求多时线程池耗尽，SSE 推流延迟

**方案**：

- `/research/stream` 端点改为 `async def`，直接消费 `agent.astream(topic)`，StreamingResponse 接收 async generator：

```python
@app.post("/research/stream")
async def stream_research(payload: ResearchRequest) -> StreamingResponse:
    config = _build_config(payload)
    agent = DeepResearchAgent(config=config)

    async def event_iterator() -> AsyncIterator[str]:
        async for event in agent.astream(payload.topic):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_iterator(), media_type="text/event-stream", ...)
```

- `/research` 同步端点改为 `async def` + `await agent.arun(topic)`（将私有 `_run_async` 重命名为公开的 `arun`）
- `run_stream` / `run` 保留为 CLI / 测试用的同步外观，但 FastAPI 不再走它们

**受影响文件**：

- 修改 `/Users/jackkang/helloagents-deepresearch/backend/src/main.py`（`stream_research`、`run_research`）
- 修改 `/Users/jackkang/helloagents-deepresearch/backend/src/agent.py`（暴露 `arun` 公开异步方法）

### 2.2 P0：应用生命周期与配置单例

**现状**（`backend/src/main.py`）：

- 使用已废弃的 `@app.on_event("startup")`（pytest 中产生 DeprecationWarning）
- `Configuration.from_env()` 被调用 4 次（模块级 `startup_config`、`create_app`、`on_event`、`__main__`），存在配置漂移风险
- `logger.add` 注册了两个 stderr sink（INFO 级 + ERROR 级），ERROR 日志会重复输出两遍

**方案**：

- 迁移到 lifespan handler：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    config: Configuration = app.state.config
    logger.info("DeepResearch configuration loaded: ...")
    yield

def create_app(config: Configuration | None = None) -> FastAPI:
    config = config or Configuration.from_env()
    app = FastAPI(title="DeepResearch (LangGraph)", lifespan=lifespan)
    app.state.config = config
    ...
```

- 全文件统一使用 `app.state.config`，仅 `_build_config` 为按请求 override 重新构造
- 删除重复的 ERROR sink；保留单一 stderr sink（级别取 `config.log_level`）
- `create_app(config)` 支持注入配置，便于测试

**受影响文件**：

- 修改 `/Users/jackkang/helloagents-deepresearch/backend/src/main.py`

### 2.3 P1：event_adapter 兜底逻辑会触发二次完整研究

**现状**（`backend/src/services/event_adapter.py`）：

```python
if not final_state:
    final_state = await graph.ainvoke(inputs, config=runnable_config)
```

流式异常（如 LLM 中途断连）后 `final_state` 为空，会**重新跑一遍完整研究流程**（再次规划、搜索、总结），耗时翻倍且重复消耗 LLM tokens。

**方案**：

- 删除 `graph.ainvoke` 兜底；流式失败时直接发 `{"type": "error", "code": "STREAM_FAILED", "detail": ...}` + `{"type": "done"}`
- `updates` 模式中已能拿到各节点输出，维护增量 `final_state`（从 `report` 节点的 update 中取 `structured_report`），无需依赖 `values` 快照兜底

**受影响文件**：

- 修改 `/Users/jackkang/helloagents-deepresearch/backend/src/services/event_adapter.py`

### 2.4 P1：笔记数据落在源码目录内

**现状**：笔记写入 `backend/src/notes/`（已有 14 个 .md + notes_index.json 混在源码里），污染源码树、易被打包进发行物。

**方案**：

- `Configuration.notes_workspace` 默认值改为 `backend/data/notes`（相对项目根），支持 `NOTES_WORKSPACE` 环境变量覆盖
- 迁移现有笔记文件到新目录；`.gitignore` 增加 `backend/data/`
- `NoteService` 不变（已接受 workspace 参数）

**受影响文件**：

- 修改 `/Users/jackkang/helloagents-deepresearch/backend/src/config.py`（notes_workspace 默认值）
- 修改 `/Users/jackkang/helloagents-deepresearch/.gitignore`
- 移动 `backend/src/notes/*` → `backend/data/notes/`

### 2.5 P2：前端 App.vue 单体组件拆分（2304 行）

**现状**：`frontend/src/App.vue` 一个文件承载全部 UI（输入区、任务列表、来源面板、报告渲染、SSE 状态机），难以维护。

**方案**（最小拆分，不引状态管理库）：

- 抽出 `frontend/src/composables/useResearchStream.ts`：封装 SSE 连接、事件分发、任务状态机（核心逻辑层）
- 抽出展示组件：
  - `frontend/src/components/TopicInput.vue`（输入与触发）
  - `frontend/src/components/TaskList.vue`（todo 列表 + 任务状态）
  - `frontend/src/components/SourcePanel.vue`（来源展示）
  - `frontend/src/components/ReportView.vue`（Markdown 报告渲染）
- `App.vue` 退化为布局壳 + composable 装配，目标 < 300 行
- 保持现有样式与交互不变，仅做结构搬移

**受影响文件**：

- 修改 `/Users/jackkang/helloagents-deepresearch/frontend/src/App.vue`
- 新增上述 composable 与 4 个组件文件

## 3. 数据流（优化后）

```
POST /research/stream (async def)
  → DeepResearchAgent.astream
    → stream_research_events(graph.astream, stream_mode=[custom, updates])
      → plan(update) → todo_list / task_status 事件
      → research(custom+update) → sources / task_summary_chunk / task_status
      → report(update) → 增量缓存 structured_report
      → persist(custom) → report_note
  → final_report（来自增量缓存，无兜底重跑） → done
```

## 4. 边界条件与异常处理

- 流式中断：发 `error` 事件（带 code）后立即 `done`，不重跑研究
- 配置注入：`create_app(config=None)` 时回落 `from_env()`，行为与现状一致
- 笔记目录不存在：`NoteService` 已有 mkdir 逻辑，无需额外处理
- 前端拆分回归风险：以现有 SSE 事件协议为契约，逐组件搬移后人工验证 + 现有集成测试兜底

## 5. 验收标准

1. 现有 8 个测试全部通过；pytest 不再出现 `on_event` DeprecationWarning
2. `/research/stream` 在 async 端点下 SSE 事件协议与现状逐字段一致（集成测试校验）
3. 流式异常路径不再触发第二次 `graph.ainvoke`（单测 mock 验证）
4. 笔记写入 `backend/data/notes/`，源码树无新增数据文件
5. `App.vue` < 300 行，前端 `npm run build` 通过，页面功能不回归

## 6. 任务优先级

| 优先级 | 内容 |
|---|---|
| P0 | 2.1 异步流式链路、2.2 lifespan + 配置单例 + 日志去重 |
| P1 | 2.3 删除二次执行兜底、2.4 笔记目录外移 |
| P2 | 2.5 前端组件拆分 |
