# Quality Foundation Harness 需求设计

## 背景与目标

当前项目是一个前后端分离的 Deep Research 原型：后端使用 FastAPI 暴露 `/healthz`、`/research`、`/research/stream`，核心研究流程由 LangGraph 在 `agent.py` 中以 `plan -> research -> report -> persist` 图结构编排；前端通过 `frontend/src/services/api.ts` 请求 `/research/stream` 并解析 SSE 事件。

现状问题：

- 项目没有自动化测试文件。
- `backend/pyproject.toml` 的 dev 依赖只有 `mypy`、`ruff`，缺少测试运行依赖。
- `backend/.env.example` 包含 `HOST`、`PORT`、`CORS_ORIGINS`、`LOG_LEVEL`、`LLM_TIMEOUT`，但后端配置模型并未全部覆盖这些字段。
- `SearchAPI` 和前端提供 `advanced` 搜索选项，但 `dispatch_search` 未实现 `advanced` handler，会静默 fallback 到 DuckDuckGo。
- SSE 事件协议是前后端耦合点，但没有测试保护。

本次需求目标是建立“质量基础 harness”，用最小、可维护的改动提升项目可验证性和配置一致性。

## 范围

### 包含

1. 后端最小测试 harness
   - 增加 pytest 相关 dev 依赖。
   - 增加 `tests` 目录。
   - 覆盖配置加载、状态合并、健康检查、SSE 协议。
   - 使用 monkeypatch/mock 避免真实 LLM、真实搜索、真实网络依赖。

2. 配置一致性修正
   - 让 `HOST`、`PORT`、`CORS_ORIGINS`、`LOG_LEVEL`、`LLM_TIMEOUT` 进入 `Configuration`。
   - `main.py` 使用配置中的 CORS、host、port、log level。
   - 保持现有默认行为尽量不变：默认 host `0.0.0.0`、port `8000`、log level `INFO`。

3. advanced 搜索选项修正
   - 保持前端现有 `advanced` 选项。
   - 后端明确实现 `advanced` handler，初始策略采用“聚合可用后端”的轻量实现。
   - 优先尝试 Tavily、DuckDuckGo、SearXNG、Perplexity，合并结果，记录不可用后端 notices。
   - 避免 `advanced` 静默退化为 DuckDuckGo。

4. SSE 协议测试
   - mock `DeepResearchAgent.run_stream`，验证 `/research/stream` 返回 `text/event-stream`。
   - 验证输出包含 `status`、`todo_list`、`final_report`、`done`。

### 不包含

- 不拆分 `frontend/src/App.vue`。
- 不新增完整 README。
- 不引入前端测试框架。
- 不重构 LangGraph 节点设计。
- 不实现完整 eval benchmark。
- 不改动 LLM prompt 或报告质量逻辑。

## 受影响文件

### 修改文件

1. `/Users/jackkang/helloagents-deepresearch/backend/pyproject.toml`
   - 修改类型：更新 dev 依赖。
   - 影响位置：`[project.optional-dependencies] dev`、`[dependency-groups] dev`。
   - 目标：加入 `pytest`、`pytest-asyncio`、`httpx`。

2. `/Users/jackkang/helloagents-deepresearch/backend/src/config.py`
   - 修改类型：扩展 `Configuration` 字段与 env alias。
   - 影响函数/类：`Configuration`、`Configuration.from_env`。
   - 新增字段：
     - `host: str`
     - `port: int`
     - `cors_origins: list[str]`
     - `log_level: str`
     - `llm_timeout: int`
   - 注意：`cors_origins` 需要支持环境变量逗号分隔字符串，例如 `http://localhost:5173,http://localhost:3000`。

3. `/Users/jackkang/helloagents-deepresearch/backend/src/main.py`
   - 修改类型：使用配置驱动 CORS、日志级别、uvicorn host/port。
   - 影响函数：`create_app`、`log_startup_configuration`、`__main__` 启动段。
   - 目标：避免 `.env.example` 与实际代码漂移。

4. `/Users/jackkang/helloagents-deepresearch/backend/src/services/search.py`
   - 修改类型：新增 advanced 搜索 handler。
   - 影响函数：`dispatch_search`，新增 `_search_advanced`。
   - 目标：`SearchAPI.ADVANCED` 有明确行为。

### 新增文件

1. `/Users/jackkang/helloagents-deepresearch/backend/tests/conftest.py`
   - 用途：测试导入路径设置，确保能从 `backend/src` 导入模块。

2. `/Users/jackkang/helloagents-deepresearch/backend/tests/unit/test_config.py`
   - 用途：测试 env/override 配置加载、CORS 字符串解析、类型转换。

3. `/Users/jackkang/helloagents-deepresearch/backend/tests/unit/test_models.py`
   - 用途：测试 `merge_todos` 后写覆盖、顺序保持。

4. `/Users/jackkang/helloagents-deepresearch/backend/tests/unit/test_search.py`
   - 用途：测试 `advanced` handler 会聚合后端结果并返回 backend=`advanced`。

5. `/Users/jackkang/helloagents-deepresearch/backend/tests/integration/test_api.py`
   - 用途：测试 `/healthz` 和 `/research/stream` 协议。

## 处理逻辑

### 配置加载逻辑

`Configuration.from_env` 当前按字段名自动读取大写环境变量，并额外显式读取 alias。新增字段后继续复用这一路径。

需要为 `cors_origins` 增加解析能力：

```python
@field_validator("cors_origins", mode="before")
@classmethod
def parse_cors_origins(cls, value):
    if value is None:
        return ["*"]
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
        return items or ["*"]
    return value
```

预期：

- 未配置时默认 `['*']`，保持当前开放 CORS 行为。
- 配置 `CORS_ORIGINS=http://localhost:5173,http://localhost:3000` 时解析为两个 origin。

### main.py 使用配置

`create_app` 中：

```python
config = Configuration.from_env()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

日志 handler 的 level 使用 `Configuration.from_env().log_level.upper()`。

`uvicorn.run` 使用：

```python
config = Configuration.from_env()
uvicorn.run(
    "main:app",
    host=config.host,
    port=config.port,
    reload=True,
    log_level=config.log_level.lower(),
)
```

### advanced 搜索逻辑

新增 `_search_advanced(query, config)`：

```python
def _search_advanced(query: str, config: Configuration) -> dict[str, Any]:
    handlers = [_search_tavily, _search_ddg, _search_searxng, _search_perplexity]
    results = []
    notices = []
    answers = []
    for handler in handlers:
        payload = handler(query, config)
        results.extend(payload.get("results") or [])
        notices.extend(payload.get("notices") or [])
        if payload.get("answer"):
            answers.append(str(payload["answer"]))
    return {
        "results": results,
        "backend": "advanced",
        "answer": "\n\n".join(answers) or None,
        "notices": notices,
    }
```

边界处理：

- 任一后端异常不应导致整体失败。
- 单个后端异常应进入 notices。
- `dispatch_search` 外层已有异常兜底，但 `_search_advanced` 内部也应做到每个 handler 独立隔离。
- 不做复杂去重，保持改动最小；后续由 `deduplicate_and_format_sources` 负责格式化阶段去重。

### 测试 harness 逻辑

#### conftest.py

将 `/backend/src` 加入 `sys.path`，避免测试依赖安装包路径：

```python
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
```

#### 配置测试

覆盖：

- override `search_api="tavily"` 能解析为 `SearchAPI.TAVILY`。
- `CORS_ORIGINS` 逗号分隔字符串能解析为 list。
- `PORT`、`LLM_TIMEOUT` 能转换为 int。

#### 状态测试

覆盖：

- `merge_todos` 对相同 id 后写覆盖。
- 首次出现顺序保持。

#### 搜索测试

通过 monkeypatch 替换 `_search_tavily`、`_search_ddg` 等内部函数，避免真实网络：

- 返回不同 title/url。
- 验证 `dispatch_search` with `Configuration(search_api=SearchAPI.ADVANCED)` 返回 backend `advanced`。
- 验证结果合并。

#### API 测试

使用 `fastapi.testclient.TestClient`：

- `/healthz` 返回 `{"status": "ok"}`。
- monkeypatch `DeepResearchAgent.run_stream`，验证 `/research/stream` 返回 SSE 文本，包含关键事件。

## 数据流路径

### 普通测试数据流

```text
pytest
  ↓
conftest.py 设置 backend/src 导入路径
  ↓
unit tests 直接导入 config/models/search
  ↓
assert 纯函数和配置行为
```

### API 测试数据流

```text
pytest
  ↓
TestClient(create_app())
  ↓
POST /research/stream
  ↓
mock DeepResearchAgent.run_stream
  ↓
StreamingResponse 输出 data: {...}\n\n
  ↓
assert SSE 协议文本
```

### advanced 搜索数据流

```text
research_node
  ↓
dispatch_search(query, config, loop_count)
  ↓
backend == advanced
  ↓
_search_advanced
  ↓
多个 backend handler 独立执行
  ↓
合并 results / notices / answers
  ↓
prepare_research_context
```

## 边界条件与异常处理

1. `CORS_ORIGINS` 为空字符串
   - 解析为 `['*']`。

2. `PORT` 非数字
   - Pydantic 抛出校验错误，保持 fail-fast。

3. advanced 某个后端缺 API key
   - 该后端返回 notice，不中断其他后端。

4. advanced 某个后端抛异常
   - 捕获异常并追加 notice。

5. SSE 测试不依赖真实 LLM
   - 使用 monkeypatch 固定事件序列。

6. 测试不写入真实 notes
   - 本次 API 测试不执行真实 agent，因此不会触发 note 持久化。

## 预期结果

完成后：

- `backend` 具备最小 pytest harness。
- `/healthz` 和 `/research/stream` 协议有自动化测试保护。
- 配置文件中的关键服务配置能被实际代码使用。
- `advanced` 搜索选项不再静默 fallback。
- 运行 `pytest` 可验证核心质量基础。

建议验证命令：

```bash
cd /Users/jackkang/helloagents-deepresearch/backend
python -m pytest
```

如果依赖尚未安装，则先安装 dev 依赖或使用项目已有包管理方式同步依赖。
