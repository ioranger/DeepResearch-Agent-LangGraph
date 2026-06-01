"""Research node: search + streaming summarization for a single TodoItem."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer

from config import Configuration
from llm import build_chat_model
from models import ResearchTaskState, TodoItem
from prompts import get_prompt
from services.notes import build_note_guidance
from services.search import dispatch_search, prepare_research_context
from services.text_processing import strip_tool_calls
from utils import strip_thinking_tokens

logger = logging.getLogger(__name__)


def build_summary_prompt(research_topic: str, task: TodoItem, context: str) -> str:
    """Construct the user prompt for the summarizer LLM call."""
    note_guidance = build_note_guidance(task)
    return (
        f"研究主题：{research_topic}\n"
        f"任务标题：{task.title}\n"
        f"任务意图：{task.intent}\n"
        f"检索关键词：{task.query}\n\n"
        f"上下文资料：\n{context}\n\n"
        f"{note_guidance}\n"
        "请输出严格符合格式要求的任务总结。"
    )


def _emit(event: dict[str, Any]) -> None:
    """Best-effort push to the LangGraph custom stream writer."""
    try:
        writer = get_stream_writer()
        writer(event)
    except Exception:
        # Outside a streaming context, just drop.
        pass


async def research_node(payload: ResearchTaskState, config: RunnableConfig) -> dict:
    """Process one TodoItem: search → summarize (streaming)."""
    cfg: Configuration = config["configurable"]["app_config"]

    task: TodoItem = payload["task"] if isinstance(payload, dict) else payload.task  # type: ignore[attr-defined]
    if not isinstance(task, TodoItem):
        task = TodoItem(**task)  # type: ignore[arg-type]
    research_topic = (
        payload.get("research_topic") if isinstance(payload, dict) else ""
    ) or ""

    task = task.model_copy()
    task.status = "in_progress"

    try:
        # 1. Search ----------------------------------------------------
        search_payload, notices, answer_text, backend = await asyncio.to_thread(
            dispatch_search, task.query, cfg, 0
        )
        task.notices = notices

        for notice in notices or []:
            if notice:
                _emit({"type": "status", "message": notice, "task_id": task.id})

        results = (search_payload or {}).get("results") if search_payload else None
        if not results:
            task.status = "skipped"
            return {"todo_items": [task]}

        sources_summary, context = prepare_research_context(
            search_payload, answer_text, cfg
        )
        task.sources_summary = sources_summary

        _emit(
            {
                "type": "sources",
                "task_id": task.id,
                "latest_sources": sources_summary,
                "raw_context": context,
                "backend": backend,
                "note_id": task.note_id,
                "note_path": task.note_path,
            }
        )

        # 2. Summarize (streaming tokens) ------------------------------
        llm = build_chat_model(cfg)
        prompt = build_summary_prompt(research_topic, task, context)
        chunks: list[str] = []
        try:
            async for chunk in llm.astream(
                [
                    SystemMessage(content=get_prompt("task_summarizer_instructions", cfg.locale).strip()),
                    HumanMessage(content=prompt),
                ]
            ):
                text = getattr(chunk, "content", "") or ""
                if not text:
                    continue
                chunks.append(text)
                _emit(
                    {
                        "type": "task_summary_chunk",
                        "task_id": task.id,
                        "content": text,
                        "note_id": task.note_id,
                    }
                )
        except Exception as exc:
            logger.warning("Streaming summary failed for task %s: %s", task.id, exc)

        raw_summary = "".join(chunks)
        cleaned = strip_tool_calls(
            strip_thinking_tokens(raw_summary) if cfg.strip_thinking_tokens else raw_summary
        ).strip()
        task.summary = cleaned or "暂无可用信息"
        task.status = "completed"

        return {
            "todo_items": [task],
            "web_research_results": [context],
            "sources_gathered": [sources_summary],
            "research_loop_count": 1,
        }

    except Exception as exc:  # pragma: no cover - per-task isolation
        logger.exception("Task %s execution failed", task.id, exc_info=exc)
        task.status = "failed"
        task.summary = f"任务执行失败：{exc}"
        return {"todo_items": [task]}
