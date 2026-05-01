"""Tests for plugin discovery inspection and capability readiness."""

from __future__ import annotations

from bengal.plugins.inspection import (
    CAPABILITY_INTEGRATION_STATUS,
    capability_details,
    inspect_entry_point,
)


class FakeEntryPoint:
    """Minimal importlib.metadata.EntryPoint stand-in."""

    def __init__(self, name: str, value: str, loaded: object):
        self.name = name
        self.value = value
        self._loaded = loaded

    def load(self) -> object:
        if isinstance(self._loaded, BaseException):
            raise self._loaded
        return self._loaded


class TemplatePlugin:
    name = "template-plugin"
    version = "1.0.0"

    def register(self, registry):
        registry.add_template_filter("shout", lambda value: str(value).upper())
        registry.on_phase("pre_render", lambda site, context: None)


class DirectivePlugin:
    name = "directive-plugin"
    version = "1.0.0"

    def register(self, registry):
        registry.add_directive(object())


class ExplodingPlugin:
    def __init__(self):
        msg = "boom"
        raise RuntimeError(msg)

    def register(self, registry):
        raise AssertionError("unreachable")


def test_template_and_phase_plugin_reports_ready_capabilities() -> None:
    report = inspect_entry_point(
        FakeEntryPoint("template", "example:TemplatePlugin", TemplatePlugin)
    )

    assert report.status == "ready"
    assert report.ready is True
    assert report.capabilities["template_filters"] == 1
    assert report.capabilities["phase_hooks"] == 1
    assert report.pending_capabilities == ()


def test_pending_capability_reports_partial_status() -> None:
    report = inspect_entry_point(
        FakeEntryPoint("directive", "example:DirectivePlugin", DirectivePlugin)
    )

    assert report.status == "partial"
    assert report.ready is False
    assert report.capabilities["directives"] == 1
    assert report.pending_capabilities == ("directives",)


def test_load_error_is_reported_without_raising() -> None:
    report = inspect_entry_point(FakeEntryPoint("broken", "example:Missing", RuntimeError("nope")))

    assert report.status == "load_error"
    assert report.has_load_error is True
    assert report.errors == ("RuntimeError: nope",)


def test_invalid_plugin_is_not_reported_as_load_error() -> None:
    report = inspect_entry_point(FakeEntryPoint("invalid", "example:Invalid", object()))

    assert report.status == "invalid"
    assert report.has_load_error is False


def test_instantiation_error_is_reported_without_raising() -> None:
    report = inspect_entry_point(
        FakeEntryPoint("exploding", "example:ExplodingPlugin", ExplodingPlugin)
    )

    assert report.status == "load_error"
    assert report.has_load_error is True
    assert report.errors == ("RuntimeError: boom",)


def test_capability_details_mark_pending_integrations() -> None:
    details = capability_details({"directives": 1, "template_filters": 1})
    by_name = {item["name"]: item for item in details}

    assert CAPABILITY_INTEGRATION_STATUS["directives"] == "pending"
    assert by_name["directives"]["ready"] is False
    assert by_name["template_filters"]["ready"] is True
