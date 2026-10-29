# 1. Record architecture decisions

- Status: accepted
- Date: 2026-10-29

## Context and problem statement

Architectural choices (frameworks, hosting, data model) are easy to forget and hard to
reconstruct from code alone. A new reader should be able to see why something was chosen.

## Decision

Record each significant decision as a short Markdown file in `docs/adr/`, numbered
sequentially, using the [MADR](https://github.com/adr/madr) structure: context, decision,
consequences.

## Consequences

- Decisions are versioned alongside the code and reviewable in pull requests.
- Superseded decisions stay in the history with their status updated, not deleted.
