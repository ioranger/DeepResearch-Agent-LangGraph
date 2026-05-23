"""LangChain BaseTool wrapping multi-backend search."""

from __future__ import annotations

from typing import Any, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from config import Configuration
from services.search import dispatch_search


class SearchToolInput(BaseModel):
    query: str = Field(description="自然语言检索 query")


class SearchTool(BaseTool):
    name: str = "search"
    description: str = "网络检索：调用 Tavily/DuckDuckGo/SearXNG/Perplexity 多后端"
    args_schema: Type[BaseModel] = SearchToolInput
    config: Any = None

    def __init__(self, config: Configuration, **kwargs: Any) -> None:
        super().__init__(config=config, **kwargs)

    def _run(self, query: str) -> dict:  # type: ignore[override]
        payload, _, _, _ = dispatch_search(query, self.config, 0)
        return payload

    async def _arun(self, query: str) -> dict:  # type: ignore[override]
        return self._run(query)
