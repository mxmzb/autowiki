from __future__ import annotations

import shutil
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from .config import WikiConfig
from .pages import slugify


def _is_url(src: str) -> bool:
    return src.startswith(("http://", "https://"))


def add_source(
    cfg: WikiConfig,
    src: str,
    title: str | None = None,
    source_id: str | None = None,
) -> str:
    """Vendor a raw source (local file or URL) into inbox/. Returns its source id.

    Idempotent: re-adding a source whose id already exists returns the id without
    refetching/recopying.
    """
    cfg.inbox_dir.mkdir(parents=True, exist_ok=True)

    if _is_url(src):
        parsed = urlparse(src)
        stem = Path(parsed.path).stem or parsed.netloc
        ext = Path(parsed.path).suffix or ".html"
    else:
        path = Path(src)
        if not path.is_file():
            raise FileNotFoundError(f"source file not found: {src}")
        stem = path.stem
        ext = path.suffix

    sid = source_id or slugify(title or stem)
    if not sid:
        raise ValueError(f"could not derive a source id from {src!r}; pass an explicit id")

    # Idempotent / unique by stem across any extension: if a source with this id
    # already exists (regardless of extension), return it without recopying.
    for existing in cfg.inbox_dir.iterdir():
        if existing.is_file() and existing.stem == sid:
            return sid
    target = cfg.inbox_dir / f"{sid}{ext}"

    if _is_url(src):
        try:
            with urllib.request.urlopen(src, timeout=30) as resp:
                data = resp.read()
        except (urllib.error.URLError, OSError) as exc:
            raise RuntimeError(f"failed to fetch {src}: {exc}") from exc
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(target)  # atomic; nothing partial left on the failure path above
    else:
        shutil.copyfile(src, target)

    return sid
