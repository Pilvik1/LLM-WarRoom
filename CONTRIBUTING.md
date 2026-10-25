# Contributing

Extended Council is a small hobby project. Focused bug reports, reproducible
provider issues, documentation fixes, and narrowly scoped pull requests are
welcome.

## Before opening an issue

- Search existing issues.
- Remove API keys, private prompts, model outputs, and personal data.
- Include the operating system, Python/Node versions, provider adapter, and a
  minimal reproduction when relevant.
- Report security issues privately according to [SECURITY.md](SECURITY.md).

## Development setup

```bash
uv sync --frozen --group dev
cd frontend && npm ci && cd ..
cp .env.example .env
```

Run the validation gates before opening a pull request:

```bash
uv run pytest
cd frontend
npm test
npm run lint
npm run build
npm audit --omit=dev
```

Keep changes small, explain behavioral tradeoffs, and add tests for new runtime
behavior. Do not commit `.env`, local `data/` artifacts, generated provider
responses, or credentials.

## Contribution terms

No CLA or DCO sign-off is required. By submitting a contribution, you agree that
it may be distributed under the repository's license and that you have the right
to submit it.

Be respectful and discuss ideas, code, and evidence rather than people. Abuse,
harassment, and disclosure of another person's private data are not acceptable.
