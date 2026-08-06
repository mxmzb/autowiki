<!-- BEGIN autowiki (managed) -->
## LLM Wiki
This project maintains an LLM wiki under `wiki/` via the `autowiki` CLI.
Full maintainer rules: `wiki/SCHEMA.md`

Invariants — do not violate:
- `wiki/index.md` and `wiki/log.md` are GENERATED. Never hand-edit; use `autowiki index` / `autowiki log`.
- `wiki/inbox/` is read-only raw sources. Add only via `autowiki add-source`.
- Create pages with `autowiki new-page` (correct frontmatter), never by hand.
- Before creating a page, `autowiki search` first — update an existing page rather than duplicate.
- After any wiki change, run `autowiki lint` (then `autowiki index`).

Don't modify the wiki unprompted — act on it only when asked (/wiki-ingest,
/wiki-query, /wiki-lint). When substantial work is ready to publish, ask whether
to include a wiki ingest immediately before creating the PR, unless the user has
already said to include or skip it. If accepted, create a draft PR to obtain its
stable URL, run /wiki-ingest, commit and push the wiki changes to the same branch,
then mark the PR ready and continue the normal review/merge flow. If declined,
publish normally. If ingestion fails, leave the PR as a draft until the failure is
resolved or the user explicitly chooses to skip it.
Do not suggest a separate wiki ingest after the PR or branch is merged.
See `wiki/SCHEMA.md` for the full ingest/query/lint workflows.
<!-- END autowiki (managed) -->
