"""Multi-backend search dispatch (replaces hello_agents SearchTool)."""

from __future__ import annotations

import logging
import os
from typing import Any, Optional, Tuple

from config import Configuration, SearchAPI
from utils import (
    deduplicate_and_format_sources,
    format_sources,
    get_config_value,
)

logger = logging.getLogger(__name__)

MAX_TOKENS_PER_SOURCE = 2000


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
def dispatch_search(
    query: str,
    config: Configuration,
    loop_count: int,
) -> Tuple[dict[str, Any], list[str], Optional[str], str]:
    """Execute configured search backend and normalise response payload.

    Returns
    -------
    payload   : {"results": [...], "backend": str, "answer": str | None, "notices": [...]}
    notices   : list[str]
    answer    : Optional[str] (direct AI answer if backend supports it)
    backend   : str (resolved backend label)
    """
    backend = get_config_value(config.search_api).lower()

    handlers = {
        "tavily": _search_tavily,
        "duckduckgo": _search_ddg,
        "searxng": _search_searxng,
        "perplexity": _search_perplexity,
        "advanced": _search_advanced,
    }
    handler = handlers.get(backend, _search_ddg)

    try:
        payload = handler(query, config)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Search backend %s failed: %s", backend, exc)
        payload = {
            "results": [],
            "backend": backend,
            "answer": None,
            "notices": [f"搜索后端 {backend} 异常: {exc}"],
        }

    notices = list(payload.get("notices") or [])
    answer = payload.get("answer")
    backend_label = str(payload.get("backend") or backend)

    logger.info(
        "Search backend=%s answer=%s results=%s notices=%s",
        backend_label,
        bool(answer),
        len(payload.get("results", [])),
        len(notices),
    )

    return payload, notices, answer, backend_label


def prepare_research_context(
    search_result: dict[str, Any] | None,
    answer_text: Optional[str],
    config: Configuration,
) -> tuple[list[dict[str, Any]], str]:
    """Build numbered context and structured source list for citation binding.

    Returns (sources_list, formatted_context) where sources_list is a list of
    ``[{id, title, url, snippet}, ...]`` and formatted_context prefixes each
    result with ``[n]`` markers.
    """
    results = (search_result or {}).get("results") or []
    sources_list: list[dict[str, Any]] = []

    context_parts: list[str] = []
    if answer_text:
        context_parts.append(f"AI直接答案：\n{answer_text}")

    for i, r in enumerate(results, start=1):
        title = r.get("title") or ""
        url = r.get("url") or ""
        snippet = (r.get("content") or r.get("raw_content") or "")[:MAX_TOKENS_PER_SOURCE]
        sources_list.append({"id": i, "title": title, "url": url, "snippet": snippet[:200]})
        context_parts.append(
            f"[{i}] {title}\n    URL: {url}\n    摘录: {snippet}"
        )

    formatted_context = "\n\n".join(context_parts) if context_parts else "暂无搜索结果"
    return sources_list, formatted_context


# ----------------------------------------------------------------------
# Backend implementations
# ----------------------------------------------------------------------
def _search_advanced(query: str, config: Configuration) -> dict[str, Any]:
    handlers = [_search_tavily, _search_ddg, _search_searxng, _search_perplexity]
    results: list[dict[str, Any]] = []
    notices: list[str] = []
    answers: list[str] = []

    for handler in handlers:
        try:
            payload = handler(query, config)
        except Exception as exc:  # pragma: no cover - per-backend isolation
            logger.exception("Advanced search handler %s failed: %s", handler.__name__, exc)
            notices.append(f"搜索后端 {handler.__name__} 异常: {exc}")
            continue

        results.extend(payload.get("results") or [])
        notices.extend(payload.get("notices") or [])
        answer = payload.get("answer")
        if answer:
            answers.append(str(answer))

    if not results:
        notices.append("Advanced 搜索未返回任何结果")

    return {
        "results": results,
        "backend": "advanced",
        "answer": "\n\n".join(answers) or None,
        "notices": notices,
    }


def _search_tavily(query: str, config: Configuration) -> dict[str, Any]:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return {
            "results": [],
            "backend": "tavily",
            "answer": None,
            "notices": ["未设置 TAVILY_API_KEY，跳过 Tavily 搜索"],
        }
    try:
        from tavily import TavilyClient
    except ImportError:
        return {"results": [], "backend": "tavily", "answer": None,
                "notices": ["缺少 tavily-python 依赖"]}

    client = TavilyClient(api_key=api_key)
    resp = client.search(
        query=query,
        max_results=5,
        include_raw_content=config.fetch_full_page,
        include_answer=True,
    )
    return {
        "results": resp.get("results", []),
        "backend": "tavily",
        "answer": resp.get("answer"),
        "notices": [],
    }


def _search_ddg(query: str, config: Configuration) -> dict[str, Any]:
    try:
        from ddgs import DDGS
    except ImportError:
        return {"results": [], "backend": "duckduckgo", "answer": None,
                "notices": ["缺少 ddgs 依赖"]}

    notices: list[str] = []
    results: list[dict[str, Any]] = []
    try:
        with DDGS() as ddgs:
            hits = list(ddgs.text(query, max_results=5))
        for hit in hits:
            results.append(
                {
                    "title": hit.get("title") or hit.get("href") or "",
                    "url": hit.get("href") or hit.get("url") or "",
                    "content": hit.get("body") or "",
                    "raw_content": hit.get("body") or "",
                }
            )
    except Exception as exc:
        notices.append(f"DuckDuckGo 检索异常: {exc}")

    if not results:
        notices.append("DuckDuckGo 未返回任何结果")
    return {"results": results, "backend": "duckduckgo", "answer": None, "notices": notices}


def _search_searxng(query: str, config: Configuration) -> dict[str, Any]:
    import requests

    base_url = os.getenv("SEARXNG_URL", "http://localhost:8888")
    notices: list[str] = []
    try:
        resp = requests.get(
            f"{base_url.rstrip('/')}/search",
            params={"q": query, "format": "json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return {"results": [], "backend": "searxng", "answer": None,
                "notices": [f"SearXNG 异常: {exc}"]}

    results = []
    for item in (data.get("results") or [])[:5]:
        results.append(
            {
                "title": item.get("title") or "",
                "url": item.get("url") or "",
                "content": item.get("content") or "",
                "raw_content": item.get("content") or "",
            }
        )
    if not results:
        notices.append("SearXNG 未返回任何结果")
    return {"results": results, "backend": "searxng", "answer": None, "notices": notices}


def _search_perplexity(query: str, config: Configuration) -> dict[str, Any]:
    import requests

    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        return {"results": [], "backend": "perplexity", "answer": None,
                "notices": ["未设置 PERPLEXITY_API_KEY"]}

    try:
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "sonar",
                "messages": [
                    {"role": "system", "content": "Search the web and return concise findings."},
                    {"role": "user", "content": query},
                ],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return {"results": [], "backend": "perplexity", "answer": None,
                "notices": [f"Perplexity 异常: {exc}"]}

    answer = ""
    try:
        answer = data["choices"][0]["message"]["content"]
    except Exception:
        pass

    citations = data.get("citations") or []
    results = [
        {"title": url, "url": url, "content": "", "raw_content": ""}
        for url in citations
    ]
    return {
        "results": results,
        "backend": "perplexity",
        "answer": answer or None,
        "notices": [],
    }
