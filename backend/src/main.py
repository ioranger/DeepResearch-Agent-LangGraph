"""FastAPI entrypoint exposing the DeepResearchAgent via HTTP."""

from __future__ import annotations

import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from dotenv import load_dotenv

# Load .env from the backend root directory
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field

from src.config import Configuration, SearchAPI
from src.agent import DeepResearchAgent

# ---------------------------------------------------------------------------
# Single shared configuration – constructed once, used everywhere
# ---------------------------------------------------------------------------
_DEFAULT_CONFIG = Configuration.from_env()

# Single log handler: level controlled by config, no duplicate ERROR sink
logger.remove()
logger.add(
    sys.stderr,
    level=_DEFAULT_CONFIG.log_level.upper(),
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <4}</level> | <cyan>{function}</cyan> | <cyan>{file}:{line}</cyan> | <level>{message}</level>",
    colorize=True,
)


class ResearchRequest(BaseModel):
    """Payload for triggering a research run."""

    topic: str = Field(..., description="Research topic supplied by the user")
    search_api: SearchAPI | None = Field(
        default=None,
        description="Override the default search backend configured via env",
    )


class ResearchResponse(BaseModel):
    """HTTP response containing the generated report and structured tasks."""

    report_markdown: str = Field(
        ..., description="Markdown-formatted research report including sections"
    )
    todo_items: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Structured TODO items with summaries and sources",
    )


def _mask_secret(value: Optional[str], visible: int = 4) -> str:
    """Mask sensitive tokens while keeping leading and trailing characters."""
    if not value:
        return "unset"
    if len(value) <= visible * 2:
        return "*" * len(value)
    return f"{value[:visible]}...{value[-visible:]}"


def _build_config(payload: ResearchRequest, base: Configuration) -> Configuration:
    """Build per-request config with optional search_api override."""
    overrides: dict[str, Any] = {}
    if payload.search_api is not None:
        overrides["search_api"] = payload.search_api
    if overrides:
        return Configuration.from_env(overrides=overrides)
    return base


# ---------------------------------------------------------------------------
# Lifespan (replaces deprecated @app.on_event)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    config: Configuration = app.state.config

    if config.llm_provider == "ollama":
        base_url = config.sanitized_ollama_url()
    elif config.llm_provider == "lmstudio":
        base_url = config.lmstudio_base_url
    else:
        base_url = config.llm_base_url or "unset"

    logger.info(
        "DeepResearch configuration loaded: provider=%s model=%s base_url=%s search_api=%s "
        "max_loops=%s fetch_full_page=%s tool_calling=%s strip_thinking=%s api_key=%s",
        config.llm_provider,
        config.resolved_model() or "unset",
        base_url,
        (config.search_api.value if isinstance(config.search_api, SearchAPI) else config.search_api),
        config.max_web_research_loops,
        config.fetch_full_page,
        config.use_tool_calling,
        config.strip_thinking_tokens,
        _mask_secret(config.llm_api_key),
    )
    yield


# ---------------------------------------------------------------------------
# App factory (accepts injectable config for testing)
# ---------------------------------------------------------------------------
def create_app(config: Configuration | None = None) -> FastAPI:
    """Create the FastAPI application.

    Accepts an optional ``config`` for test injection; falls back to
    ``from_env()`` when omitted.
    """
    config = config or Configuration.from_env()

    app = FastAPI(title="DeepResearch (LangGraph)", lifespan=lifespan)
    app.state.config = config

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- helpers ----

    def _get_cfg(request: Request) -> Configuration:
        return getattr(request.app.state, "config", config)

    # ---- endpoints ----

    @app.get("/healthz")
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/research", response_model=ResearchResponse)
    async def run_research(payload: ResearchRequest, request: Request) -> ResearchResponse:
        base_cfg = _get_cfg(request)
        try:
            req_cfg = _build_config(payload, base_cfg)
            agent = DeepResearchAgent(config=req_cfg)
            result = await agent.arun(payload.topic)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=500, detail="Research failed") from exc

        return ResearchResponse(
            report_markdown=(result.report_markdown or result.running_summary or ""),
            todo_items=[
                {
                    "id": item.id,
                    "title": item.title,
                    "intent": item.intent,
                    "query": item.query,
                    "status": item.status,
                    "summary": item.summary,
                    "sources_summary": item.sources_summary,
                    "citations": item.citations,
                    "note_id": item.note_id,
                    "note_path": item.note_path,
                }
                for item in result.todo_items
            ],
        )

    @app.post("/research/stream")
    async def stream_research(payload: ResearchRequest, request: Request) -> StreamingResponse:
        base_cfg = _get_cfg(request)
        try:
            req_cfg = _build_config(payload, base_cfg)
            agent = DeepResearchAgent(config=req_cfg)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        async def event_iterator() -> AsyncIterator[str]:
            try:
                async for event in agent.astream(payload.topic):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Streaming research failed")
                error_payload = {"type": "error", "detail": str(exc)}
                yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            event_iterator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    return app


# ---- default app for uvicorn ----
app = create_app(config=_DEFAULT_CONFIG)


if __name__ == "__main__":
    import uvicorn

    config = Configuration.from_env()
    uvicorn.run(
        app,  # reuse module-level `app`
        host=config.host,
        port=config.port,
        reload=True,
        log_level=config.log_level.lower(),
    )
