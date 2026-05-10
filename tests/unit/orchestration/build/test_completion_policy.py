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
