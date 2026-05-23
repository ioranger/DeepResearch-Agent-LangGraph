"""Deep Research - A deep research assistant powered by LangGraph."""

__version__ = "0.0.2"

from .agent import DeepResearchAgent
from .config import Configuration, SearchAPI
from .models import ResearchState, SummaryStateOutput, TodoItem

__all__ = [
    "DeepResearchAgent",
    "Configuration",
    "SearchAPI",
    "ResearchState",
    "SummaryStateOutput",
    "TodoItem",
]
