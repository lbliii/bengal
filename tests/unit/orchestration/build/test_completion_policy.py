"""Tests for build completion policy plumbing."""

from __future__ import annotations

from pathlib import Path

from bengal.orchestration.build.inputs import BuildInput
from bengal.orchestration.build.options import BuildCompletionPolicy, BuildOptions
from bengal.server.build_executor import BuildRequest, BuildResult
from bengal.utils.stats_minimal import MinimalStats


def test_build_options_default_to_complete() -> None:
    options = BuildOptions()

    assert options.completion_policy is BuildCompletionPolicy.COMPLETE


def test_build_input_round_trips_completion_policy() -> None:
    options = BuildOptions(completion_policy=BuildCompletionPolicy.SERVE_READY, quiet=True)
    build_input = BuildInput.from_options(options, Path("/site"))

    request = build_input.to_build_request()
    restored = BuildInput.from_build_request(request)

    assert request.completion_policy == "serve_ready"
    assert request.quiet is True
    assert restored.options.completion_policy is BuildCompletionPolicy.SERVE_READY
    assert restored.options.quiet is True


def test_unknown_serialized_completion_policy_falls_back_to_complete() -> None:
    request = BuildRequest(site_root="/site", completion_policy="unknown")

    restored = BuildInput.from_build_request(request)

    assert restored.options.completion_policy is BuildCompletionPolicy.COMPLETE


def test_minimal_stats_preserves_build_result_completion_policy() -> None:
    result = BuildResult(
        success=True,
        pages_built=3,
        build_time_ms=100.0,
        completion_policy="serve_ready",
    )

    stats = MinimalStats.from_build_result(result)

    assert stats.completion_policy == "serve_ready"


def test_build_input_records_no_change_census() -> None:
    build_input = BuildInput.from_options(BuildOptions(incremental=True), Path("/site"))

    assert build_input.change_census.no_changes is True
    assert build_input.change_census.single_edit is False
    assert build_input.change_census.to_dict()["changed_count"] == 0


def test_build_input_records_single_content_edit_census() -> None:
    changed = frozenset({Path("/site/content/docs/page.md")})
    build_input = BuildInput.from_options(
        BuildOptions(incremental=True),
        Path("/site"),
        changed_sources=changed,
    )

    assert build_input.change_census.no_changes is False
    assert build_input.change_census.single_edit is True
    assert build_input.change_census.content_changed_count == 1
    assert build_input.change_census.non_content_changed_count == 0
    assert build_input.change_census.single_changed_path == Path("/site/content/docs/page.md")


def test_build_input_rejects_nav_or_structural_change_as_single_edit() -> None:
    changed = frozenset({Path("/site/content/docs/page.md")})

    nav_input = BuildInput.from_options(
        BuildOptions(incremental=True),
        Path("/site"),
        changed_sources=changed,
        nav_changed_sources=changed,
    )
    structural_input = BuildInput.from_options(
        BuildOptions(incremental=True),
        Path("/site"),
        changed_sources=changed,
        structural_changed=True,
    )

    assert nav_input.change_census.single_edit is False
    assert structural_input.change_census.single_edit is False
