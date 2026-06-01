# Example report: local-LLM research on LangGraph

> **Status:** Stub. Generated as a placeholder for the
> `examples/` directory. Replace with a real report produced by the agent
> before publishing v0.3.

## Topic

Investigate how LangGraph's `StateGraph` handles parallel fan-out when
multiple sub-tasks are produced by a single planner node.

## Expected inputs

- `SEARCH_API=duckduckgo` (no API key)
- `LLM_PROVIDER=ollama`, `LLM_MODEL_ID=qwen2.5:7b`

## Expected todos

1. Find the official LangGraph docs on `Send` and conditional edges.
2. Look for open-source examples of parallel research agents.
3. Compare with `asyncio.gather` patterns in plain LangChain.
4. Summarize trade-offs and write the report.

## Notes for maintainers

Drop a finished report Markdown here once the agent has been run end-to-end.
Keep file names stable (`NN-kebab-case.md`) so the index in
`examples/README.md` stays deterministic.
