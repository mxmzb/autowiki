from __future__ import annotations

import dataclasses
import datetime as dt
from dataclasses import asdict, dataclass, field

import yaml

PAGE_TYPES = ("source-summary", "entity", "concept", "note")
STATUSES = ("active", "draft", "deprecated", "superseded")
TIERS = ("working", "episodic", "semantic", "procedural")
FM_DELIM = "---"


@dataclass
class PageFrontmatter:
    # Required (defaulted to "" so parse never crashes; validate() enforces non-empty)
    title: str = ""
    type: str = ""
    created: str = ""
    updated: str = ""
    # v1 active fields
    slug: str = ""
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    # v2-ready seam (validated for shape, behavior lands in later phases)
    status: str = "active"
    confidence: float | None = None
    review_by: str | None = None
    supersedes: list[str] = field(default_factory=list)
    superseded_by: list[str] = field(default_factory=list)
    contradicts: list[str] = field(default_factory=list)
    tier: str = "semantic"
    entities: list[dict] = field(default_factory=list)
    relations: list[dict] = field(default_factory=list)


_FIELDS = {f.name for f in dataclasses.fields(PageFrontmatter)}

# Field-shape groups used to coerce hand-edited frontmatter into safe types so
# downstream consumers (lint/index/search) never crash on a malformed page.
_STR_LIST_FIELDS = (
    "tags",
    "aliases",
    "sources",
    "related",
    "supersedes",
    "superseded_by",
    "contradicts",
)
_DICT_LIST_FIELDS = ("entities", "relations")
_STR_FIELDS = ("title", "type", "created", "updated", "slug", "summary", "status", "tier")


def _coerce_shapes(data: dict) -> dict:
    out = dict(data)
    for key in _STR_LIST_FIELDS:
        if key in out:
            value = out[key]
            if isinstance(value, list):
                out[key] = [str(item) for item in value]
            elif value is None:
                out[key] = []
            else:
                out[key] = [str(value)]
    for key in _DICT_LIST_FIELDS:
        if key in out and not isinstance(out[key], list):
            out[key] = []
    for key in _STR_FIELDS:
        if key in out and out[key] is not None and not isinstance(out[key], str):
            out[key] = str(out[key])
    return out


def today() -> str:
    return dt.date.today().isoformat()


def parse(text: str) -> tuple[PageFrontmatter, str]:
    if not text.startswith(FM_DELIM):
        raise ValueError("page is missing YAML frontmatter")
    _, fm_block, body = text.split(FM_DELIM, 2)
    data = yaml.safe_load(fm_block) or {}
    known = {k: v for k, v in data.items() if k in _FIELDS}
    return PageFrontmatter(**_coerce_shapes(known)), body.lstrip("\n")


def dump(fm: PageFrontmatter, body: str) -> str:
    fm_yaml = yaml.safe_dump(asdict(fm), sort_keys=False, allow_unicode=True).strip()
    return f"{FM_DELIM}\n{fm_yaml}\n{FM_DELIM}\n\n{body.rstrip()}\n"


def validate(
    fm: PageFrontmatter, allowed_types: tuple[str, ...] = PAGE_TYPES
) -> list[str]:
    errors: list[str] = []
    for req in ("title", "type", "created", "updated"):
        if not getattr(fm, req):
            errors.append(f"missing required field: {req}")
    if fm.type and fm.type not in allowed_types:
        errors.append(f"unknown type: {fm.type}")
    if fm.status not in STATUSES:
        errors.append(f"invalid status: {fm.status}")
    if fm.tier not in TIERS:
        errors.append(f"invalid tier: {fm.tier}")
    if fm.confidence is not None:
        try:
            in_range = 0.0 <= float(fm.confidence) <= 1.0
        except (TypeError, ValueError):
            in_range = False
        if not in_range:
            errors.append("confidence must be a number between 0 and 1")
    return errors
