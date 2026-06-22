"""Inspect :::{include} and :::{literalinclude} usage for a page."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.parsing.backends.patitas.directives.builtins.include import resolve_include_path

if TYPE_CHECKING:
    from bengal.protocols import SiteLike

_INCLUDE_DIRECTIVE = re.compile(
    r"^(\s*)(:{3,})\{(include|literalinclude)\}([^\n]*)",
    re.MULTILINE,
)


@dataclass(frozen=True, slots=True)
class IncludeReference:
    """One include directive reference found in a page."""

    directive: str
    target: str
    line_number: int
    resolved_path: Path | None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class IncludeInspection:
    """Include analysis for a single page."""

    page_path: Path
    references: tuple[IncludeReference, ...]

    @property
    def missing_targets(self) -> tuple[IncludeReference, ...]:
        return tuple(ref for ref in self.references if ref.resolved_path is None)


def inspect_page_includes(site: SiteLike, page_path: str | Path) -> IncludeInspection:
    """Resolve include targets declared in a page's markdown source."""
    root = Path(site.root_path)
    normalized = str(page_path).replace("\\", "/").lstrip("/")
    candidates = [
        root / normalized,
        root / "content" / normalized,
    ]
    if not normalized.endswith(".md"):
        candidates.extend(path.with_name("_index.md") for path in list(candidates))

    source_path: Path | None = None
    for candidate in candidates:
        if candidate.is_file():
            source_path = candidate.resolve()
            break
    if source_path is None:
        raise FileNotFoundError(f"Page not found: {page_path}")

    content = source_path.read_text(encoding="utf-8")
    references: list[IncludeReference] = []
    for match in _INCLUDE_DIRECTIVE.finditer(content):
        line_number = content.count("\n", 0, match.start()) + 1
        directive = match.group(3)
        target = match.group(4).strip()
        if not target:
            references.append(
                IncludeReference(
                    directive=directive,
                    target="",
                    line_number=line_number,
                    resolved_path=None,
                    error="empty path",
                )
            )
            continue
        resolved = resolve_include_path(
            target,
            source_file=source_path,
            site_root=root,
        )
        references.append(
            IncludeReference(
                directive=directive,
                target=target,
                line_number=line_number,
                resolved_path=resolved,
                error=None if resolved is not None else "not found",
            )
        )

    return IncludeInspection(page_path=source_path, references=tuple(references))


def format_include_inspection(inspection: IncludeInspection) -> str:
    """Format include inspection for CLI output."""
    lines = [f"Page: {inspection.page_path}"]
    if not inspection.references:
        lines.append("No include or literalinclude directives found.")
        return "\n".join(lines)

    lines.append(f"References: {len(inspection.references)}")
    for ref in inspection.references:
        status = str(ref.resolved_path) if ref.resolved_path else f"MISSING ({ref.error})"
        lines.append(f"  L{ref.line_number}  {ref.directive}  {ref.target}  ->  {status}")
    missing = inspection.missing_targets
    if missing:
        lines.append(f"Missing targets: {len(missing)}")
    return "\n".join(lines)


def inspection_to_dict(inspection: IncludeInspection) -> dict[str, Any]:
    """Serialize inspection for JSON output."""
    return {
        "page_path": str(inspection.page_path),
        "references": [
            {
                "directive": ref.directive,
                "target": ref.target,
                "line_number": ref.line_number,
                "resolved_path": str(ref.resolved_path) if ref.resolved_path else None,
                "error": ref.error,
            }
            for ref in inspection.references
        ],
        "missing_count": len(inspection.missing_targets),
    }
