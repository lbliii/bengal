"""Canonical ledger of durable build-state surfaces.

The ledger is intentionally declarative. It gives build, cache, and benchmark
work a shared vocabulary for the state files and in-memory summaries that decide
whether a warm build can skip work.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BuildStateSurface:
    """Describe one durable or reported build-state surface."""

    id: str
    owner: str
    storage: str
    write_phase: str
    read_phase: str
    incremental_role: str
    proof: tuple[str, ...]
    participates_in_warm_build: bool = True


BUILD_STATE_LEDGER: tuple[BuildStateSurface, ...] = (
    BuildStateSurface(
        id="change-census",
        owner="bengal.orchestration.build.inputs",
        storage="BuildInput.change_census / BuildStats.change_census",
        write_phase="pre-discovery",
        read_phase="build planning and reporting",
        incremental_role="Explains whether the build started from no changes, targeted changes, or structural changes.",
        proof=("tests/unit/orchestration/build/test_completion_policy.py",),
    ),
    BuildStateSurface(
        id="provenance",
        owner="bengal.build.provenance",
        storage=".bengal/provenance/index.json, records/, subvenance.json, dependency-index.json",
        write_phase="post-render",
        read_phase="incremental filtering",
        incremental_role="Maps output pages to source, dependency, and config inputs for rebuild decisions.",
        proof=(
            "tests/unit/build/provenance/test_store.py",
            "tests/unit/build/provenance/test_filter.py",
            "tests/unit/orchestration/build/test_provenance_batch.py",
            "tests/unit/orchestration/build/test_provenance_dependency_index.py",
        ),
    ),
    BuildStateSurface(
        id="page-artifacts",
        owner="bengal.cache.page_artifact_store",
        storage=".bengal/cache/page_artifacts/manifest.json plus shard files",
        write_phase="post-render",
        read_phase="incremental warm start",
        incremental_role="Restores rendered-page artifact metadata without scanning every shard on targeted loads.",
        proof=(
            "tests/unit/cache/test_page_artifact_store.py",
            "tests/unit/orchestration/incremental/test_page_artifact_cache.py",
        ),
    ),
    BuildStateSurface(
        id="output-collector",
        owner="bengal.orchestration.build_context",
        storage="BuildContext output collection and artifact inventory",
        write_phase="render and postprocess",
        read_phase="post-render finalization and metrics",
        incremental_role="Records which artifacts were written, skipped, or need downstream inventory.",
        proof=(
            "tests/unit/rendering/test_write_output_rendered_page.py",
            "tests/performance/test_post_render_pipeline_budget.py",
        ),
    ),
    BuildStateSurface(
        id="template-fingerprints",
        owner="bengal.orchestration.incremental.cache_manager",
        storage=".bengal/cache template fingerprint payload",
        write_phase="cache refresh",
        read_phase="incremental filtering",
        incremental_role="Detects active project/theme template changes and inherited theme changes.",
        proof=(
            "tests/unit/rendering/test_template_inheritance_detection.py",
            "tests/unit/orchestration/build/test_provenance_filter_path_keys.py",
        ),
    ),
    BuildStateSurface(
        id="render-context-cache",
        owner="bengal.orchestration.build_context",
        storage="per-build in-memory BuildContext caches",
        write_phase="render",
        read_phase="render",
        incremental_role="Scopes expensive render-context wrappers to one build and prevents cross-site leakage.",
        proof=(
            "tests/unit/rendering/test_engine_globals.py",
            "tests/unit/rendering/test_thread_safety.py",
        ),
        participates_in_warm_build=False,
    ),
)


def get_state_surface(surface_id: str) -> BuildStateSurface:
    """Return a build-state surface by id."""
    for surface in BUILD_STATE_LEDGER:
        if surface.id == surface_id:
            return surface
    raise KeyError(surface_id)


def warm_build_surfaces() -> tuple[BuildStateSurface, ...]:
    """Return surfaces that participate in warm-build correctness."""
    return tuple(surface for surface in BUILD_STATE_LEDGER if surface.participates_in_warm_build)


def state_surfaces_by_owner(owner: str) -> tuple[BuildStateSurface, ...]:
    """Return surfaces owned by a module or package prefix."""
    owner_prefix = f"{owner}."
    return tuple(
        surface
        for surface in BUILD_STATE_LEDGER
        if surface.owner == owner or surface.owner.startswith(owner_prefix)
    )


def proof_paths_for_surface(surface_id: str) -> tuple[str, ...]:
    """Return proof paths attached to one surface."""
    return get_state_surface(surface_id).proof


__all__ = [
    "BUILD_STATE_LEDGER",
    "BuildStateSurface",
    "get_state_surface",
    "proof_paths_for_surface",
    "state_surfaces_by_owner",
    "warm_build_surfaces",
]
