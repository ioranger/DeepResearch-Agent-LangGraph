"""Research node: thin shell delegating to iterative researcher."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.runnables import RunnableConfig

from src.config import Configuration
from src.models import ResearchTaskState, TodoItem
from src.services.researcher import iterative_research

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Build summary prompt (kept public for backward compatibility)
# ---------------------------------------------------------------------------
def build_summary_prompt(research_topic: str, task: TodoItem, context: str) -> str:
    """Construct the user prompt for the summarizer LLM call (single-pass)."""
    from src.services.notes import build_note_guidance

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


# ---------------------------------------------------------------------------
# Node entry
# ---------------------------------------------------------------------------
async def research_node(payload: ResearchTaskState, config: RunnableConfig) -> dict:
    """LangGraph node: delegate to iterative_research for multi-loop execution."""
    cfg: Configuration = config["configurable"]["app_config"]

    task: TodoItem = payload["task"] if isinstance(payload, dict) else payload.task
    if not isinstance(task, TodoItem):
        task = TodoItem(**task)
    research_topic = (
        payload.get("research_topic") if isinstance(payload, dict) else ""
    ) or ""

    return await iterative_research(task, research_topic, cfg)
