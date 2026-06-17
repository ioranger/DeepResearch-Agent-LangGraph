from __future__ import annotations

from src.config import Configuration, SearchAPI
from src.services import search


def test_advanced_search_aggregates_backend_results(monkeypatch) -> None:
    def fake_tavily(query, config):
        return {
            "results": [{"title": "tavily", "url": "https://tavily.example", "content": "a"}],
            "backend": "tavily",
            "answer": "answer a",
            "notices": [],
        }

    def fake_ddg(query, config):
        return {
            "results": [{"title": "ddg", "url": "https://ddg.example", "content": "b"}],
            "backend": "duckduckgo",
            "answer": None,
            "notices": ["ddg notice"],
        }

    def fake_searxng(query, config):
        raise RuntimeError("searxng unavailable")

    def fake_perplexity(query, config):
        return {
            "results": [],
            "backend": "perplexity",
            "answer": "answer p",
            "notices": ["perplexity notice"],
        }

    monkeypatch.setattr(search, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search, "_search_ddg", fake_ddg)
    monkeypatch.setattr(search, "_search_searxng", fake_searxng)
    monkeypatch.setattr(search, "_search_perplexity", fake_perplexity)

    config = Configuration(search_api=SearchAPI.ADVANCED)
    payload, notices, answer, backend = search.dispatch_search("query", config, 0)

    assert backend == "advanced"
    assert payload["backend"] == "advanced"
    assert [item["title"] for item in payload["results"]] == ["tavily", "ddg"]
    assert "answer a" in answer
    assert "answer p" in answer
    assert "ddg notice" in notices
    assert "perplexity notice" in notices
    assert any("searxng unavailable" in notice for notice in notices)


def test_prepare_research_context_returns_numbered_sources() -> None:
    """prepare_research_context now returns (list[dict], str) with [n] numbering."""
    search_result = {
        "results": [
            {"title": "Source A", "url": "https://a.com", "content": "Content A"},
            {"title": "Source B", "url": "https://b.com", "content": "Content B"},
        ],
    }
    config = Configuration()
    sources_list, context = search.prepare_research_context(search_result, None, config)

    assert isinstance(sources_list, list)
    assert len(sources_list) == 2
    assert sources_list[0]["id"] == 1
    assert sources_list[0]["title"] == "Source A"
    assert sources_list[1]["id"] == 2
    assert "[1]" in context
    assert "[2]" in context
    assert "Source A" in context
    assert "Source B" in context


def test_prepare_research_context_empty_results() -> None:
    """Empty results should still return valid types."""
    config = Configuration()
    sources_list, context = search.prepare_research_context({"results": []}, None, config)
    assert isinstance(sources_list, list)
    assert len(sources_list) == 0
    assert "暂无" in context or "no results" in context.lower() or "暂无搜索结果" in context
