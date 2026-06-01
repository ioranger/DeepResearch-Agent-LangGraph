# 示例报告:针对 2026 行业趋势的 advanced-search 研究

**English** | 简体中文

> **状态:** 占位文件。仅为 `examples/` 目录占位生成。
> 在发布 v0.3 之前,请替换为 agent 真实生成的报告。

## 主题

梳理 2026 年本地 LLM 服务的现状:哪些运行时(Ollama、LMStudio、vLLM、llama.cpp)
占据采用率领先位置,今年又出现了哪些新的模型家族。

## 预期输入

- `SEARCH_API=advanced`(在 tavily + ddg + searxng + perplexity 上扇出)
- `LLM_PROVIDER=custom`,`LLM_MODEL_ID=<推理模型>`

## 预期 todo 列表

1. 通过 Tavily 拉取 2026 年最近的基准测试文章。
2. 通过 SearXNG / DuckDuckGo 交叉验证社区讨论。
3. 通过 Perplexity 拉取一份综合回答。
4. 整合信源并撰写最终报告。

## 维护者备注

一旦 `advanced` 后端被端到端运行,请把生成的 Markdown 放在这里。
占位文件刻意留空,这样在 `git diff` 中能清楚看到这是真实输出,而不是模板内容。
