# Quality Foundation Harness 任务拆解

- [x] Task 1: 补充测试依赖与配置模型扩展
    - 1.1: 更新 `backend/pyproject.toml`，在 dev 依赖中加入 `pytest`、`pytest-asyncio`、`httpx`
    - 1.2: 修改 `backend/src/config.py`，向 `Configuration` 模型中补充 `host` (默认 0.0.0.0)、`port` (默认 8000)、`cors_origins`、`log_level` (默认 INFO)、`llm_timeout` 字段
    - 1.3: 在 `Configuration` 中实现 `cors_origins` 的 `field_validator`，以支持环境变量逗号分隔的字符串解析为列表

- [x] Task 2: 修正 main.py 使得服务使用最新的统一配置
    - 2.1: 修改 `backend/src/main.py` 中的 `CORSMiddleware` 注册逻辑，使用 `config.cors_origins`
    - 2.2: 调整 `logger.add` 的日志级别，使用 `config.log_level`
    - 2.3: 在文件末尾的 `uvicorn.run` 调用中，使用 `config.host`、`config.port` 和 `config.log_level`

- [ ] Task 3: 实现 Advanced 聚合搜索策略
    - 3.1: 在 `backend/src/services/search.py` 中新增 `_search_advanced` 处理器
    - 3.2: 隔离并聚合调用 `_search_tavily`、`_search_ddg`、`_search_searxng`、`_search_perplexity`，捕获异常并整理 notices 与合并结果
    - 3.3: 调整 `dispatch_search`，当配置的后端为 `SearchAPI.ADVANCED` 时，正确路由至 `_search_advanced`

- [ ] Task 4: 编写基础测试用例文件
    - 4.1: 新建 `backend/tests/conftest.py`，将 `backend/src` 动态插入至 `sys.path` 中
    - 4.2: 新建 `backend/tests/unit/test_config.py`，验证配置重载、类型转换与 CORS 字符串的按逗号解析行为
    - 4.3: 新建 `backend/tests/unit/test_models.py`，验证 `merge_todos` 的后写覆盖与顺序保持行为
    - 4.4: 新建 `backend/tests/unit/test_search.py`，通过 monkeypatch mock 内置搜索方法，测试 `advanced` 聚合和隔离行为
    - 4.5: 新建 `backend/tests/integration/test_api.py`，使用 `TestClient` 测试 `/healthz`，并 mock `DeepResearchAgent.astream` 测试 SSE 的基础事件流输出协议
