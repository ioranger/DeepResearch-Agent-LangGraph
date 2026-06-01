# Security Policy

English | [简体中文](SECURITY.zh-CN.md)

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.2.x   | Yes                |
| 0.1.x   | Best effort        |

## Reporting a Vulnerability

Please **do not** file a public issue for security problems.

Email the maintainers at the address listed on the repository's main page (or
open a private security advisory via GitHub: *Security → Advisories → New
draft security advisory*).

Include:
- A short description of the impact.
- Reproduction steps or a proof-of-concept.
- Affected versions.

We aim to acknowledge new reports within 3 business days and to ship a fix
within 30 days for critical issues.

## Secrets

The application reads API keys from environment variables
(`TAVILY_API_KEY`, `PERPLEXITY_API_KEY`, `LLM_API_KEY`, etc.). Never commit
`.env` — `.env.example` is the only file that should be checked in.
