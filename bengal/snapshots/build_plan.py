"""Frozen build-plan records for a later scheduler handoff.

RFC: ``plan/rfc-snapshot-build-plan-handoff.md`` (Proposed Records, migration
shape step 1). These types are construction-only: nothing consumes them yet.
``plugin_context`` / ``PluginBuildContext`` are omitted until a public protocol
exists.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.snapshots.types import PageSnapshot, SectionSnapshot, SiteSnapshot


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


def assemble_build_plan(
    snapshot: SiteSnapshot,
    *,
    config_hash: str,
    content_snapshot_id: str,
) -> BuildPlan:
    """Map a frozen ``SiteSnapshot`` into a frozen ``BuildPlan``.

    Construction-only: WaveScheduler still takes ``self.site``. Callers pass
    ``config_hash`` and ``content_snapshot_id``; this function does not hash.
    ``generated_outputs`` is empty until a later slice fills it.
    """
    graph = snapshot.schedule.template_dependency_graph
    template_dependencies = MappingProxyType(
        {name: tuple(sorted(graph[name])) for name in sorted(graph)}
    )
    return BuildPlan(
        config_hash=config_hash,
        content_snapshot_id=content_snapshot_id,
        pages=tuple(_page_plan(page) for page in snapshot.pages),
        sections=tuple(_section_plan(section) for section in snapshot.sections),
        template_dependencies=template_dependencies,
        generated_outputs=(),
    )


def _page_plan(page: PageSnapshot) -> PagePlan:
    return PagePlan(
        source_path=str(page.source_path),
        href=page.href,
        template_name=page.template_name,
        section_path=_section_path(page.section),
    )


def _section_path(section: SectionSnapshot | None) -> str | None:
    if section is None:
        return None
    if section.path is not None:
        return str(section.path)
    if section.href:
        return section.href
    return None


def _section_plan(section: SectionSnapshot) -> SectionPlan:
    return SectionPlan(
        path=str(section.path or section.href),
        title=section.title,
        page_hrefs=tuple(page.href for page in section.pages),
    )
