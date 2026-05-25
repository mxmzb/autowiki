---
description: Ingest a source into the LLM wiki
argument-hint: <path-or-url>
---

Ingest the source `$ARGUMENTS` into the wiki, following the **Ingest a source** workflow in @wiki/SCHEMA.md.

Steps:
1. Run `llm-wiki add-source $ARGUMENTS` and note the source id.
2. Read the source; identify entities, concepts, and key claims; briefly discuss findings with me.
3. Create a `source-summary` page with `llm-wiki new-page`, then create/update entity and concept pages
   (run `llm-wiki search` first to avoid duplicates). Cross-link with `[[slug]]`.
4. Run `llm-wiki index`, then `llm-wiki log ingest "<title>"`, then `llm-wiki lint` and fix anything reported.
