from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import click
import typer

from . import __version__
from .catalog import index_is_current, write_index
from .config import (
    ALONGSIDE_PR,
    AFTER_MERGE,
    CONFIG_NAME,
    SCHEMA_VERSION,
    WikiConfig,
    find_wiki_root,
    load_config,
    normalize_wiki_update_mode,
)
from . import embeddings
from . import graph as graphlib
from . import vectorindex
from .doctor import doctor as doctor_check
from .doctor import status as status_report
from .hooks import install_hooks, run_hook, uninstall_hooks
from .lifecycle import review as lifecycle_review
from .lifecycle import supersede as lifecycle_supersede
from .lint import fix as lint_fix
from .lint import run_lint
from .log import append_log
from .pages import new_page, set_page_fields
from .quality import quality_report
from .scaffold import init_wiki, project_root_of, resolve_target
from .search import search as search_pages
from .sources import add_source, new_source, pending_sources, source_status
from .upgrade import upgrade as upgrade_wiki

app = typer.Typer(
    help="Initialize and maintain Karpathy-style LLM wikis.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def _root() -> None:
    """Initialize and maintain Karpathy-style LLM wikis."""


@app.command()
def version() -> None:
    """Print the autowiki tool and schema version."""
    typer.echo(f"autowiki {__version__} (schema v{SCHEMA_VERSION})")


@app.command()
def init(
    path: Path = typer.Argument(Path("."), help="Project directory to initialize."),
    target: str = typer.Option("auto", help="auto|claude|generic"),
    root: bool = typer.Option(False, "--root", help="Place the wiki at the project root."),
    force: bool = typer.Option(
        False,
        "--force",
        help="Refresh templates/config over an existing wiki (never overwrites index.md, log.md, pages, or inbox).",
    ),
    yes: bool = typer.Option(False, "--yes", help="Non-interactive."),
    hooks: bool = typer.Option(
        False, "--hooks", help="Install opt-in Claude hygiene hooks (any target)."
    ),
    wiki_update_mode: str = typer.Option(
        None,
        "--wiki-update-mode",
        help="alongside-pr|after-merge",
    ),
) -> None:
    """Initialize an LLM wiki in PATH (new or existing project)."""
    try:
        selected_mode = _resolve_wiki_update_mode(
            path,
            root_mode=root,
            requested=wiki_update_mode,
            assume_yes=yes,
        )
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2)
    resolved = resolve_target(path, target, yes)
    cfg, action = init_wiki(
        path,
        target=resolved,
        root_mode=root,
        force=force,
        with_hooks=hooks,
        wiki_update_mode=selected_mode,
    )
    typer.echo(
        f"Wiki {action} at {cfg.root} "
        f"(target: {cfg.target}, wiki updates: {cfg.wiki_update_mode})"
    )


def _resolve_wiki_update_mode(
    project_root: Path,
    *,
    root_mode: bool,
    requested: str | None,
    assume_yes: bool,
) -> str | None:
    """Resolve init's optional update mode without surprising existing installs."""
    if requested is not None:
        return normalize_wiki_update_mode(requested)

    project_root = Path(project_root).resolve()
    wiki_root = project_root if root_mode else project_root / "wiki"
    if (wiki_root / CONFIG_NAME).is_file():
        return None
    if assume_yes:
        return ALONGSIDE_PR

    choice = typer.prompt(
        "How should agents handle wiki updates?\n"
        "  1. Alongside code PRs (recommended)\n"
        "  2. Separately after code PRs merge",
        default="1",
        type=click.Choice(["1", "2"]),
    )
    return ALONGSIDE_PR if choice == "1" else AFTER_MERGE


def _resolve_cfg(path: Path) -> WikiConfig:
    root = find_wiki_root(path)
    if root is None:
        typer.echo(
            "No wiki found. Run `autowiki init` here, or pass --wiki <path-inside-a-wiki>.",
            err=True,
        )
        raise typer.Exit(1)
    return load_config(root)


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@app.command("add-source")
def add_source_cmd(
    src: str = typer.Argument(..., help="Local file path or URL."),
    title: str = typer.Option(None, "--title", help="Optional title used to derive the id."),
    id: str = typer.Option(None, "--id", help="Explicit source id."),
    wiki: Path = typer.Option(Path("."), "--wiki", help="A path inside the target wiki."),
) -> None:
    """Vendor a raw source (file or URL) into the wiki inbox. Prints the source id."""
    cfg = _resolve_cfg(wiki)
    try:
        sid = add_source(cfg, src, title=title, source_id=id)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    typer.echo(sid)


@app.command("new-page")
def new_page_cmd(
    title: str = typer.Argument(..., help="Page title."),
    page_type: str = typer.Option(..., "--type", help="entity|concept|source-summary|note|<custom>"),
    summary: str = typer.Option("", "--summary"),
    tags: str = typer.Option("", "--tags", help="Comma-separated."),
    sources: str = typer.Option("", "--sources", help="Comma-separated source ids."),
    slug: str = typer.Option(None, "--slug"),
    tier: str = typer.Option("semantic", "--tier", help="working|episodic|semantic|procedural"),
    confidence: float = typer.Option(None, "--confidence", help="0.0–1.0"),
    evergreen: bool = typer.Option(False, "--evergreen", help="Exempt from decay (timeless)."),
    wiki: Path = typer.Option(Path("."), "--wiki", help="A path inside the target wiki."),
) -> None:
    """Create a new wiki page with correct frontmatter. Prints the created path."""
    cfg = _resolve_cfg(wiki)
    try:
        path = new_page(
            cfg,
            type=page_type,
            title=title,
            summary=summary,
            tags=_csv(tags),
            sources=_csv(sources),
            slug=slug,
            tier=tier,
            confidence=confidence,
            evergreen=evergreen,
        )
    except (ValueError, FileExistsError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    typer.echo(str(path))


@app.command("set")
def set_cmd(
    slug: str = typer.Argument(..., help="Slug of the page to update."),
    confidence: float = typer.Option(None, "--confidence", help="0.0–1.0"),
    tier: str = typer.Option(None, "--tier", help="working|episodic|semantic|procedural"),
    status: str = typer.Option(None, "--status", help="active|draft|deprecated|superseded"),
    review_by: str = typer.Option(None, "--review-by", help="ISO date (YYYY-MM-DD)."),
    evergreen: bool = typer.Option(None, "--evergreen/--no-evergreen", help="Exempt from decay."),
    add_source: str = typer.Option("", "--add-source", help="Comma-separated source ids to add."),
    add_related: str = typer.Option("", "--add-related", help="Comma-separated slugs to add."),
    add_tag: str = typer.Option("", "--add-tag", help="Comma-separated tags to add."),
    wiki: Path = typer.Option(Path("."), "--wiki", help="A path inside the target wiki."),
) -> None:
    """Update lifecycle fields on a page's frontmatter (auto-bumps `updated`)."""
    cfg = _resolve_cfg(wiki)
    changes: dict = {}
    if confidence is not None:
        changes["confidence"] = confidence
    if tier is not None:
        changes["tier"] = tier
    if status is not None:
        changes["status"] = status
    if review_by is not None:
        changes["review_by"] = review_by
    if evergreen is not None:
        changes["evergreen"] = evergreen
    try:
        path = set_page_fields(
            cfg,
            slug,
            add_sources=_csv(add_source),
            add_related=_csv(add_related),
            add_tags=_csv(add_tag),
            **changes,
        )
    except FileNotFoundError:
        typer.echo(f"page not found: {slug}", err=True)
        raise typer.Exit(1)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    typer.echo(str(path))


@app.command("index")
def index_cmd(
    check: bool = typer.Option(False, "--check", help="Verify index is current; exit 2 if stale."),
    wiki: Path = typer.Option(Path("."), "--wiki", help="A path inside the target wiki."),
) -> None:
    """Rebuild index.md from page frontmatter (or --check that it is current)."""
    cfg = _resolve_cfg(wiki)
    if check:
        if index_is_current(cfg):
            typer.echo("index.md is current.")
        else:
            typer.echo("index.md is out of date; run `autowiki index`.", err=True)
            raise typer.Exit(2)
    else:
        write_index(cfg)
        typer.echo("index.md rebuilt.")


@app.command("log")
def log_cmd(
    action: str = typer.Argument(..., help="e.g. ingest|query|lint|note|edit."),
    title: str = typer.Argument(...),
    note: str = typer.Option(None, "--note"),
    wiki: Path = typer.Option(Path("."), "--wiki", help="A path inside the target wiki."),
) -> None:
    """Append an entry to log.md."""
    cfg = _resolve_cfg(wiki)
    append_log(cfg, action, title, note=note)
    typer.echo(f"logged: {action} | {title}")


@app.command("search")
def search_cmd(
    query: str = typer.Argument(...),
    page_type: str = typer.Option(None, "--type"),
    tag: str = typer.Option(None, "--tag"),
    limit: int = typer.Option(10, "--limit"),
    json_out: bool = typer.Option(False, "--json"),
    hybrid: bool = typer.Option(
        None, "--hybrid/--no-hybrid", help="Fuse keyword + semantic (default: auto when available)."
    ),
    wiki: Path = typer.Option(Path("."), "--wiki", help="A path inside the target wiki."),
) -> None:
    """Search the wiki (BM25, fused with vector retrieval when available)."""
    cfg = _resolve_cfg(wiki)
    if hybrid and not (embeddings.available(cfg) and vectorindex.load(cfg) is not None):
        typer.echo("Hybrid requested but no embeddings/index; using keyword search.", err=True)
    hits = search_pages(cfg, query, type=page_type, tag=tag, limit=limit, hybrid=hybrid)
    if json_out:
        typer.echo(json.dumps([asdict(h) for h in hits]))
        return
    if not hits:
        typer.echo("No matches.")
        return
    for h in hits:
        typer.echo(f"{h.slug}  —  {h.title}\n    {h.snippet}")


@app.command("lint")
def lint_cmd(
    fix: bool = typer.Option(False, "--fix", help="Apply safe auto-repairs."),
    json_out: bool = typer.Option(False, "--json"),
    wiki: Path = typer.Option(Path("."), "--wiki", help="A path inside the target wiki."),
) -> None:
    """Check wiki health. Exits 2 if any error-level issues remain."""
    cfg = _resolve_cfg(wiki)
    issues = lint_fix(cfg) if fix else run_lint(cfg)
    if json_out:
        typer.echo(json.dumps([asdict(i) for i in issues]))
    elif not issues:
        typer.echo("Clean — no issues.")
    else:
        for i in issues:
            location = i.page or "(wiki)"
            typer.echo(f"[{i.level}] {i.code} — {location}: {i.message}")
    if any(i.level == "error" for i in issues):
        raise typer.Exit(2)


@app.command("install-hooks")
def install_hooks_cmd(
    wiki: Path = typer.Option(Path("."), "--wiki", help="A path inside the target wiki."),
) -> None:
    """Install the opt-in Claude hygiene hooks into .claude/settings.json."""
    cfg = _resolve_cfg(wiki)
    project_root, _ = project_root_of(cfg)
    install_hooks(project_root)
    typer.echo(f"Installed autowiki hooks in {project_root / '.claude' / 'settings.json'}")


@app.command("uninstall-hooks")
def uninstall_hooks_cmd(
    wiki: Path = typer.Option(Path("."), "--wiki", help="A path inside the target wiki."),
) -> None:
    """Remove the autowiki hooks from .claude/settings.json."""
    cfg = _resolve_cfg(wiki)
    project_root, _ = project_root_of(cfg)
    uninstall_hooks(project_root)
    typer.echo("Removed autowiki hooks.")


@app.command("hook")
def hook_cmd(
    event: str = typer.Argument(..., help="pre-edit|post-edit (invoked by Claude hooks)."),
) -> None:
    """Internal: dispatch a Claude hook event (reads the hook payload on stdin)."""
    raw = "" if sys.stdin.isatty() else sys.stdin.read()
    code, message = run_hook(event, raw)
    if message:
        typer.echo(message, err=code != 0)
    raise typer.Exit(code)


@app.command("doctor")
def doctor_cmd(
    wiki: Path = typer.Option(Path("."), "--wiki", help="A path inside the target wiki."),
) -> None:
    """Report wiki health and setup. Exits 1 if any error-level finding."""
    cfg = _resolve_cfg(wiki)
    findings = doctor_check(cfg)
    marks = {"ok": "✓", "warn": "!", "error": "✗"}
    for level, message in findings:
        typer.echo(f"{marks.get(level, '-')} {message}")
    if any(level == "error" for level, _ in findings):
        raise typer.Exit(1)


@app.command("status")
def status_cmd(
    wiki: Path = typer.Option(Path("."), "--wiki", help="A path inside the target wiki."),
) -> None:
    """Print a content overview of the wiki."""
    cfg = _resolve_cfg(wiki)
    s = status_report(cfg)
    typer.echo(f"Pages: {s['total']}")
    for page_type, count in sorted(s["counts"].items()):
        typer.echo(f"  {page_type}: {count}")
    typer.echo("Status: " + ", ".join(f"{k} {v}" for k, v in sorted(s["by_status"].items())))
    typer.echo("Tiers:  " + ", ".join(f"{k} {v}" for k, v in sorted(s["by_tier"].items())))
    typer.echo(f"Review due: {s['review_due']}")
    typer.echo(f"Pending sources: {s['pending_sources']}")
    if s["last_log"]:
        typer.echo(f"Last log: {s['last_log']}")
    typer.echo(f"Lint: {s['lint_errors']} error(s), {s['lint_warnings']} warning(s)")


@app.command("upgrade")
def upgrade_cmd(
    wiki: Path = typer.Option(Path("."), "--wiki", help="A path inside the target wiki."),
) -> None:
    """Refresh SCHEMA/commands/managed-block/hooks to the installed version (content untouched)."""
    cfg = _resolve_cfg(wiki)
    result = upgrade_wiki(cfg)
    extras = ", hooks" if result["hooks_refreshed"] else ""
    typer.echo(
        f"Upgraded to schema v{SCHEMA_VERSION}: refreshed SCHEMA.md, "
        f"{result['commands']} command(s), managed block{extras}; "
        f"migrated {result['pages_migrated']} page(s)."
    )


graph_app = typer.Typer(help="Query the knowledge graph.", no_args_is_help=True)
app.add_typer(graph_app, name="graph")


@graph_app.command("neighbors")
def graph_neighbors_cmd(
    slug: str = typer.Argument(..., help="Page slug."),
    depth: int = typer.Option(1, "--depth"),
    predicate: str = typer.Option(None, "--predicate", help="Only traverse this edge type."),
    json_out: bool = typer.Option(False, "--json"),
    wiki: Path = typer.Option(Path("."), "--wiki"),
) -> None:
    """Pages connected to SLUG (undirected, within --depth)."""
    g = graphlib.build_graph(_resolve_cfg(wiki))
    try:
        results = graphlib.neighbors(g, slug, depth=depth, predicate=predicate)
    except KeyError:
        typer.echo(f"page not found: {slug}", err=True)
        raise typer.Exit(1)
    if json_out:
        typer.echo(json.dumps(results))
        return
    if not results:
        typer.echo("No neighbors.")
        return
    for r in results:
        typer.echo(f"{r['distance']}  {r['slug']}  —  {r['title']}")


@graph_app.command("path")
def graph_path_cmd(
    a: str = typer.Argument(...),
    b: str = typer.Argument(...),
    json_out: bool = typer.Option(False, "--json"),
    wiki: Path = typer.Option(Path("."), "--wiki"),
) -> None:
    """Shortest connection trail between two pages."""
    g = graphlib.build_graph(_resolve_cfg(wiki))
    result = graphlib.path(g, a, b)
    if json_out:
        typer.echo(json.dumps(result))
        return
    if result is None:
        typer.echo(f"No path between {a} and {b}.")
        raise typer.Exit(1)
    typer.echo(" -> ".join(result))


@graph_app.command("hubs")
def graph_hubs_cmd(
    limit: int = typer.Option(10, "--limit"),
    json_out: bool = typer.Option(False, "--json"),
    wiki: Path = typer.Option(Path("."), "--wiki"),
) -> None:
    """Most-connected pages."""
    g = graphlib.build_graph(_resolve_cfg(wiki))
    results = graphlib.hubs(g, limit=limit)
    if json_out:
        typer.echo(json.dumps(results))
        return
    if not results:
        typer.echo("No pages.")
        return
    for r in results:
        typer.echo(f"{r['degree']:>3}  {r['slug']}  —  {r['title']}")


@graph_app.command("stats")
def graph_stats_cmd(
    json_out: bool = typer.Option(False, "--json"),
    wiki: Path = typer.Option(Path("."), "--wiki"),
) -> None:
    """Graph size and composition."""
    s = graphlib.stats(graphlib.build_graph(_resolve_cfg(wiki)))
    if json_out:
        typer.echo(json.dumps(s))
        return
    typer.echo(f"Nodes: {s['nodes']}  Edges: {s['edges']}  Isolated: {s['isolated']}")
    for page_type, count in sorted(s["by_type"].items()):
        typer.echo(f"  {page_type}: {count}")


@graph_app.command("export")
def graph_export_cmd(
    format: str = typer.Option("json", "--format", help="json|dot"),
    wiki: Path = typer.Option(Path("."), "--wiki"),
) -> None:
    """Export the graph as JSON (node-link) or Graphviz DOT."""
    g = graphlib.build_graph(_resolve_cfg(wiki))
    try:
        typer.echo(graphlib.export(g, format))
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)


@app.command("embed")
def embed_cmd(
    wiki: Path = typer.Option(Path("."), "--wiki", help="A path inside the target wiki."),
) -> None:
    """Build/update the vector index (requires the embeddings extra)."""
    cfg = _resolve_cfg(wiki)
    backend = embeddings.get_backend(cfg)
    if backend is None:
        typer.echo(
            "Embeddings backend unavailable. Install with: pip install 'autowiki[embeddings]'",
            err=True,
        )
        raise typer.Exit(1)
    s = vectorindex.build_or_update(cfg, backend)
    typer.echo(
        f"Embedded with {backend.name}: +{s['added']} added, {s['updated']} updated, "
        f"{s['removed']} removed, {s['unchanged']} unchanged."
    )


@app.command("similar")
def similar_cmd(
    slug: str = typer.Argument(..., help="Page slug."),
    limit: int = typer.Option(10, "--limit"),
    json_out: bool = typer.Option(False, "--json"),
    wiki: Path = typer.Option(Path("."), "--wiki", help="A path inside the target wiki."),
) -> None:
    """Find pages most similar to SLUG (vector nearest neighbors)."""
    cfg = _resolve_cfg(wiki)
    if not embeddings.available(cfg) or vectorindex.load(cfg) is None:
        typer.echo(
            "No vector index. Install 'autowiki[embeddings]' and run `autowiki embed`.", err=True
        )
        raise typer.Exit(1)
    try:
        results = vectorindex.similar(cfg, slug, limit=limit)
    except KeyError:
        typer.echo(f"page not in index: {slug} (run `autowiki embed`)", err=True)
        raise typer.Exit(1)
    if json_out:
        typer.echo(json.dumps([{"slug": s, "score": sc} for s, sc in results]))
        return
    if not results:
        typer.echo("No similar pages.")
        return
    for s, sc in results:
        typer.echo(f"{sc:.3f}  {s}")


@app.command("quality")
def quality_cmd(
    limit: int = typer.Option(None, "--limit", help="Show only the N weakest pages."),
    json_out: bool = typer.Option(False, "--json"),
    wiki: Path = typer.Option(Path("."), "--wiki", help="A path inside the target wiki."),
) -> None:
    """Score pages by deterministic quality signals (weakest first)."""
    cfg = _resolve_cfg(wiki)
    items = quality_report(cfg, limit=limit)
    if json_out:
        typer.echo(json.dumps(items))
        return
    if not items:
        typer.echo("No pages.")
        return
    for d in items:
        missing = f"  (missing: {', '.join(d['missing'])})" if d["missing"] else ""
        typer.echo(f"{d['score']:.2f}  {d['slug']}{missing}")


@app.command("new-source")
def new_source_cmd(
    title: str = typer.Argument(..., help="Title for the new source (becomes its slugified id)."),
    id: str = typer.Option(None, "--id", help="Explicit source id."),
    ext: str = typer.Option(".md", "--ext", help="File extension."),
    wiki: Path = typer.Option(Path("."), "--wiki", help="A path inside the target wiki."),
) -> None:
    """Create a new (empty) source file in inbox/. Reads content from stdin if piped."""
    cfg = _resolve_cfg(wiki)
    content = "" if sys.stdin.isatty() else sys.stdin.read()
    try:
        path = new_source(cfg, title, source_id=id, ext=ext, content=content)
    except (ValueError, FileExistsError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    typer.echo(str(path))


@app.command("sources")
def sources_cmd(
    pending: bool = typer.Option(False, "--pending", help="Show only un-ingested sources."),
    json_out: bool = typer.Option(False, "--json"),
    wiki: Path = typer.Option(Path("."), "--wiki", help="A path inside the target wiki."),
) -> None:
    """List inbox sources and whether each has been ingested into a page."""
    cfg = _resolve_cfg(wiki)
    items = source_status(cfg)
    if pending:
        items = [d for d in items if not d["ingested"]]
    if json_out:
        typer.echo(json.dumps(items))
        return
    if not items:
        typer.echo("No pending sources." if pending else "No sources.")
        return
    for d in items:
        typer.echo(f"[{'ingested' if d['ingested'] else 'pending'}]  {d['id']}")


@app.command("supersede")
def supersede_cmd(
    old: str = typer.Argument(..., help="Slug of the page being superseded."),
    new: str = typer.Argument(..., help="Slug of the replacement page."),
    wiki: Path = typer.Option(Path("."), "--wiki", help="A path inside the target wiki."),
) -> None:
    """Mark OLD as superseded by NEW (wires both sides; OLD stays searchable)."""
    cfg = _resolve_cfg(wiki)
    try:
        lifecycle_supersede(cfg, old, new)
    except FileNotFoundError as exc:
        typer.echo(f"page not found: {exc}", err=True)
        raise typer.Exit(1)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    typer.echo(f"{old} is now superseded by {new}.")


@app.command("review")
def review_cmd(
    threshold: float = typer.Option(0.5, "--threshold", help="Retention below this is 'decayed'."),
    json_out: bool = typer.Option(False, "--json"),
    wiki: Path = typer.Option(Path("."), "--wiki", help="A path inside the target wiki."),
) -> None:
    """List pages needing attention (overdue/decayed/low-confidence; evergreen excluded)."""
    cfg = _resolve_cfg(wiki)
    items = lifecycle_review(cfg, threshold=threshold)
    if json_out:
        typer.echo(json.dumps(items))
        return
    if not items:
        typer.echo("Nothing needs review.")
        return
    for item in items:
        typer.echo(f"{item['retention']:.2f}  {item['slug']}  ({', '.join(item['reasons'])})")


@app.command("maintain")
def maintain_cmd(
    wiki: Path = typer.Option(Path("."), "--wiki", help="A path inside the target wiki."),
) -> None:
    """Deterministic maintenance pass: rebuild index, then report lint/review/pending/quality."""
    cfg = _resolve_cfg(wiki)
    write_index(cfg)
    issues = run_lint(cfg)
    errors = sum(1 for i in issues if i.level == "error")
    warnings = sum(1 for i in issues if i.level == "warning")
    weak = sum(1 for d in quality_report(cfg) if d["score"] < 0.5)
    typer.echo("Maintenance report:")
    typer.echo("  index: rebuilt")
    typer.echo(f"  lint: {errors} error(s), {warnings} warning(s)")
    typer.echo(f"  review due: {len(lifecycle_review(cfg))}")
    typer.echo(f"  pending sources: {len(pending_sources(cfg))}")
    typer.echo(f"  low-quality pages: {weak}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
