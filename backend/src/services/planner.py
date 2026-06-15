"""Planner node for the LangGraph deep research workflow."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from config import Configuration
from llm import build_chat_model
from models import PlannerTaskItem, ResearchState, TaskPlan, TodoItem
from prompts import (
    get_current_date,
    get_prompt,
)
from utils import strip_thinking_tokens

logger = logging.getLogger(__name__)

TOOL_CALL_PATTERN = re.compile(
    r"\[TOOL_CALL:(?P<tool>[^:]+):(?P<body>[^\]]+)\]",
    re.IGNORECASE,
)


# ----------------------------------------------------------------------
# Pure parsing helpers
# ----------------------------------------------------------------------
def _extract_json_payload(text: str) -> Optional[Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


def _extract_tool_payload(text: str) -> Optional[dict[str, Any]]:
    match = TOOL_CALL_PATTERN.search(text)
    if not match:
        return None
    body = match.group("body")
    try:
        payload = json.loads(body)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass
    parts = [seg.strip() for seg in body.split(",") if seg.strip()]
    payload = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        payload[key.strip()] = value.strip().strip('"').strip("'")
    return payload or None


def _extract_tasks(raw_response: str, *, strip_thinking: bool) -> List[dict[str, Any]]:
    text = (raw_response or "").strip()
    if strip_thinking:
        text = strip_thinking_tokens(text)

    payload = _extract_json_payload(text)
    tasks: List[dict[str, Any]] = []
    if isinstance(payload, dict):
        candidate = payload.get("tasks")
        if isinstance(candidate, list):
            tasks = [it for it in candidate if isinstance(it, dict)]
    elif isinstance(payload, list):
        tasks = [it for it in payload if isinstance(it, dict)]

    if not tasks:
        tool_payload = _extract_tool_payload(text)
        if tool_payload and isinstance(tool_payload.get("tasks"), list):
            tasks = [it for it in tool_payload["tasks"] if isinstance(it, dict)]

    return tasks


def create_fallback_task(research_topic: str) -> TodoItem:
    return TodoItem(
        id=1,
        title="基础背景梳理",
        intent="收集主题的核心背景与最新动态",
        query=f"{research_topic} 最新进展" if research_topic else "基础背景梳理",
    )


# ----------------------------------------------------------------------
# Node entry
# ----------------------------------------------------------------------
def plan_node(state: ResearchState, config: RunnableConfig) -> dict:
    """LangGraph node: ask LLM to decompose research_topic into TodoItems.

    Tries structured output (``with_structured_output(TaskPlan)``) first;
    falls back to manual JSON extraction if the provider doesn't support it.
    """
    cfg: Configuration = config["configurable"]["app_config"]
    topic = state.get("research_topic", "") or ""

    prompt = get_prompt("todo_planner_instructions", cfg.locale).format(
        current_date=get_current_date(),
        research_topic=topic,
    )

    llm = build_chat_model(cfg)

    # ------------------------------------------------------------------
    # Path 1: Structured output (preferred)
    # ------------------------------------------------------------------
    try:
        structured_llm = llm.with_structured_output(TaskPlan)
        plan: TaskPlan = structured_llm.invoke(
            [
                SystemMessage(content=get_prompt("todo_planner_system_prompt", cfg.locale).strip()),
                HumanMessage(content=prompt),
            ]
        )
        if plan and plan.tasks:
            todo_items: list[TodoItem] = []
            for idx, item in enumerate(plan.tasks, start=1):
                title = str(item.title or f"任务{idx}").strip()
                intent = str(item.intent or "聚焦主题的关键问题").strip()
                query = str(item.query or topic).strip() or topic
                todo_items.append(TodoItem(id=idx, title=title, intent=intent, query=query))
            logger.info("Planner (structured) produced %d tasks: %s", len(todo_items), [t.title for t in todo_items])
            return {"todo_items": todo_items}
    except (NotImplementedError, TypeError, ValueError) as exc:
        logger.info("Structured output not supported (%s); falling back to manual parse", exc)
    except Exception as exc:
        logger.warning("Structured output failed (%s); falling back to manual parse", exc)

    # ------------------------------------------------------------------
    # Path 2: Manual parse (fallback)
    # ------------------------------------------------------------------
    try:
        response = llm.invoke(
            [
                SystemMessage(content=get_prompt("todo_planner_system_prompt", cfg.locale).strip()),
                HumanMessage(content=prompt),
            ]
        )
        raw = getattr(response, "content", "") or ""
    except Exception as exc:
        logger.warning("Planner LLM call failed: %s", exc)
        return {"todo_items": [create_fallback_task(topic)]}

    logger.info("Planner raw output (truncated): %s", raw[:500])
    tasks_payload = _extract_tasks(raw, strip_thinking=cfg.strip_thinking_tokens)

    todo_items = []
    for idx, item in enumerate(tasks_payload, start=1):
        title = str(item.get("title") or f"任务{idx}").strip()
        intent = str(item.get("intent") or "聚焦主题的关键问题").strip()
        query = str(item.get("query") or topic).strip() or topic
        todo_items.append(TodoItem(id=idx, title=title, intent=intent, query=query))

    if not todo_items:
        logger.warning("Planner produced no tasks; using fallback")
        todo_items = [create_fallback_task(topic)]

    logger.info("Planner (manual) produced %d tasks: %s", len(todo_items), [t.title for t in todo_items])
    return {"todo_items": todo_items}
