---
title: Page Frontmatter
type: concept
created: '2026-08-18'
updated: '2026-08-18'
slug: page-frontmatter
summary: The page schema autowiki reads and writes; keys it does not define are preserved
  verbatim.
tags:
- frontmatter
- schema
- data-integrity
aliases: []
sources:
- '4'
related:
- autowiki
- pr-4-preserve-unknown-frontmatter
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
- predicate: defined-by
  target: autowiki
---

## Definition

Every page in an [[autowiki]] wiki opens with a YAML frontmatter block. The
schema lives in `src/autowiki/frontmatter.py` as the `PageFrontmatter` dataclass,
and `parse()` / `dump()` are the only two functions that read and write it.

Four fields are required — `title`, `type`, `created`, `updated`. The rest carry
catalog data (`summary`, `tags`, `aliases`, `slug`), graph edges (`related`,
`relations`, `entities`, `sources`), and lifecycle state (`status`, `confidence`,
`review_by`, `tier`, `evergreen`, `supersedes`, `superseded_by`, `contradicts`).

## The unknown-key guarantee

**A key the schema does not define is ignored but never dropped.** It survives
every path that rewrites a page, and is re-emitted after the known fields in its
original order.

This is a real guarantee rather than an accident, because a wiki is expected to
extend the schema. `SCHEMA.md` tells maintainers the file is theirs to edit, and
`extra_types` already lets them add page types — a project that invents a
frontmatter key to go with them should not lose it.

Mechanically, `parse()` splits the block into keys the dataclass declares and
everything else; the remainder rides in an `extra` mapping that `dump()` merges
back at top level. Unknown keys deliberately skip `_coerce_shapes()` and
`validate()` — autowiki does not own the shape of a field it did not define.

A live example: divine-rapier defines `watch:` (repo paths whose commits make a
page's facts suspect) and drives its own drift script from it. autowiki knows
nothing about `watch:` and does not need to.

## Why it matters

Before [[pr-4-preserve-unknown-frontmatter]] the guarantee did not hold, and the
failure was silent. Four commands rewrite pages — `set`, `supersede`,
`lint --fix`, and `upgrade` — and each one deleted custom keys with no warning.

`lint --fix` was the dangerous one: it rewrites *every* page in the wiki
unconditionally, so a single invocation could strip a custom field from the whole
wiki at once, while its help text advertised "safe auto-repairs".

The failure mode is worth remembering beyond this bug. A dropped `watch:` list
does not raise anything — the page simply stops being reported as drifted, which
is indistinguishable from "not drifting". Deleted metadata fails quiet, so the
write path is where it has to be defended.

## Related concepts

- [[autowiki]] — the CLI that owns the schema.
- [[pr-4-preserve-unknown-frontmatter]] — the change that established the guarantee.
- [[wiki-update-modes]] — another setting where behaviour is configured per wiki.

## References

- `src/autowiki/frontmatter.py` — `PageFrontmatter`, `parse`, `dump`.
- `README.md` — states the preservation guarantee.
- `src/autowiki/templates/SCHEMA.md` — "Customizing your wiki".
