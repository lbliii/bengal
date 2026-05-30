"""Pure helpers for Page metadata compatibility properties."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def infer_title(metadata: Mapping[str, Any], source_path: Path) -> str:
    """Return explicit or filename-derived page title."""
    if "title" in metadata:
        return str(metadata["title"])

    if source_path.stem in ("_index", "index"):
        return humanize_stem(source_path.parent.name, replace_underscores=True)

    return humanize_stem(source_path.stem, replace_underscores=False)


def infer_nav_title(
    *,
    core_nav_title: str | None,
    metadata: Mapping[str, Any],
    fallback_title: str,
) -> str:
    """Return cached, explicit, or regular title for navigation."""
    if core_nav_title:
        return core_nav_title
    if "nav_title" in metadata:
        return str(metadata["nav_title"])
    return fallback_title


def coerce_weight(core_weight: Any, metadata: Mapping[str, Any]) -> float:
    """Return a sortable page weight, defaulting to infinity."""
    if core_weight is not None:
        weight = _float_or_none(core_weight)
        if weight is not None:
            return weight

    weight = _float_or_none(metadata.get("weight"))
    return weight if weight is not None else float("inf")


def infer_slug(metadata: Mapping[str, Any], source_path: Path) -> str:
    """Return explicit slug or source-path-derived slug."""
    if "slug" in metadata:
        return str(metadata["slug"])
    if source_path.stem == "_index":
        return source_path.parent.name
    return source_path.stem


def fallback_url(slug: str) -> str:
    """Return construction-time fallback URL for a page slug."""
    return f"/{slug}/"


def normalize_keywords(value: Any) -> list[str]:
    """Normalize frontmatter keywords to a non-empty string list."""
    if isinstance(value, str):
        return [k.strip() for k in value.split(",") if k.strip()]
    if isinstance(value, list):
        return [str(k).strip() for k in value if k is not None and str(k).strip()]
    return []


def normalize_edition(value: Any) -> list[str]:
    """Normalize edition frontmatter to a non-empty string list."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [str(v).strip() for v in value if v is not None and str(v).strip()]
    return []


def is_in_variant(metadata: Mapping[str, Any], variant: str | None) -> bool:
    """Return whether page metadata should be included for the build variant."""
    if variant is None or not str(variant).strip():
        return True
    editions = normalize_edition(metadata.get("edition"))
    if not editions:
        return True
    return variant in editions


def get_user_metadata(metadata: Mapping[str, Any], key: str, default: Any = None) -> Any:
    """Return user frontmatter only, excluding internal underscore keys."""
    if key.startswith("_"):
        return default
    return metadata.get(key, default)


def get_internal_metadata(metadata: Mapping[str, Any], key: str, default: Any = None) -> Any:
    """Return internal underscore-prefixed metadata only."""
    if not key.startswith("_"):
        key = f"_{key}"
    return metadata.get(key, default)


def is_generated(metadata: Mapping[str, Any]) -> bool:
    """Return whether metadata marks a page as generated."""
    return bool(metadata.get("_generated"))


def get_assigned_template(metadata: Mapping[str, Any]) -> str | None:
    """Return the explicitly assigned template from metadata."""
    template = metadata.get("template")
    if template is None:
        return None
    return str(template)


def get_content_type_name(metadata: Mapping[str, Any]) -> str | None:
    """Return the assigned content type from metadata."""
    content_type = metadata.get("content_type")
    if content_type is None:
        return None
    return str(content_type)


def humanize_stem(value: str, *, replace_underscores: bool) -> str:
    """Humanize a source path component for display."""
    value = value.replace("-", " ")
    if replace_underscores:
        value = value.replace("_", " ")
    return value.title()


def _float_or_none(value: Any) -> float | None:
    """Coerce value to float, returning None on invalid input."""
    try:
        return float(value)
    except ValueError, TypeError:
        return None
