"""Unit tests for prompt localization and Configuration.locale wiring."""

from __future__ import annotations

import pytest

from config import Configuration
from prompts import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    get_prompt,
    task_summarizer_instructions,
    report_writer_instructions,
    todo_planner_instructions,
    todo_planner_system_prompt,
)


@pytest.mark.parametrize(
    "name",
    [
        "todo_planner_system_prompt",
        "todo_planner_instructions",
        "task_summarizer_instructions",
        "report_writer_instructions",
    ],
)
def test_get_prompt_default_locale_matches_legacy_constants(name: str) -> None:
    """Backwards-compat: legacy module-level constants equal zh-CN prompts."""
    legacy = {
        "todo_planner_system_prompt": todo_planner_system_prompt,
        "todo_planner_instructions": todo_planner_instructions,
        "task_summarizer_instructions": task_summarizer_instructions,
        "report_writer_instructions": report_writer_instructions,
    }[name]
    assert get_prompt(name, DEFAULT_LOCALE) == legacy


@pytest.mark.parametrize(
    "name",
    [
        "todo_planner_system_prompt",
        "todo_planner_instructions",
        "task_summarizer_instructions",
        "report_writer_instructions",
    ],
)
def test_get_prompt_en_us_exists_and_differs(name: str) -> None:
    """en-US locale must exist for every prompt and not be empty."""
    en = get_prompt(name, "en-US")
    zh = get_prompt(name, "zh-CN")
    assert en.strip(), f"{name} (en-US) should not be empty"
    assert en != zh, f"{name} en-US should differ from zh-CN"


def test_default_locale_is_zh_cn() -> None:
    assert DEFAULT_LOCALE == "zh-CN"
    assert "zh-CN" in SUPPORTED_LOCALES
    assert "en-US" in SUPPORTED_LOCALES


def test_get_prompt_unknown_locale_raises() -> None:
    with pytest.raises(KeyError, match="Unknown locale"):
        get_prompt("todo_planner_system_prompt", "fr-FR")


def test_get_prompt_unknown_name_raises() -> None:
    with pytest.raises(KeyError, match="not localized"):
        get_prompt("does_not_exist", "zh-CN")


def test_configuration_locale_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOCALE", raising=False)
    cfg = Configuration.from_env()
    assert cfg.locale == "zh-CN"


def test_configuration_locale_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCALE", "en-US")
    cfg = Configuration.from_env()
    assert cfg.locale == "en-US"


def test_configuration_locale_override() -> None:
    cfg = Configuration.from_env(overrides={"locale": "en-US"})
    assert cfg.locale == "en-US"
