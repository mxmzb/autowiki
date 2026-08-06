---
description: Query the LLM wiki and optionally crystallize a note
argument-hint: <question>
---

Answer the question `$ARGUMENTS` using the wiki, following the **Answer a query** workflow in @wiki/SCHEMA.md.

Steps:
1. Run `autowiki search "$ARGUMENTS"` and read the top pages.
2. Surface connections search misses with `autowiki graph neighbors <slug>` and `autowiki graph path <a> <b>`.
3. Synthesize an answer with `[[slug]]` citations to the pages you used.
4. If the answer is reusable, create a `note` page with `autowiki new-page`, then run `autowiki index`
   and `autowiki log query "$ARGUMENTS"`.
