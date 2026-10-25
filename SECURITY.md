# Security policy

## Supported version

Security fixes are applied to the latest `0.2.x` release and the current `main`
branch. Earlier experimental commits are not supported.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability or include live
credentials, private prompts, or provider responses in an issue.

Use GitHub's private vulnerability reporting flow:

https://github.com/Pilvik1/extended-llm-council/security/advisories/new

Include the affected version or commit, reproduction steps, impact, and any
suggested mitigation. This is a hobby project maintained on a best-effort basis;
there is no guaranteed response or remediation SLA.

## Security model

- The backend binds to loopback by default and has no authentication layer.
- Provider API keys remain server-side and are never returned by readiness APIs.
- Local run and preset IDs are validated before filesystem access.
- GitHub Actions use read-only repository permissions and commit-pinned actions.
- Secret scanning and push protection are enabled on the public repository.

Extended Council is not designed for untrusted multi-user or internet-facing
deployment. If you expose it beyond loopback, add authentication, TLS, request
limits, and appropriate network isolation first.
