from __future__ import annotations

from config import Configuration, SearchAPI
from services import search


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
