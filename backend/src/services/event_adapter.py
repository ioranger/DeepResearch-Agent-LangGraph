"""Adapter mapping LangGraph stream events to the legacy SSE event protocol.

Frontend consumes events of types:
  status / todo_list / task_status / sources / task_summary_chunk /
  tool_call / report_note / final_report / done
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from config import Configuration
from models import TodoItem

logger = logging.getLogger(__name__)


def _serialize_task(task: TodoItem) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "intent": task.intent,
        "query": task.query,
        "status": task.status,
        "summary": task.summary,
        "sources_summary": task.sources_summary,
        "note_id": task.note_id,
        "note_path": task.note_path,
        "stream_token": task.stream_token,
    }


async def stream_research_events(
    graph: Any,
    topic: str,
    config: Configuration,
) -> AsyncIterator[dict[str, Any]]:
    """Run the graph in streaming mode and yield SSE-ready event dicts."""
    yield {"type": "status", "message": "初始化研究流程"}

    runnable_config = {"configurable": {"app_config": config}}
    inputs = {"research_topic": topic}

    final_state: dict[str, Any] = {}
    todo_emitted = False
    step_counter = 0
    channel_map: dict[int, dict[str, Any]] = {}

    try:
        async for stream_mode, payload in graph.astream(
            inputs,
            config=runnable_config,
            stream_mode=["custom", "updates", "values"],
        ):
            if stream_mode == "values":
                final_state = payload  # latest snapshot
                continue

            if stream_mode == "custom":
                # research_node + persist_node already publish ready-to-use
                # SSE payloads via langgraph.config.get_stream_writer().
                yield payload
                continue

            if stream_mode == "updates":
                for node_name, node_output in (payload or {}).items():
                    if not isinstance(node_output, dict):
                        continue

                    # Plan completed → emit todo_list
                    if node_name == "plan" and not todo_emitted:
                        items = node_output.get("todo_items") or []
                        if items:
                            for index, t in enumerate(items, start=1):
                                channel_map[t.id] = {"step": index, "token": f"task_{t.id}"}
                            yield {
                                "type": "todo_list",
                                "tasks": [_serialize_task(t) for t in items],
                                "step": 0,
                            }
                            # in_progress notice for each task
                            for t in items:
                                step_counter += 1
                                yield {
                                    "type": "task_status",
                                    "task_id": t.id,
                                    "status": "in_progress",
                                    "title": t.title,
                                    "intent": t.intent,
                                    "note_id": t.note_id,
                                    "note_path": t.note_path,
                                    "step": channel_map.get(t.id, {}).get("step"),
                                }
                            todo_emitted = True

                    # Research completed (per parallel branch) → emit task_status
                    if node_name == "research":
                        items = node_output.get("todo_items") or []
                        for t in items:
                            yield {
                                "type": "task_status",
                                "task_id": t.id,
                                "status": t.status,
                                "title": t.title,
                                "intent": t.intent,
                                "summary": t.summary,
                                "sources_summary": t.sources_summary,
                                "note_id": t.note_id,
                                "note_path": t.note_path,
                                "step": channel_map.get(t.id, {}).get("step"),
                            }

                    # Report node completed → capture structured_report incrementally
                    if node_name == "report":
                        report_text = node_output.get("structured_report")
                        if report_text:
                            final_state["structured_report"] = report_text

                    # Persist updates need no extra mapping; persist
                    # already pushed `report_note` via custom stream.
    except Exception as exc:
        logger.exception("Streaming research failed during streaming: %s", exc)
        yield {"type": "error", "code": "STREAM_FAILED", "detail": str(exc)}
        yield {"type": "done"}
        return

    # Build final report from incremental updates (no secondary graph.ainvoke!)
    report = final_state.get("structured_report") or ""
    yield {
        "type": "final_report",
        "report": report,
        "note_id": final_state.get("report_note_id"),
        "note_path": final_state.get("report_note_path"),
    }
    yield {"type": "done"}
