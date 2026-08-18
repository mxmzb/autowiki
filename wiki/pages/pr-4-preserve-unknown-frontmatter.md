---
title: 'PR 4: Preserve Unknown Frontmatter'
type: source-summary
created: '2026-08-18'
updated: '2026-08-18'
slug: pr-4-preserve-unknown-frontmatter
summary: Fixes silent deletion of custom frontmatter keys across all four page-writing
  paths.
tags:
- pull-request
- bugfix
- frontmatter
aliases: []
sources:
- '4'
related:
- autowiki
- page-frontmatter
status: active
confidence: 0.9
review_by: null
supersedes: []
superseded_by: []
contradicts: []
tier: semantic
evergreen: false
entities: []
relations:
- predicate: fixes
  target: page-frontmatter
---

## Summary

PR #4 (closing issue #3) makes [[autowiki]] preserve frontmatter keys its schema
does not define. `parse()` had kept only keys declared on `PageFrontmatter` and
`dump()` wrote back only `asdict(fm)`, so every read-modify-write path silently
deleted a wiki's own frontmatter. See [[page-frontmatter]] for the resulting
guarantee.

## Key points

- **Cause.** One line: `known = {k: v for k, v in data.items() if k in _FIELDS}`.
  Unknown keys were dropped at parse time and could never be re-emitted.
- **Fix.** Unknown keys ride in an `extra` mapping; `dump()` pops it and merges
  the contents at top level. With `sort_keys=False`, merge order is emit order,
  so known fields come first and unknowns follow in their original order.
- **Blast radius — four writing paths**, all now covered by tests that fail
  against the pre-fix code:

  | Path | Scope |
  |---|---|
  | `set` (`pages.py`) | one page |
  | `supersede` (`lifecycle.py`) | two pages — old and new |
  | `lint --fix` (`lint.py`) | **every page in the wiki** |
  | `upgrade` (`upgrade.py`) | every page in the wiki |

- **`maintain` is not affected** — it calls the read-only `run_lint`, not `fix`.
- **Three design constraints** the fix had to respect: `_FIELDS` is derived from
  the dataclass, so `extra` had to be excluded from it explicitly; `asdict()`
  would otherwise emit a literal nested `extra:` key; and unknown keys must skip
  `_coerce_shapes()` and `validate()`, since autowiki does not own the shape of a
  field it did not define.

## Entities & concepts

- [[autowiki]] — the affected CLI.
- [[page-frontmatter]] — the schema and the guarantee this PR established.

## Notes

Found in divine-rapier, which defines a `watch:` key for its own drift detection.
An agent bumped `updated` via `autowiki set` and the `watch:` lists went with it;
2 of 16 pages carried the key. That ratio is the hazard — too few pages for the
loss to be obvious in review, important enough that drift detection for them
would have been silently dead.

Deliberately out of scope, and flagged in issue #3 as its own change: `dump()`
also materialises every unset default, so a one-field edit produces a large diff.
That is behavioural, not data loss.
