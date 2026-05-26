# llm-wiki

Initialize and maintain Karpathy-style LLM wikis in any project.

## Install (local dev)

```
uv tool install --editable .
```

## Usage

```
llm-wiki init [PATH] [--target claude|generic|auto] [--root]
llm-wiki version
```

`init` scaffolds a `wiki/` directory (`inbox/` sources, `pages/`, generated `index.md`/`log.md`,
`SCHEMA.md`) and injects a managed block into `CLAUDE.md`/`AGENTS.md`. See
`docs/superpowers/specs/2026-05-25-llm-wiki-phase-1-design.md` for the full design.
