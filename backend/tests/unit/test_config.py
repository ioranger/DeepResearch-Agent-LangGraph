from __future__ import annotations

from config import Configuration, SearchAPI


def test_config_override_search_api() -> None:
    config = Configuration.from_env(overrides={"search_api": "tavily"})

    assert config.search_api == SearchAPI.TAVILY


def test_config_parses_cors_origins_from_env(monkeypatch) -> None:
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "http://localhost:5173, http://localhost:3000",
    )

    config = Configuration.from_env()

    assert config.cors_origins == [
        "http://localhost:5173",
        "http://localhost:3000",
    ]


def test_config_parses_numeric_env_values(monkeypatch) -> None:
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("LLM_TIMEOUT", "120")

    config = Configuration.from_env()

    assert config.port == 9000
    assert config.llm_timeout == 120
