"""LLM client factory for LangChain chat models."""

from __future__ import annotations

import logging

from langchain_core.language_models.chat_models import BaseChatModel

from src.config import Configuration

logger = logging.getLogger(__name__)


def build_chat_model(config: Configuration) -> BaseChatModel:
    """Instantiate a LangChain BaseChatModel from Configuration.

    Supports providers: ollama, lmstudio, openai, and any OpenAI-compatible
    endpoint via custom base_url + api_key.
    """
    provider = (config.llm_provider or "").strip().lower()
    model = config.resolved_model() or "llama3.2"

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        # ChatOllama uses native Ollama API (no /v1 suffix)
        base_url = config.ollama_base_url.rstrip("/")
        if base_url.endswith("/v1"):
            base_url = base_url[: -len("/v1")]
        logger.info("Building ChatOllama model=%s base_url=%s", model, base_url)
        return ChatOllama(model=model, base_url=base_url, temperature=0.0)

    # OpenAI-compatible path (openai / lmstudio / custom)
    from langchain_openai import ChatOpenAI

    if provider == "lmstudio":
        base_url = config.lmstudio_base_url
        api_key = config.llm_api_key or "lm-studio"
    else:
        base_url = config.llm_base_url
        api_key = config.llm_api_key or "EMPTY"

    kwargs: dict = {"model": model, "temperature": 0.0, "api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url

    logger.info("Building ChatOpenAI model=%s base_url=%s", model, base_url)
    return ChatOpenAI(**kwargs)
