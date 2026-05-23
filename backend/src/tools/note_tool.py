"""LangChain BaseTool wrapping NoteService."""

from __future__ import annotations

from typing import Any, List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from services.notes import NoteService


class NoteToolInput(BaseModel):
    action: str = Field(description="One of: create / read / update / list / search")
    note_id: Optional[str] = None
    title: Optional[str] = None
    note_type: Optional[str] = None
    tags: Optional[List[str]] = None
    content: Optional[str] = None
    query: Optional[str] = None
    task_id: Optional[int] = None


class NoteTool(BaseTool):
    name: str = "note"
    description: str = (
        "管理研究笔记，支持 create/read/update/list/search 操作。"
        "字段：action (必填), note_id, title, note_type, tags(list), content, query。"
    )
    args_schema: Type[BaseModel] = NoteToolInput
    service: Any = None

    def __init__(self, service: NoteService, **kwargs: Any) -> None:
        super().__init__(service=service, **kwargs)

    def _run(self, **kwargs: Any) -> str:  # type: ignore[override]
        payload = {k: v for k, v in kwargs.items() if v is not None}
        return self.service.run(payload)

    async def _arun(self, **kwargs: Any) -> str:  # type: ignore[override]
        return self._run(**kwargs)
