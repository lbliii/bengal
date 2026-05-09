"""Tests for search backend configuration contracts."""

from __future__ import annotations

import pytest

from bengal.errors import BengalConfigError
from bengal.postprocess.search_backends import (
    LunrSearchBackend,
    resolve_search_backend_config,
)


def test_search_backend_defaults_to_lunr() -> None:
    config = resolve_search_backend_config({})

    assert config.enabled is True
    assert config.backend == "lunr"
    assert config.prebuilt_enabled is True


def test_search_false_disables_backend_artifacts() -> None:
    config = resolve_search_backend_config(False)

    assert config.enabled is False
    assert LunrSearchBackend(object(), config).generate([], lambda _label, factory: factory()) == []


def test_lunr_prebuilt_uses_existing_legacy_config() -> None:
    config = resolve_search_backend_config({"backend": "lunr", "lunr": {"prebuilt": False}})

    assert config.backend == "lunr"
    assert config.prebuilt_enabled is False


def test_unknown_search_backend_is_a_config_error() -> None:
    with pytest.raises(BengalConfigError, match="Unsupported search backend"):
        resolve_search_backend_config({"backend": "remote"})


def test_invalid_lunr_config_is_a_config_error() -> None:
    with pytest.raises(BengalConfigError, match=r"Invalid search\.lunr configuration"):
        resolve_search_backend_config({"backend": "lunr", "lunr": True})
