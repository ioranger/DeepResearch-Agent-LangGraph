# Quality Foundation Harness 实施总结

## 完成内容

### 1. 后端测试依赖配置

已更新 `/Users/jackkang/helloagents-deepresearch/backend/pyproject.toml`：

- 在 `[project.optional-dependencies].dev` 中加入：
  - `pytest>=8.0.0`
  - `pytest-asyncio>=0.23.0`
  - `httpx>=0.27.0`
- 在 `[dependency-groups].dev` 中同步加入上述测试依赖。
- 保留原有 `mypy`、`ruff` 配置。

### 2. 配置一致性修正

已扩展 `/Users/jackkang/helloagents-deepresearch/backend/src/config.py`：

- 新增 `llm_timeout`、`host`、`port`、`cors_origins`、`log_level` 字段。
- 新增 `parse_cors_origins` validator，用于解析逗号分隔的 `CORS_ORIGINS`。
- 在 `Configuration.from_env` 中加入新增字段的环境变量映射。

已更新 `/Users/jackkang/helloagents-deepresearch/backend/src/main.py`：

- 日志 handler 使用 `startup_config.log_level.upper()`。
- `create_app()` 使用 `config.cors_origins` 配置 CORS。
- `uvicorn.run` 使用 `config.host`、`config.port`、`config.log_level.lower()`。

### 3. advanced 搜索后端

已更新 `/Users/jackkang/helloagents-deepresearch/backend/src/services/search.py`：

- 在 `dispatch_search` handler map 中注册 `advanced`。
- 新增 `_search_advanced`，聚合：
  - Tavily
  - DuckDuckGo
  - SearXNG
  - Perplexity
- 每个后端独立异常隔离。
- 汇总 `results`、`notices`、`answer`。
- 避免 `advanced` 静默 fallback 到 DuckDuckGo。

### 4. 后端测试 harness

新增测试结构：

```text
backend/tests/
├── conftest.py
├── integration/
│   └── test_api.py
└── unit/
    ├── test_config.py
    ├── test_models.py
    └── test_search.py
```

覆盖内容：

- `test_config.py`
  - search_api override 解析。
  - `CORS_ORIGINS` 逗号分隔解析。
  - `PORT`、`LLM_TIMEOUT` 数值环境变量转换。

- `test_models.py`
  - `merge_todos` 相同 id 后写覆盖。
  - 任务首次出现顺序保持。
  - 空列表边界行为。

- `test_search.py`
  - monkeypatch 各搜索后端。
  - 验证 `advanced` 聚合结果、answer、notices。
  - 验证单后端异常不会中断整体搜索。

- `test_api.py`
  - `/healthz` 返回 `{"status": "ok"}`。
  - mock `DeepResearchAgent.run_stream`，验证 `/research/stream` SSE 协议包含 `status`、`todo_list`、`final_report`、`done`。

## 验证结果

执行命令：

```bash
cd /Users/jackkang/helloagents-deepresearch/backend
uv run pytest
```

结果：

```text
8 passed, 6 warnings in 0.43s
```

说明：

- `python -m pytest` 未执行成功，因为当前 shell 中没有 `python` 命令。
- `python3 -m pytest` 未执行成功，因为系统 Python 未安装 pytest。
- 使用项目已有的 `uv run pytest` 成功安装/同步测试依赖并通过所有测试。

## 注意事项

测试通过时 FastAPI 输出了 `on_event` deprecated warning：

- 位置：`backend/src/main.py` 的 `@app.on_event("startup")`。
- 当前不影响功能和测试结果。
- 该问题不在本次 doc.md 范围内，后续可单独迁移到 lifespan handler。

## 任务状态

`.comate/specs/quality-foundation-harness/tasks.md` 中 5 个顶层任务均已完成。
