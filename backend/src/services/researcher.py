"""Iterative research loop: search → summarize → reflect → repeat.

Replaces the single-pass logic that was embedded directly in
``research_node``. Each iteration inspects the accumulated context,
asks the LLM to decide whether enough information has been gathered,
and — if not — formulates a follow-up query.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer

from config import Configuration
from llm import build_chat_model
from models import TodoItem
from prompts import get_prompt
from services.notes import build_note_guidance
from services.text_processing import filter_relevant_snippets, strip_tool_calls
from services.search import dispatch_search, prepare_research_context
from utils import strip_thinking_tokens

logger = logging.getLogger(__name__)


def _emit(event: dict[str, Any]) -> None:
    """Best-effort push to the LangGraph custom stream writer."""
    try:
        writer = get_stream_writer()
        writer(event)
    except Exception:
        pass


def _build_summary_prompt(
    research_topic: str,
    task: TodoItem,
    context: str,
    *,
    loop: int = 1,
    previous_summary: str = "",
    citation_directive: str = "",
) -> str:
    """Construct a summarization prompt that may include prior-round context."""
    note_guidance = build_note_guidance(task)
    base = (
        f"研究主题：{research_topic}\n"
        f"任务标题：{task.title}\n"
        f"任务意图：{task.intent}\n"
        f"检索关键词：{task.query}\n\n"
    )
    if previous_summary:
        base += (
            f"前一轮总结（第{loop - 1}轮）：\n{previous_summary}\n\n"
            f"本轮新增上下文资料（第{loop}轮）：\n{context}\n\n"
        )
    else:
        base += f"上下文资料：\n{context}\n\n"

    if citation_directive:
        base += f"{citation_directive}\n\n"
    base += f"{note_guidance}\n请输出严格符合格式要求的任务总结。"
    return base


async def _stream_summarize(
    task: TodoItem,
    research_topic: str,
    context: str,
    cfg: Configuration,
    *,
    loop: int = 1,
    previous_summary: str = "",
) -> str:
    """Stream tokens from the summarizer and emit task_summary_chunk."""
    llm = build_chat_model(cfg)
    directive = get_prompt("citation_directive", cfg.locale)
    prompt = _build_summary_prompt(
        research_topic, task, context,
        loop=loop, previous_summary=previous_summary,
        citation_directive=directive,
    )
    chunks: list[str] = []
    async for chunk in llm.astream(
        [
            SystemMessage(
                content=get_prompt("task_summarizer_instructions", cfg.locale).strip()
            ),
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
    return "".join(chunks)


async def _reflect(
    task: TodoItem,
    research_topic: str,
    current_summary: str,
    all_context: str,
    cfg: Configuration,
) -> tuple[bool, str, str]:
    """Ask the LLM to evaluate research sufficiency.

    Returns (is_sufficient, follow_up_query, reasoning).
    """
    llm = build_chat_model(cfg)
    prompt = (
        f"研究主题：{research_topic}\n"
        f"任务标题：{task.title}\n"
        f"任务意图：{task.intent}\n\n"
        f"当前累计上下文：\n{all_context}\n\n"
        f"当前总结（草稿）：\n{current_summary}\n\n"
        f"请评估信息是否足够充分，严格输出 JSON。"
    )
    try:
        resp = await llm.ainvoke(
            [
                SystemMessage(
                    content=get_prompt("reflection_evaluator", cfg.locale).strip()
                ),
                HumanMessage(content=prompt),
            ]
        )
        raw = getattr(resp, "content", "") or ""
    except Exception as exc:
        logger.warning("Reflection LLM call failed: %s — assuming sufficient", exc)
        return True, "", f"Reflection call failed: {exc}"

    # Parse JSON from LLM output
    raw = raw.strip()
    # Strip any markdown code fences
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try to find JSON object
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                logger.warning("Could not parse reflection JSON: %s", raw[:200])
                return True, "", "Could not parse reflection output"
        else:
            logger.warning("No JSON found in reflection: %s", raw[:200])
            return True, "", "No JSON in reflection output"

    is_sufficient = bool(data.get("is_sufficient", True))
    follow_up = str(data.get("follow_up_query") or "")
    reasoning = str(data.get("reasoning") or "")
    return is_sufficient, follow_up, reasoning


async def iterative_research(
    task: TodoItem,
    research_topic: str,
    cfg: Configuration,
) -> dict[str, Any]:
    """Execute the full research loop for a single TodoItem.

    Returns a dict compatible with the LangGraph research node output shape:
    ``{"todo_items": [...], "web_research_results": [...], "sources_gathered": [...], "research_loop_count": N}``.
    """
    task = task.model_copy()
    task.status = "in_progress"

    max_loops = max(1, cfg.max_web_research_loops)

    accumulated_sources: list[dict[str, Any]] = []
    accumulated_context_parts: list[str] = []
    accumulated_summary = ""
    current_query = task.query
    research_loop_count = 0

    try:
        for loop in range(1, max_loops + 1):
            research_loop_count = loop

            # 1. Search -------------------------------------------------
            search_payload, notices, answer_text, backend = await asyncio.to_thread(
                dispatch_search, current_query, cfg, loop - 1
            )

            for notice in notices or []:
                if notice:
                    _emit({"type": "status", "message": notice, "task_id": task.id})

            results = (search_payload or {}).get("results") if search_payload else None
            # Filter snippets for relevance
            if results and len(results) > 8:
                search_payload["results"] = filter_relevant_snippets(results, task.query)
                results = search_payload["results"]
            if not results:
                if loop == 1:
                    task.status = "skipped"
                    return {"todo_items": [task]}
                # Still have previous data; break the loop
                break

            sources_list, context = prepare_research_context(
                search_payload, answer_text, cfg
            )
            accumulated_sources.extend(sources_list)
            accumulated_context_parts.append(context)

            # Track citation ids
            for s in sources_list:
                if s.get("id") and s["id"] not in task.citations:
                    task.citations.append(s["id"])

            _emit(
                {
                    "type": "sources",
                    "task_id": task.id,
                    "latest_sources": sources_list,
                    "raw_context": context,
                    "backend": backend,
                    "note_id": task.note_id,
                    "note_path": task.note_path,
                }
            )

            # 2. Summarize (streaming) -----------------------------------
            combined_context = "\n\n---\n\n".join(accumulated_context_parts)
            raw_summary = await _stream_summarize(
                task, research_topic, combined_context, cfg,
                loop=loop, previous_summary=accumulated_summary,
            )
            cleaned = strip_tool_calls(
                strip_thinking_tokens(raw_summary) if cfg.strip_thinking_tokens else raw_summary
            ).strip()
            current_summary = cleaned or "暂无可用信息"
            accumulated_summary = current_summary

            # 3. Reflect -------------------------------------------------
            is_sufficient, follow_up_query, reasoning = await _reflect(
                task, research_topic, current_summary, combined_context, cfg
            )

            _emit(
                {
                    "type": "task_reflection",
                    "task_id": task.id,
                    "is_sufficient": is_sufficient,
                    "follow_up_query": follow_up_query,
                    "reasoning": reasoning,
                    "current_loop": loop,
                    "max_loops": max_loops,
                    "note_id": task.note_id,
                }
            )

            if is_sufficient or loop >= max_loops:
                break

            current_query = follow_up_query or task.query

        # Finalize task --------------------------------------------------
        task.summary = accumulated_summary or "暂无可用信息"
        # Build structured reference list for the report
        seen_ids: set[int] = set()
        unique_sources: list[dict[str, Any]] = []
        for s in accumulated_sources:
            sid = s.get("id") if isinstance(s, dict) else None
            if sid is not None and sid not in seen_ids:
                seen_ids.add(sid)
                unique_sources.append(s)

        task.sources_summary = (
            "\n".join(
                f"[{s['id']}] {s.get('title','')} — {s.get('url','')}"
                for s in unique_sources
            )
            if unique_sources
            else ""
        )
        task.citations = sorted(seen_ids)
        task.status = "completed"

        return {
            "todo_items": [task],
            "web_research_results": accumulated_context_parts,
            "sources_gathered": accumulated_sources,
            "research_loop_count": research_loop_count,
        }

    except Exception as exc:  # pragma: no cover - per-task isolation
        logger.exception("Task %s execution failed", task.id, exc_info=exc)
        task.status = "failed"
        task.summary = f"任务执行失败：{exc}"
        return {"todo_items": [task]}
