"""Report and persist nodes for the LangGraph deep research workflow."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer

from config import Configuration
from llm import build_chat_model
from models import ResearchState
from prompts import get_prompt
from services.notes import NoteService
from services.text_processing import strip_tool_calls
from utils import strip_thinking_tokens

logger = logging.getLogger(__name__)


def build_report_prompt(state: ResearchState) -> str:
    """Pure prompt-building helper, ported from the legacy ReportingService."""
    todo_items = state.get("todo_items") or []
    research_topic = state.get("research_topic", "") or ""

    tasks_block = []
    for task in todo_items:
        summary_block = task.summary or "暂无可用信息"
        sources_block = task.sources_summary or "暂无来源"
        tasks_block.append(
            f"### 任务 {task.id}: {task.title}\n"
            f"- 任务目标：{task.intent}\n"
            f"- 检索查询：{task.query}\n"
            f"- 执行状态：{task.status}\n"
            f"- 任务总结：\n{summary_block}\n"
            f"- 来源概览：\n{sources_block}\n"
        )

    note_refs = [
        f"- 任务 {t.id}《{t.title}》：note_id={t.note_id}"
        for t in todo_items
        if t.note_id
    ]
    notes_section = "\n".join(note_refs) if note_refs else "- 暂无可用任务笔记"

    read_tpl = json.dumps({"action": "read", "note_id": "<note_id>"}, ensure_ascii=False)
    create_tpl = json.dumps(
        {
            "action": "create",
            "title": f"研究报告：{research_topic}",
            "note_type": "conclusion",
            "tags": ["deep_research", "report"],
            "content": "请在此沉淀最终报告要点",
        },
        ensure_ascii=False,
    )

    return (
        f"研究主题：{research_topic}\n"
        f"任务概览：\n{''.join(tasks_block)}\n"
        f"可用任务笔记：\n{notes_section}\n"
        f"请针对每条任务笔记使用格式：[TOOL_CALL:note:{read_tpl}] 读取内容，整合所有信息后撰写报告。\n"
        f"如需输出汇总结论，可追加调用：[TOOL_CALL:note:{create_tpl}] 保存报告要点。"
    )


def report_node(state: ResearchState, config: RunnableConfig) -> dict:
    """Synchronous LLM call producing the final structured report."""
    cfg: Configuration = config["configurable"]["app_config"]
    prompt = build_report_prompt(state)

    llm = build_chat_model(cfg)
    try:
        resp = llm.invoke(
            [
                SystemMessage(content=get_prompt("report_writer_instructions", cfg.locale).strip()),
                HumanMessage(content=prompt),
            ]
        )
        raw = getattr(resp, "content", "") or ""
    except Exception as exc:
        logger.exception("Report generation failed: %s", exc)
        return {"structured_report": f"报告生成失败：{exc}"}

    text = raw.strip()
    if cfg.strip_thinking_tokens:
        text = strip_thinking_tokens(text)
    text = strip_tool_calls(text).strip() or "报告生成失败，请检查输入。"

    return {"structured_report": text}


def persist_node(state: ResearchState, config: RunnableConfig) -> dict:
    """Persist the final report to NoteService and emit a report_note event."""
    cfg: Configuration = config["configurable"]["app_config"]
    report = state.get("structured_report") or ""
    if not cfg.enable_notes or not report.strip():
        return {}

    service = NoteService(cfg.notes_workspace)
    topic = state.get("research_topic", "") or ""
    try:
        note_id, note_path = service.save_report(topic, report.strip())
    except Exception as exc:
        logger.warning("Failed to persist final report: %s", exc)
        return {}

    if not note_id:
        return {}

    title = f"研究报告：{topic}".strip() or "研究报告"
    payload: dict[str, Any] = {
        "type": "report_note",
        "note_id": note_id,
        "title": title,
        "content": report.strip(),
        "note_path": str(note_path),
    }
    try:
        get_stream_writer()(payload)
    except Exception:
        pass

    return {"report_note_id": note_id, "report_note_path": str(note_path)}
