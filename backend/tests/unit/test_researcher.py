"""Unit tests for the iterative research loop (researcher.py)."""

from __future__ import annotations

import pytest

from src.config import Configuration
from src.models import TodoItem
from src.services.researcher import _reflect


# ---------------------------------------------------------------------------
# Reflection tests
# ---------------------------------------------------------------------------
def make_reflection_json(is_sufficient: bool, follow_up: str = "", reasoning: str = "ok") -> str:
    """Helper to produce valid reflection JSON."""
    import json
    return json.dumps({
        "is_sufficient": is_sufficient,
        "follow_up_query": follow_up,
        "reasoning": reasoning,
    }, ensure_ascii=False)


class FakeLLM:
    """Simulate an LLM that returns a pre-canned reflection JSON."""

    def __init__(self, raw_output: str):
        self.raw = raw_output

    async def ainvoke(self, messages):
        # Return an object with .content attribute
        class FakeResp:
            content = self.raw
        return FakeResp()


@pytest.mark.asyncio
async def test_reflect_parses_sufficient_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valid JSON with is_sufficient=True is parsed correctly."""
    from src.llm import build_chat_model
    monkeypatch.setattr(
        "src.services.researcher.build_chat_model",
        lambda cfg: FakeLLM(make_reflection_json(True)),
    )
    task = TodoItem(id=1, title="t", intent="i", query="q")
    cfg = Configuration.from_env()
    sufficient, follow_up, reasoning = await _reflect(task, "topic", "summary", "ctx", cfg)
    assert sufficient is True
    assert follow_up == ""
    assert reasoning == "ok"


@pytest.mark.asyncio
async def test_reflect_parses_insufficient_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valid JSON with is_sufficient=False returns follow_up_query."""
    from src.llm import build_chat_model
    monkeypatch.setattr(
        "src.services.researcher.build_chat_model",
        lambda cfg: FakeLLM(
            make_reflection_json(False, follow_up="deeper search terms", reasoning="not enough data")
        ),
    )
    task = TodoItem(id=1, title="t", intent="i", query="q")
    cfg = Configuration.from_env()
    sufficient, follow_up, reasoning = await _reflect(task, "topic", "summary", "ctx", cfg)
    assert sufficient is False
    assert follow_up == "deeper search terms"


@pytest.mark.asyncio
async def test_reflect_fallback_on_bad_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-JSON output defaults to is_sufficient=True."""
    from src.llm import build_chat_model
    monkeypatch.setattr(
        "src.services.researcher.build_chat_model",
        lambda cfg: FakeLLM("just some rambling text, not valid JSON"),
    )
    task = TodoItem(id=1, title="t", intent="i", query="q")
    cfg = Configuration.from_env()
    sufficient, follow_up, reasoning = await _reflect(task, "topic", "summary", "ctx", cfg)
    assert sufficient is True


@pytest.mark.asyncio
async def test_reflect_fallback_on_llm_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """If LLM call raises, default to sufficient and don't crash."""
    from src.llm import build_chat_model

    class ExplodingLLM:
        async def ainvoke(self, messages):
            raise RuntimeError("boom")

    monkeypatch.setattr(
        "src.services.researcher.build_chat_model",
        lambda cfg: ExplodingLLM(),
    )
    task = TodoItem(id=1, title="t", intent="i", query="q")
    cfg = Configuration.from_env()
    sufficient, _, _ = await _reflect(task, "topic", "summary", "ctx", cfg)
    assert sufficient is True
