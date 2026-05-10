"""Immutable per-page rendering artifacts for post-render consumers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

type JsonFrozen = str | int | float | bool | None | tuple[str, tuple[Any, ...]]


@dataclass(frozen=True, slots=True)
class PageArtifact:
    """Frozen page record handed from rendering to postprocess/cache code."""

    source_path: Path
    url: str
    uri: str
    title: str
    description: str
    date: str | None
    date_iso: str | None
    plain_text: str
    excerpt: str
    content_preview: str
    word_count: int
    reading_time: int
    section: str
    tags: tuple[str, ...]
    dir: str
    enhanced_metadata: JsonFrozen = ("dict", ())
    is_autodoc: bool = False
    full_json_data: JsonFrozen | None = None
    json_output_path: Path | None = None
    raw_metadata: JsonFrozen = ("dict", ())
    anchors: tuple[str, ...] = ()

    @classmethod
    def from_accumulated(
        cls, data: Any, anchors: frozenset[str] | tuple[str, ...] = ()
    ) -> PageArtifact:
        """Create a frozen artifact from legacy AccumulatedPageData-like data."""
        json_output_path = getattr(data, "json_output_path", None)
        return cls(
            source_path=Path(data.source_path),
            url=str(getattr(data, "url", "")),
            uri=str(getattr(data, "uri", "")),
            title=str(getattr(data, "title", "")),
            description=str(getattr(data, "description", "")),
            date=getattr(data, "date", None),
            date_iso=getattr(data, "date_iso", None),
            plain_text=str(getattr(data, "plain_text", "")),
            excerpt=str(getattr(data, "excerpt", "")),
            content_preview=str(getattr(data, "content_preview", "")),
            word_count=int(getattr(data, "word_count", 0) or 0),
            reading_time=int(getattr(data, "reading_time", 0) or 0),
            section=str(getattr(data, "section", "")),
            tags=tuple(str(tag) for tag in getattr(data, "tags", ()) or ()),
            dir=str(getattr(data, "dir", "")),
            enhanced_metadata=_freeze_mapping(getattr(data, "enhanced_metadata", {}) or {}),
            is_autodoc=bool(getattr(data, "is_autodoc", False)),
            full_json_data=_freeze_json(getattr(data, "full_json_data", None)),
            json_output_path=Path(json_output_path) if json_output_path else None,
            raw_metadata=_freeze_mapping(getattr(data, "raw_metadata", {}) or {}),
            anchors=tuple(sorted(str(anchor) for anchor in anchors)),
        )

    @classmethod
    def from_cache_record(cls, record: dict[str, Any]) -> PageArtifact:
        """Create a frozen artifact from a persisted cache record."""
        json_output_path = record.get("json_output_path")
        return cls(
            source_path=Path(record["source_path"]),
            url=str(record.get("url", "")),
            uri=str(record.get("uri", "")),
            title=str(record.get("title", "")),
            description=str(record.get("description", "")),
            date=record.get("date"),
            date_iso=record.get("date_iso"),
            plain_text=str(record.get("plain_text", "")),
            excerpt=str(record.get("excerpt", "")),
            content_preview=str(record.get("content_preview", "")),
            word_count=int(record.get("word_count") or 0),
            reading_time=int(record.get("reading_time") or 0),
            section=str(record.get("section", "")),
            tags=tuple(str(tag) for tag in record.get("tags", ()) or ()),
            dir=str(record.get("dir", "")),
            enhanced_metadata=_freeze_mapping(record.get("enhanced_metadata", {}) or {}),
            is_autodoc=bool(record.get("is_autodoc", False)),
            full_json_data=_freeze_json(record.get("full_json_data")),
            json_output_path=Path(json_output_path) if json_output_path else None,
            raw_metadata=_freeze_mapping(record.get("raw_metadata", {}) or {}),
            anchors=tuple(str(anchor) for anchor in record.get("anchors", ()) or ()),
        )

    def to_accumulated(self, accumulated_type: Any) -> Any:
        """Rehydrate this artifact into the legacy AccumulatedPageData shape."""
        return accumulated_type(
            source_path=self.source_path,
            url=self.url,
            uri=self.uri,
            title=self.title,
            description=self.description,
            date=self.date,
            date_iso=self.date_iso,
            plain_text=self.plain_text,
            excerpt=self.excerpt,
            content_preview=self.content_preview,
            word_count=self.word_count,
            reading_time=self.reading_time,
            section=self.section,
            tags=list(self.tags),
            dir=self.dir,
            enhanced_metadata=_thaw_mapping(self.enhanced_metadata),
            is_autodoc=self.is_autodoc,
            full_json_data=_thaw_json(self.full_json_data),
            json_output_path=self.json_output_path,
            raw_metadata=_thaw_mapping(self.raw_metadata),
        )

    def to_cache_record(self) -> dict[str, Any]:
        """Serialize this artifact to the durable BuildCache record shape."""
        return {
            "source_path": str(self.source_path),
            "url": self.url,
            "uri": self.uri,
            "title": self.title,
            "description": self.description,
            "date": self.date,
            "date_iso": self.date_iso,
            "plain_text": self.plain_text,
            "excerpt": self.excerpt,
            "content_preview": self.content_preview,
            "word_count": self.word_count,
            "reading_time": self.reading_time,
            "section": self.section,
            "tags": list(self.tags),
            "dir": self.dir,
            "enhanced_metadata": _thaw_mapping(self.enhanced_metadata),
            "is_autodoc": self.is_autodoc,
            "full_json_data": _thaw_json(self.full_json_data),
            "json_output_path": str(self.json_output_path) if self.json_output_path else None,
            "raw_metadata": _thaw_mapping(self.raw_metadata),
            "anchors": list(self.anchors),
        }

    def fingerprint_record(self) -> dict[str, Any]:
        """Return stable fields that affect generated site-wide outputs."""
        record = self.to_cache_record()
        record.pop("anchors", None)
        record.pop("json_output_path", None)
        return record


def _freeze_mapping(value: dict[Any, Any]) -> JsonFrozen:
    return ("dict", tuple(sorted((str(key), _freeze_json(item)) for key, item in value.items())))


def _freeze_json(value: Any) -> JsonFrozen:
    if isinstance(value, str | int | float | bool | type(None)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return _freeze_mapping(value)
    if isinstance(value, list | tuple | set | frozenset):
        return ("list", tuple(_freeze_json(item) for item in value))
    return str(value)


def _thaw_mapping(value: JsonFrozen) -> dict[str, Any]:
    thawed = _thaw_json(value)
    return thawed if isinstance(thawed, dict) else {}


def _thaw_json(value: JsonFrozen) -> Any:
    if isinstance(value, tuple) and len(value) == 2:
        kind, payload = value
        if kind == "dict":
            return {str(key): _thaw_json(item) for key, item in payload}
        if kind == "list":
            return [_thaw_json(item) for item in payload]
    return value
