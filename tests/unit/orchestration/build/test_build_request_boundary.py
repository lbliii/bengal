"""BuildRequest lives in orchestration and is re-exported by server."""

from __future__ import annotations

import pickle

from bengal.orchestration.build.requests import BuildRequest
from bengal.server.build_executor import BuildRequest as ServerBuildRequest


def test_build_request_is_owned_by_orchestration() -> None:
    request = BuildRequest(site_root="/site", changed_paths=("content/page.md",))

    assert request.site_root == "/site"
    assert request.changed_paths == ("content/page.md",)
    assert request.incremental is True


def test_server_build_request_reexport_preserves_compatibility() -> None:
    assert ServerBuildRequest is BuildRequest


def test_build_request_stays_picklable() -> None:
    request = BuildRequest(site_root="/site", completion_policy="serve_ready")

    restored = pickle.loads(pickle.dumps(request))

    assert restored == request
