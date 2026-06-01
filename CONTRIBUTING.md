# Contributing to DeepResearch on LangGraph

English | [简体中文](CONTRIBUTING.zh-CN.md)

Thanks for your interest in contributing! This project is a LangGraph-based deep
research agent with a Vue 3 frontend. Issues, PRs, and Discussions are all
welcome.

## Development Setup

Prerequisites:
- Python `>=3.10,<3.15`
- [uv](https://docs.astral.sh/uv/) for Python dependency management
- Node.js `>=20` for the frontend

```bash
# Backend
cd backend
uv sync
cp .env.example .env  # then fill in API keys

# Frontend
cd ../frontend
npm install
```

## Running Tests

```bash
cd backend
uv run ruff check src tests
uv run pytest
```

The integration test for the SSE stream is fast and offline; it monkeypatches
the agent so you do not need real API keys to validate the protocol.

## Pull Requests

1. Fork the repo and create a topic branch (`feat/<name>`, `fix/<name>`, `docs/<name>`).
2. Keep PRs small and focused. One concern per PR.
3. Use [Conventional Commits](https://www.conventionalcommits.org/) for the
   commit title: `feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`.
4. Add or update tests for any behavior change. New features without tests
   are unlikely to be merged.
5. Make sure `uv run ruff check src tests && uv run pytest` is green before
   requesting review.

## Reporting Bugs

Use the **Bug report** issue template. Include:
- Reproduction steps (curl command or frontend flow).
- Expected vs. actual behavior.
- Backend logs (set `LOG_LEVEL=DEBUG`).
- OS, Python version, `uv --version`.

## Feature Requests

Use the **Feature request** template. Describe the user story, not just the
solution. Cross-link any related issues.

## Code of Conduct

By participating you agree to abide by the [Code of Conduct](.github/CODE_OF_CONDUCT.md)
(this is a placeholder — adopt the Contributor Covenant before going public).

## License

By contributing, you agree that your contributions will be licensed under the
project's [MIT License](LICENSE).
