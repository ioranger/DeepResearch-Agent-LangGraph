"""State models used by the deep research workflow (LangGraph version)."""

from __future__ import annotations

import operator
from typing import List, Optional, TypedDict

from pydantic import BaseModel, Field
from typing_extensions import Annotated


class TodoItem(BaseModel):
    """单个待办任务项。"""

    id: int
    title: str
    intent: str
    query: str
    status: str = "pending"
    summary: Optional[str] = None
    sources_summary: Optional[str] = None
    notices: List[str] = Field(default_factory=list)
    note_id: Optional[str] = None
    note_path: Optional[str] = None
    stream_token: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True}


def merge_todos(left: List[TodoItem], right: List[TodoItem]) -> List[TodoItem]:
    """Reducer: 按 id 合并 TodoItem，相同 id 后写覆盖前写，保持出现顺序。"""
    if not left:
        return list(right or [])
    if not right:
        return list(left)

    by_id: dict[int, TodoItem] = {}
    order: list[int] = []
    for item in list(left) + list(right):
        if item.id not in by_id:
            order.append(item.id)
        by_id[item.id] = item
    return [by_id[i] for i in order]


class ResearchState(TypedDict, total=False):
    """LangGraph 主状态：使用 reducer 支持 Send fan-out 合并。"""

    research_topic: str
    todo_items: Annotated[List[TodoItem], merge_todos]
    web_research_results: Annotated[List[str], operator.add]
    sources_gathered: Annotated[List[str], operator.add]
    research_loop_count: Annotated[int, operator.add]
    structured_report: Optional[str]
    report_note_id: Optional[str]
    report_note_path: Optional[str]


class ResearchTaskState(TypedDict, total=False):
    """传给 research 节点的子状态（通过 Send dispatch）。"""

    task: TodoItem
    research_topic: str


class SummaryStateOutput(BaseModel):
    """同步接口返回类型，向后兼容旧 API。"""

    running_summary: Optional[str] = None
    report_markdown: Optional[str] = None
    todo_items: List[TodoItem] = Field(default_factory=list)
