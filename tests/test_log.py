from autowiki.config import WikiConfig
from autowiki.log import append_log


def test_append_log_canonical_line(wiki_cfg: WikiConfig):
    append_log(wiki_cfg, "ingest", "Some Source")
    text = wiki_cfg.log_file.read_text()
    assert "## [" in text
    assert "ingest | Some Source" in text


def test_append_log_accumulates_in_order(wiki_cfg: WikiConfig):
    append_log(wiki_cfg, "ingest", "First")
    append_log(wiki_cfg, "query", "Second")
    text = wiki_cfg.log_file.read_text()
    assert text.index("First") < text.index("Second")


def test_append_log_creates_header_when_absent(wiki_cfg: WikiConfig):
    wiki_cfg.log_file.unlink()
    append_log(wiki_cfg, "note", "Fresh")
    text = wiki_cfg.log_file.read_text()
    assert text.startswith("# Log")
    assert "note | Fresh" in text


def test_append_log_note(wiki_cfg: WikiConfig):
    append_log(wiki_cfg, "ingest", "X", note="extra detail")
    assert "> extra detail" in wiki_cfg.log_file.read_text()
