# Quality Foundation Harness 实施任务计划

- [x] Task 1: 更新后端测试依赖配置
    - 1.1: 在 `backend/pyproject.toml` 的 optional dev 依赖中加入 `pytest`、`pytest-asyncio`、`httpx`
    - 1.2: 在 `backend/pyproject.toml` 的 dependency group dev 中同步加入测试依赖
    - 1.3: 保持现有 `ruff`、`mypy` 配置不变

- [x] Task 2: 扩展运行配置并接入 main.py
    - 2.1: 在 `Configuration` 中新增 `host`、`port`、`cors_origins`、`log_level`、`llm_timeout` 字段
    - 2.2: 为 `cors_origins` 增加逗号分隔字符串解析逻辑
    - 2.3: 在 `Configuration.from_env` 中加入新增字段的环境变量映射
    - 2.4: 在 `main.py` 中使用 `config.cors_origins` 配置 CORS
    - 2.5: 在 `main.py` 中使用 `config.log_level` 配置日志 handler 级别
    - 2.6: 在 `main.py` 的 uvicorn 启动段使用 `config.host`、`config.port`、`config.log_level`

- [x] Task 3: 实现 advanced 搜索后端
    - 3.1: 在 `dispatch_search` 的 handler map 中注册 `advanced`
    - 3.2: 新增 `_search_advanced` 聚合 Tavily、DuckDuckGo、SearXNG、Perplexity 搜索结果
    - 3.3: 为 `_search_advanced` 增加单后端异常隔离和 notices 汇总
    - 3.4: 保持 `prepare_research_context` 和现有搜索后端行为不变

- [x] Task 4: 创建后端测试 harness 基础结构
    - 4.1: 创建 `backend/tests/conftest.py` 并加入 `backend/src` 导入路径
    - 4.2: 创建 `backend/tests/unit/test_config.py` 覆盖配置 override、CORS 解析、数值环境变量转换
    - 4.3: 创建 `backend/tests/unit/test_models.py` 覆盖 `merge_todos` 后写覆盖和顺序保持
    - 4.4: 创建 `backend/tests/unit/test_search.py` 覆盖 advanced 搜索聚合行为
    - 4.5: 创建 `backend/tests/integration/test_api.py` 覆盖 `/healthz` 和 `/research/stream` SSE 协议

- [x] Task 5: 运行后端测试并修复问题
    - 5.1: 在 `backend` 目录运行 `python -m pytest`
    - 5.2: 如存在导入、依赖或断言失败，按最小改动修复
    - 5.3: 重新运行测试确认通过
    - 5.4: 检查实现是否仍符合 doc.md 的范围约束
