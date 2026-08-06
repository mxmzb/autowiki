---
description: Lint the LLM wiki and fix issues
---

Run the **Lint** workflow in @wiki/SCHEMA.md.

Steps:
1. Run `autowiki lint --json` and read the reported issues.
2. Fix broken links, orphans, missing summaries, and stale pages. For flagged contradictions, read the
   pages and resolve or annotate them.
3. Re-run `autowiki lint` until it is clean.
