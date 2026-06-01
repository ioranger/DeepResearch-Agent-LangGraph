# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-06-01

### Added
- Quality foundation harness: pytest scaffolding (8 tests across `tests/unit` and `tests/integration`).
- `Configuration` field expansion: `llm_timeout`, `host`, `port`, `cors_origins`, `log_level`, plus a `parse_cors_origins` validator.
- `SearchAPI.ADVANCED` backend that fans out across `tavily / duckduckgo / searxng / perplexity` with per-backend exception isolation.
- `.comate/specs/quality-foundation-harness/` design spec, summary, and task checklist.
- CI workflow (lint + tests via `uv`).

### Changed
- `main.py` now sources `host` / `port` / `cors_origins` / `log_level` from `Configuration.from_env()` instead of hardcoded values.

## [0.1.0] - 2026-05-23

### Added
- Initial commit: DeepResearch on LangGraph.
- LangGraph StateGraph pipeline: `plan → research → report → persist`.
- Five search backends: `duckduckgo`, `tavily`, `perplexity`, `searxng`, `advanced`.
- Vue 3 + Vite frontend with SSE streaming.
- Markdown note persistence under `backend/notes/`.
