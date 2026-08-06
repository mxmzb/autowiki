---
title: 'PR 1: Configurable Wiki Update Timing'
type: source-summary
created: '2026-08-06'
updated: '2026-08-06'
slug: pr-1-configurable-wiki-update-timing
summary: Adds a persisted choice between same-PR and post-merge wiki update workflows.
tags:
- pull-request
- wiki-workflow
aliases: []
sources:
- '1'
related:
- autowiki
- wiki-update-modes
status: active
confidence: 1.0
review_by: null
supersedes: []
superseded_by: []
contradicts: []
tier: semantic
evergreen: false
entities: []
relations: []
---

## Summary

Pull request #1 made wiki-update timing an installation-level choice owned by
[[autowiki]]. The selected [[wiki-update-modes|wiki update mode]] is persisted in
`.autowiki.toml`, used to render the managed agent instructions, and preserved
when a wiki is reinitialized or upgraded.

## Key points

- New installations default to `alongside_pr`, where the coding agent asks about
  ingestion before PR creation and accepted wiki work joins the same branch.
- Installations can instead choose `after_merge`, which retains the separate
  post-merge suggestion workflow.
- Interactive `autowiki init` presents the choice; scripts can use
  `--wiki-update-mode alongside-pr|after-merge` or accept the recommended mode
  with `--yes`.
- Existing configurations without the field load and upgrade as `after_merge`,
  avoiding an unexpected workflow change.
- Re-running `autowiki init` preserves the saved choice unless an explicit mode
  is supplied, allowing an existing installation to switch without `--force`.

## Entities & concepts

- [[autowiki]] owns configuration, initialization, upgrades, and managed-block
  generation.
- [[wiki-update-modes]] defines the two supported publishing workflows and their
  compatibility behavior.

## Notes

This PR also established the mode used by this repository: `alongside_pr`.
The repository wiki itself was initialized separately after the feature merged,
so subsequent feature ingests can travel with their code PRs.
