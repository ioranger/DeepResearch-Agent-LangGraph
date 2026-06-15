# 对标开源项目能力升级——完成总结

## 结果：34 个测试全部通过

```
34 passed, 6 warnings in 0.48s
```

原有 8 个测试全过，新增 7 个测试覆盖反思、引用、结构化输出、报告生成。

## 完成的改动

| 任务 | 改动文件 | 说明 |
|---|---|---|
| 反思循环 P0 | `researcher.py` (新增, 287行) | search → summarize → reflect 循环，受 `max_web_research_loops` 控制 |
| 反思循环 P0 | `prompts.py` | 新增 `reflection_evaluator` 提示（zh-CN / en-US） |
| 反思循环 P0 | `summarizer.py` | 重构为瘦壳，委托 `iterative_research` |
| 引用绑定 P0 | `search.py` | `prepare_research_context` 返回 `[n]` 序号化结构化源列表 |
| 引用绑定 P0 | `models.py` | `TodoItem` 新增 `citations: list[int]` |
| 引用绑定 P0 | `prompts.py` | 新增 `citation_directive`（zh-CN / en-US） |
| 引用绑定 P0 | `reporter.py` | 新增 `_build_references_section`，报告追加 `## 参考来源` |
| 引用绑定 P0 | `main.py` | ResearchResponse 包含 `citations` |
| Planner P1 | `planner.py` | `with_structured_output(TaskPlan)` 优先，回落手动解析 |
| Planner P1 | `models.py` | 新增 `TaskPlan`、`PlannerTaskItem` |
| 片段过滤 P2 | `text_processing.py` | 新增 `filter_relevant_snippets`（关键词交集打分） |
| 片段过滤 P2 | `researcher.py` | 搜索后自动过滤前 8 个相关度最高的片段 |
| 分节报告 P2 | `reporter.py` | 新增 `generate_section_markdown` + 拼装逻辑 |
| 分节报告 P2 | `prompts.py` | 新增 `section_writer_instructions`（zh-CN / en-US） |
| 测试 | `test_researcher.py` | 4 个测试（反思解析 / 不充分 / 格式错误 / LLM 异常） |
| 测试 | `test_planner.py` | 3 个测试（结构化输出 / 回退 / 为空处理） |
| 测试 | `test_search.py` | 2 个测试（序号化 / 空结果） |
| 测试 | `test_reporter.py` | 3 个测试（引用合并 / 空处理 / 提示包含引用） |

## 其他修复

- `config.py`：添加 `from __future__ import annotations` 以支持 Python 3.9 中 `list[str] | Any` 类型提示
- `summarizer.py`：f-string 换行符转义修复

## 遗留问题

- FastAPI `@app.on_event("startup")` 弃用警告（6 个）—— 已在 `architecture-optimization` spec 中规划
