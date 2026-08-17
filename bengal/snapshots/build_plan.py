"""Frozen build-plan records for a later scheduler handoff.

RFC: ``plan/rfc-snapshot-build-plan-handoff.md`` (Proposed Records, migration
shape step 1). These types are construction-only: nothing consumes them yet.
``plugin_context`` / ``PluginBuildContext`` are omitted until a public protocol
exists.
"""

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class PagePlan:
    """Frozen facts for one page in a build plan."""

    source_path: str
    href: str
    template_name: str
    section_path: str | None = None


@dataclass(frozen=True, slots=True)
class SectionPlan:
    """Frozen facts for one section in a build plan."""

    path: str
    title: str
    page_hrefs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GeneratedOutputPlan:
    """Frozen facts for one generated artifact (sitemap, feed, search, …)."""

    kind: str
    path: str


@dataclass(frozen=True, slots=True)
class BuildPlan:
    """Immutable build-scoped handoff assembled after content discovery.

    ``template_dependencies`` accepts any mapping at construction and is stored
    as a ``MappingProxyType`` of tuples so callers cannot mutate the plan.
    """

    config_hash: str
    content_snapshot_id: str
    pages: tuple[PagePlan, ...]
    sections: tuple[SectionPlan, ...]
    template_dependencies: MappingProxyType[str, tuple[str, ...]]
    generated_outputs: tuple[GeneratedOutputPlan, ...] = ()

    def __post_init__(self) -> None:
        frozen = MappingProxyType(
            {key: tuple(deps) for key, deps in self.template_dependencies.items()}
        )
        object.__setattr__(self, "template_dependencies", frozen)


@dataclass(frozen=True, slots=True)
class IncrementalPlan:
    """Warm-build wrapper around a full ``BuildPlan``.

    Named invalidation reasons stay as strings until a later consumer defines
    a typed reason enum.
    """

    build_plan: BuildPlan
    changed_inputs: tuple[str, ...]
    affected_pages: tuple[str, ...]
    affected_outputs: tuple[str, ...]
    fallback_reasons: tuple[str, ...]
