"""Note service: persistent Markdown notes with JSON index.

Replaces hello_agents NoteTool with a self-contained implementation. Maintains
file/index schema compatibility with existing notes_index.json.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Iterable, Optional

from models import TodoItem

logger = logging.getLogger(__name__)


def build_note_guidance(task: TodoItem) -> str:
    """Generate note tool usage guidance for a specific task (instructional text)."""
    tags_list = ["deep_research", f"task_{task.id}"]
    tags_literal = json.dumps(tags_list, ensure_ascii=False)

    if task.note_id:
        read_payload = json.dumps({"action": "read", "note_id": task.note_id}, ensure_ascii=False)
        update_payload = json.dumps(
            {
                "action": "update",
                "note_id": task.note_id,
                "task_id": task.id,
                "title": f"任务 {task.id}: {task.title}",
                "note_type": "task_state",
                "tags": tags_list,
                "content": "请将本轮新增信息补充到任务概览中",
            },
            ensure_ascii=False,
        )
        return (
            "笔记协作指引：\n"
            f"- 当前任务笔记 ID：{task.note_id}。\n"
            f"- 在书写总结前必须调用：[TOOL_CALL:note:{read_payload}] 获取最新内容。\n"
            f"- 完成分析后调用：[TOOL_CALL:note:{update_payload}] 同步增量信息。\n"
            "- 更新时保持原有段落结构，新增内容请在对应段落中补充。\n"
            f"- 建议 tags 保持为 {tags_literal}，保证其他 Agent 可快速定位。\n"
            "- 成功同步到笔记后，再输出面向用户的总结。\n"
        )

    create_payload = json.dumps(
        {
            "action": "create",
            "task_id": task.id,
            "title": f"任务 {task.id}: {task.title}",
            "note_type": "task_state",
            "tags": tags_list,
            "content": "请记录任务概览、来源概览",
        },
        ensure_ascii=False,
    )
    return (
        "笔记协作指引：\n"
        f"- 当前任务尚未建立笔记，请先调用：[TOOL_CALL:note:{create_payload}]。\n"
        "- 创建成功后记录返回的 note_id，并在后续所有更新中复用。\n"
        "- 同步笔记后，再输出面向用户的总结。\n"
    )


class NoteService:
    """Markdown-on-disk note storage compatible with the legacy NoteTool format."""

    def __init__(self, workspace: str | Path) -> None:
        self.root = Path(workspace).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "notes_index.json"
        self._lock = Lock()
        self._index = self._load_index()

    # ------------------------------------------------------------------
    # Index helpers
    # ------------------------------------------------------------------
    def _load_index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {
                "notes": [],
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "total_notes": 0,
                },
            }
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - corrupted index fallback
            logger.warning("Failed to load notes_index.json: %s", exc)
            return {"notes": [], "metadata": {"total_notes": 0}}

    def _save_index(self) -> None:
        self._index.setdefault("metadata", {})["total_notes"] = len(self._index.get("notes", []))
        self.index_path.write_text(
            json.dumps(self._index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _next_seq(self) -> int:
        max_seq = -1
        for entry in self._index.get("notes", []):
            note_id = entry.get("id", "")
            match = re.search(r"_(\d+)$", note_id)
            if match:
                max_seq = max(max_seq, int(match.group(1)))
        return max_seq + 1

    def _generate_note_id(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"note_{timestamp}_{self._next_seq()}"

    def _note_path(self, note_id: str) -> Path:
        return self.root / f"{note_id}.md"

    def _find_entry(self, note_id: str) -> Optional[dict[str, Any]]:
        for entry in self._index.get("notes", []):
            if entry.get("id") == note_id:
                return entry
        return None

    @staticmethod
    def _format_tags(tags: Optional[Iterable[str]]) -> list[str]:
        return list(tags) if tags else []

    @staticmethod
    def _frontmatter(entry: dict[str, Any]) -> str:
        tags_literal = json.dumps(entry.get("tags", []), ensure_ascii=False)
        lines = [
            "---",
            f"id: {entry['id']}",
            f"title: {entry.get('title', '')}",
            f"type: {entry.get('type', 'note')}",
            f"tags: {tags_literal}",
            f"created_at: {entry.get('created_at', '')}",
        ]
        if entry.get("updated_at"):
            lines.append(f"updated_at: {entry['updated_at']}")
        lines.append("---")
        return "\n".join(lines)

    @staticmethod
    def _strip_frontmatter(text: str) -> str:
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                return parts[2].lstrip("\n")
        return text

    # ------------------------------------------------------------------
    # Public dispatch
    # ------------------------------------------------------------------
    def run(self, payload: dict[str, Any]) -> str:
        action = (payload or {}).get("action", "").strip().lower()
        handler = getattr(self, f"_{action}", None)
        if not handler:
            return f"❌ 未知 action: {action}"
        try:
            with self._lock:
                return handler(payload)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("NoteService action %s failed", action)
            return f"❌ 操作失败: {exc}"

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _create(self, payload: dict[str, Any]) -> str:
        title = payload.get("title") or "未命名笔记"
        note_type = payload.get("note_type", "note")
        tags = self._format_tags(payload.get("tags"))
        content = payload.get("content", "")

        note_id = self._generate_note_id()
        entry = {
            "id": note_id,
            "title": title,
            "type": note_type,
            "tags": tags,
            "created_at": datetime.now().isoformat(),
        }
        body = f"{self._frontmatter(entry)}\n\n# {title}\n\n{content}".rstrip() + "\n"
        self._note_path(note_id).write_text(body, encoding="utf-8")
        self._index.setdefault("notes", []).append(entry)
        self._save_index()
        return f"✅ 已创建笔记\nID: {note_id}\n标题: {title}"

    def _read(self, payload: dict[str, Any]) -> str:
        note_id = payload.get("note_id", "")
        entry = self._find_entry(note_id)
        if not entry:
            return f"❌ 未找到笔记 {note_id}"
        path = self._note_path(note_id)
        if not path.exists():
            return f"❌ 笔记文件缺失 {note_id}"
        text = path.read_text(encoding="utf-8")
        return f"ID: {note_id}\n\n{text}"

    def _update(self, payload: dict[str, Any]) -> str:
        note_id = payload.get("note_id", "")
        entry = self._find_entry(note_id)
        if not entry:
            return f"❌ 未找到笔记 {note_id}"

        if "title" in payload and payload["title"]:
            entry["title"] = payload["title"]
        if "note_type" in payload and payload["note_type"]:
            entry["type"] = payload["note_type"]
        if "tags" in payload and payload["tags"] is not None:
            entry["tags"] = self._format_tags(payload["tags"])
        entry["updated_at"] = datetime.now().isoformat()

        path = self._note_path(note_id)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        old_body = self._strip_frontmatter(existing)
        new_content = payload.get("content")
        if new_content is None:
            body = old_body
        else:
            body = f"# {entry.get('title','')}\n\n{new_content}".rstrip() + "\n"

        full = f"{self._frontmatter(entry)}\n\n{body}"
        path.write_text(full, encoding="utf-8")
        self._save_index()
        return f"✅ 已更新笔记\nID: {note_id}"

    def _list(self, payload: dict[str, Any]) -> str:
        notes = self._index.get("notes", [])
        note_type = payload.get("note_type")
        if note_type:
            notes = [n for n in notes if n.get("type") == note_type]
        lines = [f"共 {len(notes)} 条笔记:"]
        for n in notes:
            lines.append(f"- {n.get('id')} | {n.get('type')} | {n.get('title')}")
        return "\n".join(lines)

    def _search(self, payload: dict[str, Any]) -> str:
        query = (payload.get("query") or "").lower().strip()
        if not query:
            return "❌ 缺少 query"
        hits: list[str] = []
        for entry in self._index.get("notes", []):
            title = (entry.get("title") or "").lower()
            tags = " ".join(entry.get("tags", [])).lower()
            if query in title or query in tags:
                hits.append(f"- {entry['id']} | {entry.get('title')}")
                continue
            path = self._note_path(entry["id"])
            if path.exists() and query in path.read_text(encoding="utf-8").lower():
                hits.append(f"- {entry['id']} | {entry.get('title')} (内容命中)")
        return f"搜索 '{query}' 共 {len(hits)} 条:\n" + ("\n".join(hits) if hits else "(无)")

    # ------------------------------------------------------------------
    # Convenience for persist_node
    # ------------------------------------------------------------------
    def save_report(self, topic: str, content: str) -> tuple[str, Path]:
        title = f"研究报告：{topic}".strip() or "研究报告"
        response = self.run(
            {
                "action": "create",
                "title": title,
                "note_type": "conclusion",
                "tags": ["deep_research", "report"],
                "content": content,
            }
        )
        match = re.search(r"ID:\s*([^\n]+)", response)
        note_id = match.group(1).strip() if match else ""
        return note_id, self._note_path(note_id)
