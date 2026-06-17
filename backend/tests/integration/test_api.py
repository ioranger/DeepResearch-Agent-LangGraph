from __future__ import annotations

from fastapi.testclient import TestClient

from src.main import create_app


def test_healthz() -> None:
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_research_stream_sse_protocol(monkeypatch) -> None:
    def fake_run_stream(self, topic):
        yield {"type": "status", "message": "初始化研究流程"}
        yield {
            "type": "todo_list",
            "tasks": [
                {
                    "id": 1,
                    "title": "背景梳理",
                    "intent": "了解背景",
                    "query": topic,
                    "status": "pending",
                    "summary": None,
                    "sources_summary": None,
                    "note_id": None,
                    "note_path": None,
                }
            ],
            "step": 0,
        }
        yield {"type": "final_report", "report": "测试报告"}
        yield {"type": "done"}

    monkeypatch.setattr("src.agent.DeepResearchAgent.run_stream", fake_run_stream)

    client = TestClient(create_app())
    response = client.post(
        "/research/stream",
        json={"topic": "AI Agent 架构", "search_api": "duckduckgo"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    text = response.text
    assert "data:" in text
    assert '"type": "status"' in text
    assert '"type": "todo_list"' in text
    assert '"type": "final_report"' in text
    assert '"type": "done"' in text
