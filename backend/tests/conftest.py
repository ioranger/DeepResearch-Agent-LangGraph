from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import Configuration, SearchAPI
from src.models import TodoItem


# ---------------------------------------------------------------------------
# Configuration fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_config() -> Configuration:
    """Isolated test config that does NOT read the real .env file."""
    return Configuration(
        llm_provider="custom",
        llm_model_id="test-model",
        llm_api_key="fake-key-for-testing",
        llm_base_url="http://localhost:9999/v1",
        search_api=SearchAPI.TAVILY,
        tavily_api_key="fake-tavily-key",
        max_web_research_loops=1,
        cors_origins=["http://localhost:5173", "http://localhost:5174"],
        host="127.0.0.1",
        port=9999,
        log_level="DEBUG",
        llm_timeout=5,
    )


@pytest.fixture
def mock_ddg_config() -> Configuration:
    """Config that uses DuckDuckGo (no API key needed)."""
    return Configuration(
        llm_provider="custom",
        llm_model_id="test-model",
        llm_api_key="fake-key",
        search_api=SearchAPI.DUCKDUCKGO,
    )


# ---------------------------------------------------------------------------
# Search result fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_search_results() -> dict:
    """Standardized search results for all search-related tests."""
    return {
        "results": [
            {
                "title": "Quantum Computing Overview",
                "url": "https://example.com/quantum",
                "content": "Quantum computing uses qubits for parallel computation.",
            },
            {
                "title": "Qubits Explained",
                "url": "https://example.com/qubits",
                "content": "A qubit can represent 0, 1, or both simultaneously.",
            },
        ],
        "backend": "tavily",
        "answer": "Quantum computing leverages quantum mechanics.",
        "notices": [],
    }


@pytest.fixture
def mock_empty_search_results() -> dict:
    """Empty results to test edge cases."""
    return {"results": [], "backend": "duckduckgo", "answer": None, "notices": []}


# ---------------------------------------------------------------------------
# TodoItem fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_todo_items() -> list[TodoItem]:
    """Standardized task list for planner/reporter tests."""
    return [
        TodoItem(id=1, title="Background Research", intent="Understand the topic background", query="quantum computing basics"),
        TodoItem(id=2, title="Technical Analysis", intent="Analyze technical challenges", query="quantum computing challenges"),
        TodoItem(id=3, title="Future Outlook", intent="Explore future trends", query="quantum computing future"),
    ]


@pytest.fixture
def mock_completed_todo_items(mock_todo_items: list[TodoItem]) -> list[TodoItem]:
    """All tasks marked as completed with summaries."""
    for item in mock_todo_items:
        item.status = "completed"
        item.summary = f"Summary for {item.title}"
        item.sources_summary = f"[1] {item.title} — https://example.com/{item.id}"
    return mock_todo_items


# ---------------------------------------------------------------------------
# SSE event sequence fixture (Contract Test data)
# ---------------------------------------------------------------------------

@pytest.fixture
def expected_sse_event_types() -> list[str]:
    """The complete set of event types the SSE protocol MUST emit."""
    return [
        "status",
        "todo_list",
        "task_status",
        "sources",
        "task_summary_chunk",
        "final_report",
        "done",
    ]


@pytest.fixture
def mock_agent_event_sequence():
    """A complete, realistic SSE event sequence for contract testing.

    Yields a list of dicts representing a full research run lifecycle.
    """
    return [
        {"type": "status", "message": "初始化研究流程"},
        {
            "type": "todo_list",
            "tasks": [
                {
                    "id": 1,
                    "title": "测试任务",
                    "intent": "验证 SSE 协议",
                    "query": "SSE protocol test",
                    "status": "pending",
                    "summary": None,
                    "sources_summary": None,
                    "note_id": None,
                    "note_path": None,
                }
            ],
            "step": 0,
        },
        {"type": "task_status", "task_id": 1, "status": "in_progress", "title": "测试任务"},
        {
            "type": "sources",
            "task_id": 1,
            "latest_sources": [{"id": 1, "title": "来源A", "url": "https://a.com", "snippet": "片段A"}],
            "backend": "tavily",
        },
        {"type": "task_summary_chunk", "task_id": 1, "content": "这是摘要内容"},
        {"type": "task_status", "task_id": 1, "status": "completed", "title": "测试任务", "summary": "完成"},
        {"type": "final_report", "report": "# 测试报告\n\n这是报告内容。"},
        {"type": "done"},
    ]
