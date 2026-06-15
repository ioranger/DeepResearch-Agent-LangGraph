# 对标开源优秀 Deep Research 项目的能力升级（opensource-benchmark-upgrade）

## 1. 背景与目标

参考 `open_deep_research`（LangChain 官方）、`GPT Researcher`、`STORM`（Stanford）等主流开源 Deep Research 项目，弥补本项目在**研究深度、可信度、结构化、检索效率**四个维度的差距。

与 `architecture-optimization`（异步链路/lifespan/前端拆分）正交，可独立推进。

## 2. 差距清单

| 维度 | 主流做法 | 本项目现状 | 收益 |
|---|---|---|---|
| 研究深度 | 反思循环：summary → 评估缺口 → follow-up 查询 | `max_web_research_loops` 已存在但**未启用**，每个任务只搜一轮 | 高 |
| 可信度 | 行内 `[n]` 引用 + 末尾 References | `sources_summary` 仅罗列，报告正文无锚点 | 高 |
| 解析稳定性 | `with_structured_output` 强 schema | 手写 find `{`/`}` + 工具调用回退 | 中 |
| 检索效率 | embedding 相似度过滤片段 | `prepare_research_context` 整页拼接 | 中 |
| 报告质量 | 分节生成 → 拼装 | `report_node` 单次 LLM 调用 | 中 |

## 3. 改进方案

### 3.1 P0：反思循环（reflection loop）

**思路**：在 `research_node` 内增加 reflect 步骤。首轮搜 → 总结 → 反思评估"信息是否充分、还缺什么"；不充分则生成 follow-up query 追加搜索，受 `max_web_research_loops` 约束。

**改造点**：

- `services/summarizer.py` 抽出 `_summarize_once(task, context, cfg) -> (summary, accumulated_context)`
- 新增 `services/researcher.py`，实现 `async def iterative_research(task, cfg) -> final_summary`：
  - 维护 `accumulated_context`、`accumulated_sources`
  - 循环上限 `cfg.max_web_research_loops`
  - 每轮：search → 拼接新片段 → 总结 → reflect（LLM 评估 + 输出 follow-up query）
  - reflect 用结构化输出 `{ "is_sufficient": bool, "follow_up_query": str, "reasoning": str }`
- `research_node` 改为薄壳：调用 `iterative_research`，SSE 事件按需加 `task_reflection_chunk`
- 事件：保留现有 `sources` / `task_summary_chunk` / `task_status`，新增 `task_reflection`（一次性，反思评估结果）

**新增 prompt**：在 `prompts.py` 增加 `reflection_evaluator`（中英）

**受影响文件**：

- 新增 `/Users/jackkang/helloagents-deepresearch/backend/src/services/researcher.py`
- 修改 `/Users/jackkang/helloagents-deepresearch/backend/src/services/summarizer.py`（拆出 `_summarize_once`）
- 修改 `/Users/jackkang/helloagents-deepresearch/backend/src/prompts.py`（新增反思 prompt）
- 修改 `/Users/jackkang/helloagents-deepresearch/backend/src/main.py`（`Configuration` 默认 `max_web_research_loops` 建议 2）

### 3.2 P0：引用绑定（citation binding）

**思路**：搜索阶段给来源编 `[1][2]…` 序号；总结阶段强制 LLM 在引用信息时加 `[n]`；报告阶段汇总 References 列表。

**改造点**：

- `services/search.py` 增加 `prepare_research_context` 输出格式：
  - 每条结果前加 `[n] 标题 — URL`
  - `sources_summary` 改为 `[{id, title, url, snippet}, ...]`
- `TodoItem` 扩展：`citations: list[int]`（该任务引用了哪些编号）
- 新增 `prompts.py` 中的 `citation_directive`（中英），在 `task_summarizer_instructions` 中追加：要求 LLM 在引用具体信息时使用 `[n]` 标注
- `build_summary_prompt` 在上下文里附 `[n] 标题 — 摘录` 列表
- `reporter.py` 的最终报告尾部追加 `## 参考来源`，由所有任务的 citations 聚合去重

**受影响文件**：

- 修改 `/Users/jackkang/helloagents-deepresearch/backend/src/services/search.py`（序号化）
- 修改 `/Users/jackkang/helloagents-deepresearch/backend/src/models.py`（TodoItem.citations）
- 修改 `/Users/jackkang/helloagents-deepresearch/backend/src/prompts.py`（citation_directive）
- 修改 `/Users/jackkang/helloagents-deepresearch/backend/src/services/summarizer.py`（构造带 [n] 的上下文）
- 修改 `/Users/jackkang/helloagents-deepresearch/backend/src/services/reporter.py`（拼装 References 段）
- 修改 `/Users/jackkang/helloagents-deepresearch/backend/src/services/event_adapter.py`（SSE 事件 `sources` 改为结构化 list）

### 3.3 P1：planner 结构化输出

**思路**：用 LangChain 的 `with_structured_output(TaskPlan)` 强约束 planner JSON；失败时再回落手写解析。

**改造点**：

- 在 `models.py` 新增 `TaskPlan(BaseModel)`：`tasks: list[PlannerTaskItem]`，每项含 `title / intent / query`
- `services/planner.py`：`llm.with_structured_output(TaskPlan).invoke(...)` 优先路径
- 失败/不支持时退回现有 `_extract_tasks`
- 行为变化：planner 更稳定，无需 LLM 理解 `[TOOL_CALL:todo:...]` 自定义格式

**受影响文件**：

- 修改 `/Users/jackkang/helloagents-deepresearch/backend/src/models.py`（新增 TaskPlan）
- 修改 `/Users/jackkang/helloagents-deepresearch/backend/src/services/planner.py`（结构化输出路径）
- 修改 `/Users/jackkang/helloagents-deepresearch/backend/src/prompts.py`（planner 提示改为 JSON 风格说明）

### 3.4 P2：检索片段相关性压缩

**思路**：避免整页塞 prompt，对抓取的多片段做与 query 的简单相关度过滤（BM25 简化版或句子级关键词匹配），保留 Top-K。

**改造点**：

- `services/text_processing.py` 新增 `filter_relevant_snippets(snippets, query, top_k=8) -> list[Snippet]`
- `prepare_research_context` 调用该函数后再拼接
- 不引入外部 embedding 依赖，保持轻量

**受影响文件**：

- 修改 `/Users/jackkang/helloagents-deepresearch/backend/src/services/text_processing.py`
- 修改 `/Users/jackkang/helloagents-deepresearch/backend/src/services/search.py`（拼接前过滤）

### 3.5 P2：报告分节生成

**思路**：按 todo_items 分节生成再拼装，避免单次长 prompt 质量下降。

**改造点**：

- `services/reporter.py` 拆出 `generate_section_markdown(task, cfg) -> str`
- `report_node` 改为：先并行/串行生成每节，最后拼装 + 报告级 LLM 整合
- 提示词新增 `section_writer_instructions`

**受影响文件**：

- 修改 `/Users/jackkang/helloagents-deepresearch/backend/src/services/reporter.py`
- 修改 `/Users/jackkang/helloagents-deepresearch/backend/src/prompts.py`

## 4. 数据流（升级后）

```
plan (with_structured_output) → TodoItems
  → research_node (per task)
      loop 1..max_loops:
        search (snippet filter) → [n] 序号化 sources
        summarize with citation_directive → summary + citations
        reflect → {is_sufficient, follow_up_query}
        if is_sufficient: break
  → report_node (分节 → 整合 → References)
  → persist
```

## 5. 边界条件与异常处理

- 反思循环单次失败：捕获异常后跳出循环，使用已积累的 summary，不阻断整次研究
- structured_output 不支持的 provider：自动回落手写解析
- 检索片段全被过滤：返回 "无可用信息" 而非空字符串
- 引用编号冲突：每任务独立从 1 开始编号，报告阶段做全局去重映射

## 6. 验收标准

1. 现有 8 个测试全部通过；新增 ≥ 4 个测试覆盖反思、引用、结构化输出
2. 反思循环生效：`max_web_research_loops=2` 时，单任务至少能见到 2 次 `sources` 事件
3. 引用锚点：报告正文中出现 `[1][2]` 形式引用，且末尾有 `## 参考来源` 列表
4. planner 结构化输出：mock LLM 直接返回 JSON，验证 `plan_node` 不走工具调用解析路径
5. 检索片段过滤：构造 10 条 snippets，验证仅 Top-K 与 query 相关的被保留

## 7. 任务优先级

| 优先级 | 内容 |
|---|---|
| P0 | 3.1 反思循环、3.2 引用绑定 |
| P1 | 3.3 planner 结构化输出 |
| P2 | 3.4 检索片段过滤、3.5 报告分节生成 |
