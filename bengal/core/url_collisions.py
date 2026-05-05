"""Structured URL collision detection for site pages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.url_ownership import URLRegistry


@dataclass(frozen=True)
class URLCollisionClaimant:
    """One page or generated artifact claiming a URL."""

    source: str
    display_source: str
    owner: str = ""
    priority: int | None = None


@dataclass(frozen=True)
class URLCollisionRecord:
    """All claimants for one colliding URL."""

    url: str
    claimants: tuple[URLCollisionClaimant, ...]

    @property
    def count(self) -> int:
        """Number of claimants for this URL."""
        return len(self.claimants)


def _source_label(source: str, root_path: Path | None) -> str:
    if root_path is None:
        return source
    try:
        source_path = Path(source)
        if source_path.is_absolute():
            return str(source_path.relative_to(root_path))
    except ValueError:
        pass
    return source


def collect_url_collision_records(
    pages: Any,
    *,
    root_path: Path | None = None,
    url_registry: URLRegistry | None = None,
) -> list[URLCollisionRecord]:
    """Collect structured URL collision records from pages."""
    urls_seen: dict[str, list[str]] = {}

    for page in pages:
        url = page._path
        source = str(getattr(page, "source_path", page.title))
        urls_seen.setdefault(url, []).append(source)

    records: list[URLCollisionRecord] = []
    for url, sources in urls_seen.items():
        if len(sources) <= 1:
            continue

        claim = url_registry.get_claim(url) if url_registry is not None else None
        claimants = []
        for index, source in enumerate(sources):
            owner = claim.owner if claim is not None and index == 0 else ""
            priority = claim.priority if claim is not None and index == 0 else None
            claimants.append(
                URLCollisionClaimant(
                    source=source,
                    display_source=_source_label(source, root_path),
                    owner=owner,
                    priority=priority,
                )
            )

        records.append(URLCollisionRecord(url=url, claimants=tuple(claimants)))

    return records


def format_url_collision_text(record: URLCollisionRecord) -> str:
    """Format a plain compatibility message for one URL collision."""
    lines = [f"URL collision: {record.url}", "  Claimants:"]
    for index, claimant in enumerate(record.claimants, 1):
        owner_info = f" ({claimant.owner}, priority {claimant.priority})" if claimant.owner else ""
        lines.append(f"    {index}. {claimant.display_source}{owner_info}")
    lines.append("Tip: Give one page a unique slug, permalink, or output namespace")
    return "\n".join(lines)
