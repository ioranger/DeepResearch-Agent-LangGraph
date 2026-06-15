# 对标开源项目能力升级任务清单

- [x] Task 1: 反思循环核心——新增 `services/researcher.py` 和重构 research 节点
    - 1.1: 在 `prompts.py` 新增 `reflection_evaluator` 系统提示和用户提示模板（中英双语，输出 `{"is_sufficient": bool, "follow_up_query": str, "reasoning": str}`）
    - 1.2: 新增 `services/researcher.py`，实现 `async def iterative_research(task, research_topic, cfg) -> dict`
    - 1.3: 实现循环逻辑：首轮 search → summarize → reflect（调用 LLM 结构化输出评估），不充分则生成 follow-up 查询继续，上限 `cfg.max_web_research_loops`
    - 1.4: 每轮通过 stream_writer 推送 `task_reflection` 事件（含 is_sufficient、follow_up_query、current_loop）
    - 1.5: 异常处理：任一轮异常不阻断整体，使用已积累的 summary 返回
    - 1.6: 重构 `services/summarizer.py` 的 `research_node` 为薄壳，委托给 `iterative_research`
    - 1.7: 更新 SSE 事件：`event_adapter.py` 透传 `task_reflection` 事件

- [x] Task 2: 引用绑定——搜索结果编号化，报告增加引用锚点和 References
    - 2.1: `models.py` 的 `TodoItem` 新增 `citations: list[int]` 字段
    - 2.2: `prompts.py` 新增 `citation_directive` 提示（中英双语，要求 LLM 引用信息时使用 `[n]` 标注）
    - 2.3: `services/search.py` 的 `prepare_research_context` 改造：每条结果前加 `[n] 标题 — URL`，`sources_summary` 改为结构化 `[{id, title, url, snippet}]` 列表
    - 2.4: `services/summarizer.py` 的 `build_summary_prompt` 追加 `citation_directive`，上下文附 `[n]` 序号列表
    - 2.5: `services/event_adapter.py` 的 `sources` SSE 事件改为结构化 list 格式
    - 2.6: `services/reporter.py` 的 `build_report_prompt` 传递各任务 citations；`report_node` 输出末尾追加 `## 参考来源` 去重列表

- [x] Task 3: Planner 结构化输出——`with_structured_output` 强约束
    - 3.1: `models.py` 新增 `TaskPlan(BaseModel)` 和 `PlannerTaskItem(BaseModel)`：`tasks: list[PlannerTaskItem]`，每项含 title/intent/query
    - 3.2: `prompts.py` 修改 `todo_planner_system_prompt`，移除 `[TOOL_CALL:todo:...]` 自定义格式要求，改为 JSON 风格说明
    - 3.3: `services/planner.py` 的 `plan_node`：优先 `llm.with_structured_output(TaskPlan).invoke()`，异常/不支持时回落现有 `_extract_tasks` 手工解析
    - 3.4: 重构 planner 返回路径：成功走 `TaskPlan` 时直接 `.model_dump()` 映射为 `TodoItem` 列表

- [x] Task 4: 检索片段相关性过滤——Top-K 轻量过滤
    - 4.1: `services/text_processing.py` 新增 `filter_relevant_snippets(snippets, query, top_k=8) -> list[dict]`，基于关键词交集打分 + 长度归一化
    - 4.2: `services/search.py` 的 `prepare_research_context` 在拼接前调用 `filter_relevant_snippets`
    - 4.3: 边界处理：过滤后为空返回 "暂无可用信息"

- [x] Task 5: 报告分节生成——逐节生成后拼装
    - 5.1: `prompts.py` 新增 `section_writer_instructions`（中英双语，单节生成指令）
    - 5.2: `services/reporter.py` 新增 `generate_section_markdown(task, research_topic, cfg) -> str`
    - 5.3: `report_node` 改为串行生成各 task 的 section → 拼装 → 调 LLM 整合为完整报告
    - 5.4: 保留现有单次生成路径作为分节生成失败时的回落

- [x] Task 6: 测试与验证——回归 + 新增测试
    - 6.1: 新增 `tests/unit/test_researcher.py`：验证 `iterative_research` 循环 ≥ 2 次；异常不阻断
    - 6.2: 新增 `tests/unit/test_planner.py`：验证结构化输出路径；mock 不支持时回落
    - 6.3: 扩展 `tests/unit/test_search.py`：验证 `prepare_research_context` 输出带 `[n]` 序号
    - 6.4: 新增 `tests/unit/test_reporter.py`：验证 `sources_summary` 结构化 list + 报告含 References
    - 6.5: 运行全量 `uv run pytest`，确保现有 8 个测试全过，新增 ≥ 4 个通过
