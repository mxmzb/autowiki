from llm_wiki.config import WikiConfig
from llm_wiki.doctor import doctor, status
from llm_wiki.log import append_log
from llm_wiki.pages import new_page


def test_doctor_healthy_wiki_has_no_errors(wiki_cfg: WikiConfig):
    findings = doctor(wiki_cfg)
    assert not any(level == "error" for level, _ in findings)


def test_doctor_reports_missing_schema(wiki_cfg: WikiConfig):
    wiki_cfg.schema_file.unlink()
    findings = doctor(wiki_cfg)
    assert any(level == "error" and "SCHEMA.md" in msg for level, msg in findings)


def test_status_counts_pages_by_type(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="entity", title="A")
    new_page(wiki_cfg, type="entity", title="B")
    new_page(wiki_cfg, type="note", title="C")
    s = status(wiki_cfg)
    assert s["total"] == 3
    assert s["counts"]["entity"] == 2
    assert s["counts"]["note"] == 1


def test_status_reports_last_log_entry(wiki_cfg: WikiConfig):
    append_log(wiki_cfg, "ingest", "Latest Thing")
    s = status(wiki_cfg)
    assert "Latest Thing" in s["last_log"]


def test_doctor_index_not_stale_with_unparseable_page(fake_embeddings, wiki_cfg: WikiConfig):
    from llm_wiki import embeddings
    from llm_wiki.vectorindex import build_or_update

    new_page(wiki_cfg, type="concept", title="Good", summary="x")
    build_or_update(wiki_cfg, embeddings.get_backend(wiki_cfg))
    # an unparseable page can never be embedded; it must not make the index read "stale"
    (wiki_cfg.pages_dir / "broken.md").write_text("no frontmatter here\n")
    findings = doctor(wiki_cfg)
    assert not any("stale" in msg for _level, msg in findings)
    assert any("vectors indexed" in msg for _level, msg in findings)
