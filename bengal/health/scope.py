"""Internal validation scopes for incremental health checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from bengal.health.report import CheckResult
    from bengal.protocols import PageLike, SiteLike


@dataclass(frozen=True)
class ValidationScope:
    """Internal description of which files a validator should inspect."""

    incremental: bool = False
    files_to_validate: frozenset[Path] | None = None
    cached_results_by_file: Mapping[Path, Sequence[CheckResult]] = field(default_factory=dict)

    @property
    def is_scoped(self) -> bool:
        """Return whether validation should be limited to selected files."""
        return self.files_to_validate is not None

    @property
    def cached_file_count(self) -> int:
        """Return number of unchanged files with cached validation state."""
        return len(self.cached_results_by_file)

    @property
    def cached_result_count(self) -> int:
        """Return number of cached check results available for reuse."""
        return sum(len(results) for results in self.cached_results_by_file.values())

    def pages_to_validate(self, site: SiteLike) -> list[PageLike]:
        """Return pages selected by this scope, or all pages for full validation."""
        if self.files_to_validate is None:
            return list(site.pages)
        return [
            page
            for page in site.pages
            if getattr(page, "source_path", None) in self.files_to_validate
        ]

    def cached_results(self) -> list[CheckResult]:
        """Flatten cached results in deterministic source-path order."""
        results = []
        for path in sorted(self.cached_results_by_file):
            results.extend(self.cached_results_by_file[path])
        return results


@dataclass(frozen=True)
class ScopedValidationContext:
    """Build-context proxy carrying a health validation scope."""

    base: Any
    validation_scope: ValidationScope

    def __getattr__(self, name: str) -> Any:
        if self.base is None:
            raise AttributeError(name)
        return getattr(self.base, name)


def with_validation_scope(build_context: Any, scope: ValidationScope | None) -> Any:
    """Attach a validation scope to a build context without mutating it."""
    if scope is None:
        return build_context
    return ScopedValidationContext(base=build_context, validation_scope=scope)


def get_validation_scope(build_context: Any) -> ValidationScope | None:
    """Return a validation scope from a scoped build context when present."""
    return getattr(build_context, "validation_scope", None)
