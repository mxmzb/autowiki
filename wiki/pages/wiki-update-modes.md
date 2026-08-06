---
title: Wiki Update Modes
type: concept
created: '2026-08-06'
updated: '2026-08-06'
slug: wiki-update-modes
summary: Controls whether agents include wiki updates with code PRs or suggest them
  after merge.
tags:
- workflow
- pull-request
- wiki
aliases: []
sources:
- '1'
related:
- autowiki
- pr-1-configurable-wiki-update-timing
status: active
confidence: 1.0
review_by: null
supersedes: []
superseded_by: []
contradicts: []
tier: semantic
evergreen: true
entities: []
relations: []
---

## Definition

Wiki update modes are a persisted [[autowiki]] installation choice controlling
when coding agents offer to ingest completed work:

- `alongside_pr`: ask immediately before creating a code PR. If accepted, create
  a draft PR for a stable source URL, ingest it, push wiki changes to the same
  branch, and then continue the normal ready/merge flow.
- `after_merge`: keep wiki work separate and suggest ingestion after substantial
  work, especially after a PR or feature branch merges.

## Why it matters

Timing determines whether durable project knowledge lands atomically with the
change it documents or arrives in a follow-up PR. Persisting the choice prevents
`autowiki upgrade` from overwriting a repository's preferred workflow.

New installations default to `alongside_pr`. A legacy configuration without the
field resolves to `after_merge`, preserving its established behavior. Users can
change an existing installation by re-running `autowiki init` with
`--wiki-update-mode`.

## Related concepts

- [[autowiki]] renders the selected policy into managed agent instructions.
- [[pr-1-configurable-wiki-update-timing]] records the implementation and
  compatibility decisions.

## References

- Source `1`: pull request #1, “Add configurable wiki update timing.”
