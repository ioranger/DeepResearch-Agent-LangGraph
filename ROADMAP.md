# Roadmap

English | [简体中文](ROADMAP.zh-CN.md)

This roadmap tracks the public evolution of **DeepResearch on LangGraph**. It
mirrors internal `.comate/specs/` plans but is intentionally shorter so
visitors can see direction at a glance.

## Now — v0.2.x (Quality Foundation)
- [x] Quality foundation harness: pytest scaffolding, config drift fixes, `advanced` search backend, SSE protocol test.
- [x] CI workflow (lint + tests).
- [x] Public docs: README, LICENSE, CHANGELOG, ROADMAP, CONTRIBUTING, SECURITY.
- [x] Docker + docker-compose with optional Ollama profile.
- [ ] Public screencast / demo link in README.

## Next — v0.3.x (Search Reliability)
- [ ] Concurrent backend fan-out in `_search_advanced` (asyncio.gather, per-backend timeout).
- [ ] Frontend surfacing of per-backend latency and result counts.
- [ ] `wiki_query` / `wiki_search` MCP tool wrappers (currently in `tools/`, not wired).

## Later — v0.4.x (Agent Capability)
- [ ] ReAct agent node so the LLM can choose when to use `note_tool` / `search_tool`.
- [ ] Locale-aware prompts (English / 中文 / 日本語) driven by UI language.
- [ ] HTTP runtime API hardening: `POST /v1/research` and `/v1/sessions`.

## Stretch — v1.0
- [ ] Stable public API for embedding the agent in IDEs and web UIs.
- [ ] First-class evaluation harness on a held-out research benchmark.
- [ ] Distributed research workers (multi-tenant scheduling).

See `.comate/specs/` for full design notes on each milestone.
