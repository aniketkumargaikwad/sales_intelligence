# ADR-0001: Licence

Status: Accepted (design PR #1 merged 2026-10-22). Date: 2026-10-22.

## Context

We want other people (and other repos via the plugin) to be able to use the project. Some of the
best free tools in the stack are AGPL-3.0 (Reacher `check-if-email-exists`, Firecrawl) and some
reference projects are GPLv3 (OpenOutreach). Copying their code into our repo would force our
licence; calling them over the network as separate, unmodified services does not.

## Decision

License the repo under **MIT**.

- AGPL tools run as separate services (their upstream Docker images, unmodified) reached over HTTP.
  We never vendor or link their code.
- GPL/AGPL projects (OpenOutreach, Firecrawl) are design references only: we read them for ideas,
  we don't copy code.
- `docs/provider-matrix.md` records each dependency's licence and how we use it.

## Alternatives

- **AGPL-3.0**: would let us embed AGPL code, but discourages adoption and adds obligations for
  anyone hosting a modified version. We don't need to embed anything.
- **Apache-2.0**: similar to MIT plus a patent grant; a fine choice if the operator prefers it.

## Consequences

- Anyone can fork and use the code commercially.
- If we ever modify Reacher or Firecrawl, we must publish those modifications under AGPL; we avoid
  that by configuring, not patching, them.
