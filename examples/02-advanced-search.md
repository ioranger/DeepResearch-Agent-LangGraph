# Example report: advanced-search research on a 2026 industry trend

> **Status:** Stub. Generated as a placeholder for the
> `examples/` directory. Replace with a real report produced by the agent
> before publishing v0.3.

## Topic

Map the state of local LLM serving in 2026: which runtimes (Ollama,
LMStudio, vLLM, llama.cpp) lead in adoption, and what new model families
landed this year.

## Expected inputs

- `SEARCH_API=advanced` (fans out across tavily + ddg + searxng + perplexity)
- `LLM_PROVIDER=custom`, `LLM_MODEL_ID=<reasoning model>`

## Expected todos

1. Pull recent benchmark posts from 2026 via Tavily.
2. Cross-check community discussions via SearXNG / DuckDuckGo.
3. Pull a synthesized answer from Perplexity.
4. Reconcile sources and write the final report.

## Notes for maintainers

Once the `advanced` backend is exercised end-to-end, paste the resulting
Markdown here. The stub intentionally leaves the body empty so it's obvious
in `git diff` that this is real output, not template boilerplate.
