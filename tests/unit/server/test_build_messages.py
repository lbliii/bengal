"""
Tests for ``send_build_error_payload`` and ``send_build_ok_payload``
in :mod:`bengal.server.live_reload.notification` (Sprint A3.2).

Pins the SSE wire contract for the two overlay-control messages:

- ``build_error`` — pushes the A0.2 envelope as the next SSE ``data:`` chunk
  so the browser-side overlay client can render an error UI in place.
- ``build_ok`` — pushes the dismiss signal so the overlay tears itself down
  after a successful rebuild.

The notifier's only job is wire concerns: JSON-encode the payload, increment
the SSE generation counter, and signal waiters. The transport schema itself
is owned by ``bengal/errors/overlay/transport.py`` (tested separately).
"""

from __future__ import annotations

import json

import pytest

from bengal.server import live_reload
from bengal.server.live_reload import reset_for_testing
from bengal.server.live_reload.notification import (
    send_build_error_payload,
    send_build_ok_payload,
)


@pytest.fixture(autouse=True)
def _reset_sse_state() -> None:
    """Reset the SSE singleton between tests to keep generations comparable."""
    reset_for_testing()
    yield
    reset_for_testing()


@pytest.fixture(autouse=True)
def _enable_reload_events(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force events on regardless of the developer's local env."""
    monkeypatch.delenv("BENGAL_DISABLE_RELOAD_EVENTS", raising=False)


class TestSendBuildErrorPayload:
    def test_stores_payload_as_json_in_last_action(self) -> None:
        payload = {
            "type": "build_error",
            "schema_version": 1,
            "timestamp": "2026-04-17T15:34:12Z",
            "errors": [{"code": "R004", "message": "boom"}],
        }
        send_build_error_payload(payload)

        decoded = json.loads(live_reload._last_action)
        assert decoded == payload

    def test_increments_generation(self) -> None:
        before = live_reload._reload_generation
        send_build_error_payload({"type": "build_error", "errors": []})
        assert live_reload._reload_generation == before + 1

    def test_two_sends_two_increments(self) -> None:
        before = live_reload._reload_generation
        send_build_error_payload({"type": "build_error", "errors": []})
        send_build_error_payload({"type": "build_error", "errors": []})
        assert live_reload._reload_generation == before + 2

    def test_does_not_send_when_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BENGAL_DISABLE_RELOAD_EVENTS", "1")
        before_gen = live_reload._reload_generation
        before_action = live_reload._last_action
        send_build_error_payload({"type": "build_error", "errors": []})
        assert live_reload._reload_generation == before_gen
        assert live_reload._last_action == before_action

    def test_handles_unserializable_payload_gracefully(self) -> None:
        before_gen = live_reload._reload_generation
        # `set` is not JSON-serializable; the notifier should swallow the
        # error and leave SSE state untouched rather than propagating.
        send_build_error_payload({"type": "build_error", "errors": {1, 2, 3}})
        assert live_reload._reload_generation == before_gen


class TestSendBuildOkPayload:
    def test_stores_payload_as_json_in_last_action(self) -> None:
        payload = {
            "type": "build_ok",
            "schema_version": 1,
            "timestamp": "2026-04-17T15:34:45Z",
            "build_ms": 142,
        }
        send_build_ok_payload(payload)

        decoded = json.loads(live_reload._last_action)
        assert decoded == payload

    def test_increments_generation(self) -> None:
        before = live_reload._reload_generation
        send_build_ok_payload({"type": "build_ok"})
        assert live_reload._reload_generation == before + 1

    def test_does_not_send_when_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BENGAL_DISABLE_RELOAD_EVENTS", "1")
        before_gen = live_reload._reload_generation
        before_action = live_reload._last_action
        send_build_ok_payload({"type": "build_ok"})
        assert live_reload._reload_generation == before_gen
        assert live_reload._last_action == before_action

    def test_handles_unserializable_payload_gracefully(self) -> None:
        before_gen = live_reload._reload_generation
        send_build_ok_payload({"build_ms": object()})
        assert live_reload._reload_generation == before_gen


class TestExportedFromPackage:
    def test_send_build_error_payload_re_exported(self) -> None:
        from bengal.server.live_reload import send_build_error_payload as exported

        assert exported is send_build_error_payload

    def test_send_build_ok_payload_re_exported(self) -> None:
        from bengal.server.live_reload import send_build_ok_payload as exported

        assert exported is send_build_ok_payload


class TestBuildTriggerOverlayBranching:
    """Pin the build → overlay routing logic in BuildTrigger.

    Three transitions matter:

    1. errored build → push ``build_error``, suppress regular reload
    2. clean build after errored build → push ``build_ok``, suppress regular reload
    3. clean build after clean build → no overlay traffic; regular reload runs

    These tests poke ``_handle_overlay_messages`` directly because the
    full ``trigger_build`` path needs a real Site and the orchestration
    pipeline; the contract we care about is the branching, not the
    plumbing.
    """

    def _make_trigger(self):
        from pathlib import Path
        from unittest.mock import MagicMock

        from bengal.server.build_trigger import BuildTrigger

        site = MagicMock()
        site.root_path = Path("/test/site")
        site.output_dir = Path("/test/site/public")
        return BuildTrigger(site=site, executor=MagicMock())

    def _make_template_error(self):
        from pathlib import Path

        from bengal.errors import ErrorCode
        from bengal.rendering.errors import (
            TemplateErrorContext,
            TemplateRenderError,
        )

        return TemplateRenderError(
            error_type="filter",
            message="No filter named 'bogus'",
            template_context=TemplateErrorContext(
                template_name="x.html",
                line_number=1,
                column=1,
                source_line="{{ x | bogus }}",
                surrounding_lines=[(1, "{{ x | bogus }}")],
                template_path=Path("/x.html"),
            ),
            code=ErrorCode.R004,
        )

    def test_errored_build_pushes_build_error_and_suppresses_reload(self) -> None:
        trigger = self._make_trigger()
        err = self._make_template_error()

        result = trigger._handle_overlay_messages([err], build_duration=0.05)

        assert result is True
        assert trigger._had_template_errors_last_build is True
        decoded = json.loads(live_reload._last_action)
        assert decoded["type"] == "build_error"
        assert len(decoded["errors"]) == 1
        assert decoded["errors"][0]["code"] == "R004"

    def test_clean_after_error_pushes_build_ok_and_suppresses_reload(self) -> None:
        trigger = self._make_trigger()
        # Simulate previous errored state.
        trigger._had_template_errors_last_build = True

        result = trigger._handle_overlay_messages([], build_duration=0.142)

        assert result is True
        assert trigger._had_template_errors_last_build is False
        decoded = json.loads(live_reload._last_action)
        assert decoded["type"] == "build_ok"
        assert decoded["build_ms"] == 142

    def test_clean_after_clean_returns_false_and_no_overlay_send(self) -> None:
        trigger = self._make_trigger()
        before_action = live_reload._last_action

        result = trigger._handle_overlay_messages([], build_duration=0.05)

        assert result is False
        assert trigger._had_template_errors_last_build is False
        # No overlay traffic — _last_action unchanged from the autouse
        # reset_for_testing fixture's reset value.
        assert live_reload._last_action == before_action

    def test_repeated_errored_builds_keep_pushing_build_error(self) -> None:
        trigger = self._make_trigger()
        err = self._make_template_error()

        trigger._handle_overlay_messages([err], build_duration=0.01)
        gen_after_first = live_reload._reload_generation

        trigger._handle_overlay_messages([err], build_duration=0.01)

        assert live_reload._reload_generation == gen_after_first + 1
        assert trigger._had_template_errors_last_build is True
