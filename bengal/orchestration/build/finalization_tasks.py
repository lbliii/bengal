"""Finalization task contracts for build completion policies."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from bengal.orchestration.build.options import BuildCompletionPolicy


class FinalizationTaskTier(StrEnum):
    """Product tier produced by a finalization task."""

    SERVE_READY = "serve_ready"
    ARTIFACTS = "artifacts"
    QUALITY = "quality"
    PERSISTENCE = "persistence"


class FinalizationFailurePolicy(StrEnum):
    """How a task failure affects the build."""

    FAIL_BUILD = "fail_build"
    WARN = "warn"


@dataclass(frozen=True, slots=True)
class FinalizationTaskSpec:
    """Contract for a post-render build task."""

    name: str
    tier: FinalizationTaskTier
    blocks_complete: bool
    blocks_serve_ready: bool
    failure_policy: FinalizationFailurePolicy
    outputs: tuple[str, ...] = ()

    def blocks(self, policy: BuildCompletionPolicy) -> bool:
        """Return whether this task blocks the requested completion policy."""
        if policy is BuildCompletionPolicy.SERVE_READY:
            return self.blocks_serve_ready
        return self.blocks_complete


def default_finalization_task_specs() -> tuple[FinalizationTaskSpec, ...]:
    """Return Bengal's built-in post-render task contracts."""
    return (
        FinalizationTaskSpec(
            name="special_pages",
            tier=FinalizationTaskTier.SERVE_READY,
            blocks_complete=True,
            blocks_serve_ready=True,
            failure_policy=FinalizationFailurePolicy.FAIL_BUILD,
            outputs=("404.html",),
        ),
        FinalizationTaskSpec(
            name="output_formats",
            tier=FinalizationTaskTier.ARTIFACTS,
            blocks_complete=True,
            blocks_serve_ready=False,
            failure_policy=FinalizationFailurePolicy.WARN,
            outputs=("index.json", "llms.txt", "llm-full.txt"),
        ),
        FinalizationTaskSpec(
            name="sitemap",
            tier=FinalizationTaskTier.ARTIFACTS,
            blocks_complete=True,
            blocks_serve_ready=False,
            failure_policy=FinalizationFailurePolicy.WARN,
            outputs=("sitemap.xml",),
        ),
        FinalizationTaskSpec(
            name="robots",
            tier=FinalizationTaskTier.ARTIFACTS,
            blocks_complete=True,
            blocks_serve_ready=False,
            failure_policy=FinalizationFailurePolicy.WARN,
            outputs=("robots.txt",),
        ),
        FinalizationTaskSpec(
            name="feeds",
            tier=FinalizationTaskTier.ARTIFACTS,
            blocks_complete=True,
            blocks_serve_ready=False,
            failure_policy=FinalizationFailurePolicy.WARN,
            outputs=("rss.xml", "atom.xml"),
        ),
        FinalizationTaskSpec(
            name="redirects",
            tier=FinalizationTaskTier.ARTIFACTS,
            blocks_complete=True,
            blocks_serve_ready=False,
            failure_policy=FinalizationFailurePolicy.WARN,
        ),
        FinalizationTaskSpec(
            name="xref",
            tier=FinalizationTaskTier.ARTIFACTS,
            blocks_complete=True,
            blocks_serve_ready=False,
            failure_policy=FinalizationFailurePolicy.WARN,
            outputs=("xref.json",),
        ),
        FinalizationTaskSpec(
            name="asset_audit",
            tier=FinalizationTaskTier.QUALITY,
            blocks_complete=True,
            blocks_serve_ready=False,
            failure_policy=FinalizationFailurePolicy.WARN,
        ),
        FinalizationTaskSpec(
            name="health",
            tier=FinalizationTaskTier.QUALITY,
            blocks_complete=True,
            blocks_serve_ready=False,
            failure_policy=FinalizationFailurePolicy.WARN,
        ),
        FinalizationTaskSpec(
            name="cache_save",
            tier=FinalizationTaskTier.PERSISTENCE,
            blocks_complete=True,
            blocks_serve_ready=False,
            failure_policy=FinalizationFailurePolicy.WARN,
        ),
        FinalizationTaskSpec(
            name="stats",
            tier=FinalizationTaskTier.PERSISTENCE,
            blocks_complete=True,
            blocks_serve_ready=True,
            failure_policy=FinalizationFailurePolicy.FAIL_BUILD,
        ),
    )


def blocking_finalization_task_names(policy: BuildCompletionPolicy) -> tuple[str, ...]:
    """Return task names that block the requested policy."""
    return tuple(spec.name for spec in default_finalization_task_specs() if spec.blocks(policy))
