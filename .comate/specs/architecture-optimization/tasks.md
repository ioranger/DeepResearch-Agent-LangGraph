# 架构优化任务清单

- [x] Task 1: 流式链路真异步化——main.py + agent.py
    - 1.1: `agent.py` 重命名 `_run_async` 为 `arun`（公开异步方法），`run` 改为 `asyncio.run(self.arun(...))`
    - 1.2: `main.py` 的 `/research` 端点改为 `async def run_research`，直接 `await agent.arun(topic)`
    - 1.3: `main.py` 的 `/research/stream` 端点改为 `async def stream_research`，用 `agent.astream(topic)` 返回 AsyncIterator
    - 1.4: `agent.py` 保留 `run_stream` / `run` 作为 CLI / 测试用的同步外观

- [x] Task 2: 应用生命周期迁移——lifespan 替换 on_event + 配置单例 + 日志去重
    - 2.1: `main.py` 添加 `asynccontextmanager lifespan(app)` ，启动日志写入 lifespan
    - 2.2: `create_app` 接收可选的 `Configuration` 参数，存到 `app.state.config`，lifespan hook
    - 2.3: 删除模块级 `startup_config` 和 `@app.on_event("startup")`
    - 2.4: `_build_config` 从 `app.state.config` 取基础配置做按请求 override
    - 2.5: 删除重复的 ERROR 级 stderr sink，保留单一 logger.add（级别取 config.log_level）
    - 2.6: 更新 `__main__` 块，传递 config 给 `create_app`

- [x] Task 3: event_adapter 删除二次执行兜底
    - 3.1: 删除 `if not final_state: final_state = await graph.ainvoke(...)` 代码块
    - 3.2: 改为流式失败时发 `{"type": "error", "code": "STREAM_FAILED", "detail": ...}` + `{"type": "done"}`
    - 3.3: 从 `report` 节点的 `updates` 增量提取 `structured_report` 写入 `final_state`

- [x] Task 4: 笔记目录外移——源码目录 → data 目录
    - 4.1: `config.py` 的 `notes_workspace` 默认值改为 `backend/data/notes`（相对项目根）
    - 4.2: `.gitignore` 增加 `backend/data/`
    - 4.3: 迁移现有笔记文件：`mv backend/src/notes/* backend/data/notes/`

- [x] Task 5: 前端 App.vue 组件拆分
    - 5.1: 抽出 `frontend/src/composables/useResearchStream.ts`：SSE 连接 + 事件分发 + 任务状态机
    - 5.2: 抽出 `frontend/src/components/TopicInput.vue`
    - 5.3: 抽出 `frontend/src/components/TaskList.vue`
    - 5.4: 抽出 `frontend/src/components/SourcePanel.vue`
    - 5.5: 抽出 `frontend/src/components/ReportView.vue`
    - 5.6: `App.vue` 退化为布局壳 + composable 装配，目标 < 300 行
    - 5.7: 验证 `npm run build` 通过

- [x] Task 6: 测试验证——回归 + 更新
    - 6.1: 更新 `tests/integration/test_api.py`，适配 async 端点（httpx.AsyncClient）
    - 6.2: 新增 event_adapter 异常路径测试
    - 6.3: 运行全量 `uv run pytest`，确保 34 个测试全过 + 0 个 on_event 警告
