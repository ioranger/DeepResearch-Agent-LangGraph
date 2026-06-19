"""SSE protocol contract tests.

These tests verify that the /research/stream endpoint:
1. Returns text/event-stream content type
2. Emits ALL required event types in a complete run
3. Each event has the mandatory fields for its type
4. The event sequence ends with final_report followed by done
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from src.main import create_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_sse_events(response_text: str) -> list[dict]:
    """Parse raw SSE text into a list of event dicts."""
    events: list[dict] = []
    for block in response_text.split("\n\n"):
        block = block.strip()
        if not block or not block.startswith("data:"):
            continue
        payload = block[5:].strip()
        if payload:
            events.append(json.loads(payload))
    return events


def _install_mock_agent(monkeypatch, event_sequence: list[dict]) -> None:
    """Monkeypatch DeepResearchAgent to yield a fixed event sequence."""

    async def fake_astream(self, topic):
        for ev in event_sequence:
            yield ev

    monkeypatch.setattr("src.agent.DeepResearchAgent.astream", fake_astream)


# ---------------------------------------------------------------------------
# Contract: Content-Type
# ---------------------------------------------------------------------------

class TestSSEContentType:
    def test_returns_event_stream_content_type(self, monkeypatch, mock_agent_event_sequence):
        _install_mock_agent(monkeypatch, mock_agent_event_sequence)
        client = TestClient(create_app())
        resp = client.post("/research/stream", json={"topic": "test"})
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")


# ---------------------------------------------------------------------------
# Contract: Event type completeness
# ---------------------------------------------------------------------------

class TestSSEEventCompleteness:
    def test_all_required_event_types_present(
        self, monkeypatch, mock_agent_event_sequence, expected_sse_event_types
    ):
        _install_mock_agent(monkeypatch, mock_agent_event_sequence)
        client = TestClient(create_app())
        resp = client.post("/research/stream", json={"topic": "test"})
        events = _parse_sse_events(resp.text)
        actual_types = {e["type"] for e in events}

        missing = set(expected_sse_event_types) - actual_types
        assert not missing, f"Missing required event types: {missing}"

    def test_done_is_last_event(self, monkeypatch, mock_agent_event_sequence):
        _install_mock_agent(monkeypatch, mock_agent_event_sequence)
        client = TestClient(create_app())
        resp = client.post("/research/stream", json={"topic": "test"})
        events = _parse_sse_events(resp.text)

        assert len(events) >= 2, "Expected at least 2 events"
        assert events[-1]["type"] == "done", f"Last event must be 'done', got {events[-1]['type']}"

    def test_final_report_precedes_done(self, monkeypatch, mock_agent_event_sequence):
        _install_mock_agent(monkeypatch, mock_agent_event_sequence)
        client = TestClient(create_app())
        resp = client.post("/research/stream", json={"topic": "test"})
        events = _parse_sse_events(resp.text)
        types = [e["type"] for e in events]

        assert "final_report" in types, "final_report event missing"
        assert "done" in types, "done event missing"
        assert types.index("final_report") < types.index("done"), \
            "final_report must come before done"


# ---------------------------------------------------------------------------
# Contract: Event field validation
# ---------------------------------------------------------------------------

class TestSSEEventFields:
    def test_status_event_has_message(self, monkeypatch, mock_agent_event_sequence):
        _install_mock_agent(monkeypatch, mock_agent_event_sequence)
        client = TestClient(create_app())
        resp = client.post("/research/stream", json={"topic": "test"})
        events = _parse_sse_events(resp.text)

        status_events = [e for e in events if e["type"] == "status"]
        assert len(status_events) >= 1
        for ev in status_events:
            assert "message" in ev and isinstance(ev["message"], str)

    def test_todo_list_event_has_tasks(self, monkeypatch, mock_agent_event_sequence):
        _install_mock_agent(monkeypatch, mock_agent_event_sequence)
        client = TestClient(create_app())
        resp = client.post("/research/stream", json={"topic": "test"})
        events = _parse_sse_events(resp.text)

        todo_events = [e for e in events if e["type"] == "todo_list"]
        assert len(todo_events) == 1
        tasks = todo_events[0].get("tasks", [])
        assert isinstance(tasks, list) and len(tasks) >= 1
        for t in tasks:
            assert "id" in t and "title" in t

    def test_final_report_has_nonempty_report(self, monkeypatch, mock_agent_event_sequence):
        _install_mock_agent(monkeypatch, mock_agent_event_sequence)
        client = TestClient(create_app())
        resp = client.post("/research/stream", json={"topic": "test"})
        events = _parse_sse_events(resp.text)

        report_events = [e for e in events if e["type"] == "final_report"]
        assert len(report_events) == 1
        report = report_events[0].get("report", "")
        assert isinstance(report, str) and len(report) > 0

    def test_task_status_has_task_id_and_status(self, monkeypatch, mock_agent_event_sequence):
        _install_mock_agent(monkeypatch, mock_agent_event_sequence)
        client = TestClient(create_app())
        resp = client.post("/research/stream", json={"topic": "test"})
        events = _parse_sse_events(resp.text)

        ts_events = [e for e in events if e["type"] == "task_status"]
        assert len(ts_events) >= 1
        for ev in ts_events:
            assert "task_id" in ev
            assert "status" in ev
            assert ev["status"] in ("pending", "in_progress", "completed", "failed", "skipped")

    def test_sources_event_has_task_id(self, monkeypatch, mock_agent_event_sequence):
        _install_mock_agent(monkeypatch, mock_agent_event_sequence)
        client = TestClient(create_app())
        resp = client.post("/research/stream", json={"topic": "test"})
        events = _parse_sse_events(resp.text)

        src_events = [e for e in events if e["type"] == "sources"]
        assert len(src_events) >= 1
        for ev in src_events:
            assert "task_id" in ev


# ---------------------------------------------------------------------------
# Contract: Error handling
# ---------------------------------------------------------------------------

class TestSSEErrorHandling:
    def test_agent_exception_yields_error_then_done(self, monkeypatch):
        """When the agent's astream raises mid-stream, the event_adapter should
        catch it, emit an error event, and still emit done."""
        async def failing_astream(self, topic):
            yield {"type": "status", "message": "开始"}
            raise RuntimeError("LLM connection refused")

        monkeypatch.setattr("src.agent.DeepResearchAgent.astream", failing_astream)
        client = TestClient(create_app())
        resp = client.post("/research/stream", json={"topic": "test"})
        events = _parse_sse_events(resp.text)

        types = [e["type"] for e in events]
        # The stream should at least have the status event that was yielded
        assert "status" in types
        # The adapter should catch the error and end gracefully
        assert types[-1] == "done", f"Stream should end with done even after error, got: {types[-1]}"
