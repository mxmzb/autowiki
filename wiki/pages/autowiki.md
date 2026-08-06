---
title: autowiki
type: entity
created: '2026-08-06'
updated: '2026-08-06'
slug: autowiki
summary: A deterministic CLI for initializing and maintaining agent-authored project
  wikis.
tags:
- project
- cli
aliases: []
sources:
- '1'
related:
- wiki-update-modes
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

## Overview

`autowiki` is a deterministic CLI that scaffolds and maintains an agent-authored
project wiki. It owns structural bookkeeping—configuration, source vendoring,
page templates, indexing, linting, search, graph queries, lifecycle metadata, and
managed agent instructions—while an LLM does the reading and writing.

## Key facts

- A wiki can live in `wiki/` or at the project root.
- `.autowiki.toml` persists installation choices, including
  [[wiki-update-modes|wiki update timing]].
- Managed blocks in provider instruction files are regenerated from saved
  configuration during initialization and upgrades.
- `index.md` and `log.md` are generated, and inbox sources are added only through
  the CLI.

## Relationships

- Implements [[wiki-update-modes]].
- Pull request [[pr-1-configurable-wiki-update-timing]] introduced the persisted
  mode and mode-specific managed instructions.

## References

- Source `1`: pull request #1, “Add configurable wiki update timing.”
