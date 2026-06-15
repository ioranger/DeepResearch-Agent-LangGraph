"""LangGraph-based DeepResearchAgent orchestrator.

Replaces the HelloAgents-based coordinator. Public API (`run`, `run_stream`)
is preserved for backward compatibility with main.py.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, Iterator

from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.types import Send

from config import Configuration
from models import ResearchState, SummaryStateOutput, TodoItem
from services.event_adapter import stream_research_events
from services.planner import plan_node
from services.reporter import persist_node, report_node
from services.summarizer import research_node

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Graph assembly
# ----------------------------------------------------------------------
def fan_out_research(state: ResearchState) -> list[Send]:
    """Conditional edge: dispatch each TodoItem to a parallel research worker."""
    topic = state.get("research_topic", "") or ""
    return [
        Send("research", {"task": item, "research_topic": topic})
        for item in state.get("todo_items") or []
    ]


def build_graph(config: Configuration | None = None):
    """Compile the deep research StateGraph."""
    graph = StateGraph(ResearchState)
    graph.add_node("plan", plan_node)
    graph.add_node("research", research_node)
    graph.add_node("report", report_node)
    graph.add_node("persist", persist_node)

    graph.add_edge(START, "plan")
    graph.add_conditional_edges("plan", fan_out_research, ["research"])
    graph.add_edge("research", "report")
    graph.add_edge("report", "persist")
    graph.add_edge("persist", END)

    return graph.compile()


# ----------------------------------------------------------------------
# Public agent class
# ----------------------------------------------------------------------
class DeepResearchAgent:
    """Backward-compatible wrapper around the compiled LangGraph."""

    def __init__(self, config: Configuration | None = None) -> None:
        self.config = config or Configuration.from_env()
        self.graph = build_graph(self.config)

    # ------------------------------------------------------------------
    # Public async API (preferred for FastAPI)
    # ------------------------------------------------------------------
    async def arun(self, topic: str) -> SummaryStateOutput:
        """Run the full research pipeline asynchronously."""
        runnable_config = {"configurable": {"app_config": self.config}}
        final_state = await self.graph.ainvoke(
            {"research_topic": topic},
            config=runnable_config,
        )
        report = final_state.get("structured_report") or ""
        todo_items: list[TodoItem] = list(final_state.get("todo_items") or [])
        return SummaryStateOutput(
            running_summary=report,
            report_markdown=report,
            todo_items=todo_items,
        )

    # ------------------------------------------------------------------
    # Synchronous API
    # ------------------------------------------------------------------
    def run(self, topic: str) -> SummaryStateOutput:
        """Sync façade for CLI / scripts."""
        return asyncio.run(self.arun(topic))

    async def _run_async(self, topic: str) -> SummaryStateOutput:
        """Deprecated: kept for backwards compatibility. Use arun directly."""
        return await self.arun(topic)

    # ------------------------------------------------------------------
    # Streaming API
    # ------------------------------------------------------------------
    def run_stream(self, topic: str) -> Iterator[dict[str, Any]]:
        """Synchronous-iterator façade over the async streaming events."""
        loop = asyncio.new_event_loop()
        agen = stream_research_events(self.graph, topic, self.config).__aiter__()
        try:
            while True:
                try:
                    event = loop.run_until_complete(agen.__anext__())
                except StopAsyncIteration:
                    break
                yield event
        finally:
            loop.close()

    async def astream(self, topic: str) -> AsyncIterator[dict[str, Any]]:
        async for ev in stream_research_events(self.graph, topic, self.config):
            yield ev


def run_deep_research(topic: str, config: Configuration | None = None) -> SummaryStateOutput:
    return DeepResearchAgent(config=config).run(topic)
