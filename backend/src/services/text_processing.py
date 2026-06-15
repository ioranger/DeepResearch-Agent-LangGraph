"""Utility helpers for normalizing agent generated text."""

from __future__ import annotations

import re


def strip_tool_calls(text: str) -> str:
    """移除文本中的工具调用标记。"""

    if not text:
        return text

    pattern = re.compile(r"\[TOOL_CALL:[^\]]+\]")
    return pattern.sub("", text)

def filter_relevant_snippets(
    results: list[dict],
    query: str,
    top_k: int = 8,
) -> list[dict]:
    """Lightweight relevance filter based on keyword overlap.

    Scores each result's content against the query using simple keyword
    intersection, normalized by content length. Returns top_k results only.

    No external embedding dependency required.
    """
    if not results or len(results) <= top_k:
        return list(results)

    query_terms = set(query.lower().split())

    def score(r: dict) -> float:
        text = ((r.get("content") or r.get("raw_content") or "")).lower()
        if not text:
            return 0.0
        words = set(text.split())
        overlap = len(query_terms & words)
        return overlap / max(len(text), 1)

    scored = sorted(results, key=score, reverse=True)
    filtered = [r for r in scored if score(r) > 0]
    if not filtered:
        return scored[:top_k]
    return filtered[:top_k]

