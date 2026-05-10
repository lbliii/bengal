"""Tests for plugin registry contract validation."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from bengal.plugins.registry import PluginRegistry


def test_freeze_returns_immutable_snapshot() -> None:
    registry = PluginRegistry()
    registry.add_template_filter("shout", lambda value: str(value).upper())

    frozen = registry.freeze()

    assert frozen.template_filters[0][0] == "shout"
    with pytest.raises(FrozenInstanceError):
        frozen.template_filters = ()
    with pytest.raises(RuntimeError, match="Cannot modify"):
        registry.add_template_filter("quiet", lambda value: value)


def test_template_function_validates_phase() -> None:
    registry = PluginRegistry()

    with pytest.raises(ValueError, match="phase must be an integer from 1 to 9"):
        registry.add_template_function("helper", lambda: None, phase=0)


def test_template_filter_requires_callable() -> None:
    registry = PluginRegistry()

    with pytest.raises(TypeError, match="must be callable"):
        registry.add_template_filter("broken", "not-callable")  # type: ignore[arg-type]


def test_extension_names_must_be_non_empty() -> None:
    registry = PluginRegistry()

    with pytest.raises(ValueError, match="non-empty string"):
        registry.add_shortcode("", "<span />")


def test_content_source_must_be_class() -> None:
    registry = PluginRegistry()

    with pytest.raises(TypeError, match="must be a class"):
        registry.add_content_source("remote", object())  # type: ignore[arg-type]
