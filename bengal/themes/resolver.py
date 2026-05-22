"""Internal theme discovery and resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

ThemeSource = Literal["site-local", "bundled", "installed", "path"]


@dataclass(frozen=True, slots=True)
class ThemeRecord:
    """Resolved theme identity and metadata."""

    slug: str
    name: str
    source: ThemeSource
    path: Path | None
    metadata: dict[str, Any] = field(default_factory=dict)
    package: str | None = None
    distribution: str | None = None
    version: str | None = None


def is_theme_dir(path: Path) -> bool:
    """Return true when a directory has theme-like structure."""
    return path.is_dir() and (
        (path / "templates").is_dir()
        or (path / "theme.toml").is_file()
        or (path / "theme.yaml").is_file()
    )


def read_theme_metadata(theme_path: Path) -> dict[str, Any]:
    """Read best-effort metadata from ``theme.toml`` or ``theme.yaml``."""
    from bengal.themes.metadata import load_theme_metadata

    result = load_theme_metadata(theme_path)
    if result.errors:
        return {}
    return result.metadata.raw


def theme_display_name(slug: str, metadata: dict[str, Any]) -> str:
    """Return the user-facing theme name for a metadata dictionary."""
    raw = metadata.get("name")
    if isinstance(raw, dict):
        return str(raw.get("name") or slug)
    return str(raw or slug)


class ThemeResolver:
    """Resolve site-local, bundled, installed, and path-addressed themes."""

    def __init__(self, site_root: Path) -> None:
        self.site_root = site_root

    def iter_site_local(self) -> list[ThemeRecord]:
        themes_dir = self.site_root / "themes"
        if not themes_dir.is_dir():
            return []
        return [
            self._record_from_path(path, "site-local")
            for path in sorted(themes_dir.iterdir())
            if is_theme_dir(path)
        ]

    def iter_bundled(self) -> list[ThemeRecord]:
        from bengal.themes.utils import THEMES_ROOT

        return [
            self._record_from_path(path, "bundled")
            for path in sorted(THEMES_ROOT.iterdir())
            if is_theme_dir(path)
        ]

    def iter_installed(self) -> list[ThemeRecord]:
        from bengal.core.theme import get_installed_themes

        records: list[ThemeRecord] = []
        for slug, theme in sorted(get_installed_themes().items()):
            manifest = theme.resolve_resource_path("theme.toml")
            if manifest is None:
                manifest = theme.resolve_resource_path("theme.yaml")
            theme_path = manifest.parent if manifest is not None else None
            metadata = read_theme_metadata(theme_path) if theme_path is not None else {}
            records.append(
                ThemeRecord(
                    slug=slug,
                    name=theme_display_name(slug, metadata),
                    source="installed",
                    path=theme_path,
                    metadata=metadata,
                    package=theme.package,
                    distribution=theme.distribution,
                    version=theme.version,
                )
            )
        return records

    def iter_available(self) -> list[ThemeRecord]:
        """Return themes by resolution precedence, hiding lower-priority duplicates."""
        records: list[ThemeRecord] = []
        seen: set[str] = set()
        for collection in (self.iter_site_local(), self.iter_bundled(), self.iter_installed()):
            for record in collection:
                if record.slug in seen:
                    continue
                records.append(record)
                seen.add(record.slug)
        return records

    def resolve(self, theme: str) -> ThemeRecord | None:
        """Resolve a theme slug or explicit directory path."""
        path = Path(theme).expanduser()
        if is_theme_dir(path):
            return self._record_from_path(path.resolve(), "path")

        for record in self.iter_available():
            if record.slug == theme:
                return record
        return None

    def _record_from_path(self, path: Path, source: ThemeSource) -> ThemeRecord:
        metadata = read_theme_metadata(path)
        slug = path.name
        return ThemeRecord(
            slug=slug,
            name=theme_display_name(slug, metadata),
            source=source,
            path=path,
            metadata=metadata,
            version=str(metadata["version"]) if metadata.get("version") else None,
        )
