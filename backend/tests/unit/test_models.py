from __future__ import annotations

from models import TodoItem, merge_todos


def test_merge_todos_overwrites_same_id_and_preserves_order() -> None:
    left = [
        TodoItem(id=1, title="A", intent="old", query="q1", status="pending"),
        TodoItem(id=2, title="B", intent="old", query="q2", status="pending"),
    ]
    right = [
        TodoItem(id=1, title="A", intent="new", query="q1", status="completed"),
        TodoItem(id=3, title="C", intent="new", query="q3", status="pending"),
    ]

    result = merge_todos(left, right)

    assert [item.id for item in result] == [1, 2, 3]
    assert result[0].intent == "new"
    assert result[0].status == "completed"
    assert result[1].title == "B"
    assert result[2].title == "C"


def test_merge_todos_handles_empty_sides() -> None:
    item = TodoItem(id=1, title="A", intent="intent", query="query")

    assert merge_todos([], [item]) == [item]
    assert merge_todos([item], []) == [item]
