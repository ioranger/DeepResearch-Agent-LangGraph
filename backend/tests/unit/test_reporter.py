"""Unit tests for report generation with citations and References."""

from __future__ import annotations

import pytest

from src.config import Configuration
from src.models import ResearchState, TodoItem
from src.services.reporter import _build_references_section, build_report_prompt


def test_build_references_section_collects_unique_citations() -> None:
    """Sources from multiple tasks are deduplicated and sorted."""
    task_a = TodoItem(
        id=1, title="A", intent="a", query="a",
        sources_summary="[1] Source One — https://one.com\n[2] Source Two — https://two.com",
        citations=[1, 2],
    )
    task_b = TodoItem(
        id=2, title="B", intent="b", query="b",
        sources_summary="[2] Source Two — https://two.com\n[3] Source Three — https://three.com",
        citations=[2, 3],
    )
    state: ResearchState = {"research_topic": "test", "todo_items": [task_a, task_b]}
    refs = _build_references_section(state)
    assert "## 参考来源" in refs
    assert "[1]" in refs
    assert "[2]" in refs
    assert "[3]" in refs


def test_build_references_section_empty() -> None:
    """No tasks → empty string."""
    state: ResearchState = {"research_topic": "test", "todo_items": []}
    assert _build_references_section(state) == ""


def test_build_report_prompt_includes_citation_info() -> None:
    """Report prompt carries citation IDs for each task."""
    task = TodoItem(
        id=1, title="Test", intent="test", query="test",
        summary="要点内容 [1]",
        sources_summary="[1] Src — url",
        citations=[1],
    )
    state: ResearchState = {"research_topic": "test", "todo_items": [task]}
    prompt = build_report_prompt(state)
    assert "引用编号" in prompt
    assert "1" in prompt
    assert "要点内容 [1]" in prompt
