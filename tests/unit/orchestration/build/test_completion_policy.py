"""Tests for build completion policy plumbing."""

from __future__ import annotations

from pathlib import Path

from bengal.orchestration.build.inputs import BuildInput
from bengal.orchestration.build.options import BuildCompletionPolicy, BuildOptions
from bengal.server.build_executor import BuildRequest


def test_build_options_default_to_complete() -> None:
    options = BuildOptions()

    assert options.completion_policy is BuildCompletionPolicy.COMPLETE


def test_build_input_round_trips_completion_policy() -> None:
    options = BuildOptions(completion_policy=BuildCompletionPolicy.SERVE_READY)
    build_input = BuildInput.from_options(options, Path("/site"))

    request = build_input.to_build_request()
    restored = BuildInput.from_build_request(request)

    assert request.completion_policy == "serve_ready"
    assert restored.options.completion_policy is BuildCompletionPolicy.SERVE_READY


def test_unknown_serialized_completion_policy_falls_back_to_complete() -> None:
    request = BuildRequest(site_root="/site", completion_policy="unknown")

    restored = BuildInput.from_build_request(request)

    assert restored.options.completion_policy is BuildCompletionPolicy.COMPLETE
