# 更新日志

**English** | 简体中文

本项目的所有重要变更都会记录在此文件中。
格式基于 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
项目遵循 [语义化版本](https://semver.org/spec/v2.0.0.html) 规范。

## [Unreleased]

## [0.2.0] - 2026-06-01

### 新增
- 质量基础脚手架:pytest 脚手架(`tests/unit` 与 `tests/integration` 共 8 个测试)。
- `Configuration` 字段扩展:`llm_timeout`、`host`、`port`、`cors_origins`、`log_level`,以及 `parse_cors_origins` 校验器。
- `SearchAPI.ADVANCED` 后端,在 `tavily / duckduckgo / searxng / perplexity` 上扇出,每个后端异常隔离。
- `.comate/specs/quality-foundation-harness/` 设计规范、摘要与任务清单。
- CI 工作流(通过 `uv` 运行 lint + tests)。

### 变更
- `main.py` 现在从 `Configuration.from_env()` 读取 `host` / `port` / `cors_origins` / `log_level`,不再使用硬编码值。

## [0.1.0] - 2026-05-23

### 新增
- 初始提交:DeepResearch on LangGraph。
- LangGraph StateGraph 流水线:`plan → research → report → persist`。
- 五个搜索后端:`duckduckgo`、`tavily`、`perplexity`、`searxng`、`advanced`。
- Vue 3 + Vite 前端,支持 SSE 流式输出。
- Markdown 笔记持久化,保存于 `backend/notes/`。
