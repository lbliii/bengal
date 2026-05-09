"""Tests for version lifecycle status compatibility."""

from __future__ import annotations

import pytest

from bengal.core.version import Version, VersionConfig


def test_deprecated_bool_derives_deprecated_status() -> None:
    version = Version(id="v1", deprecated=True)

    assert version.status == "deprecated"
    assert version.deprecated is True
    assert version.to_dict()["status"] == "deprecated"
    assert version.to_dict()["deprecated"] is True


def test_explicit_status_wins_over_deprecated_alias() -> None:
    version = Version(id="v1", status="legacy", deprecated=True)

    assert version.status == "legacy"
    assert version.deprecated is False


def test_eol_status_remains_template_deprecated() -> None:
    version = Version(id="v1", status="eol")

    assert version.status == "eol"
    assert version.deprecated is True
    assert version.to_dict()["status"] == "eol"
    assert version.to_dict()["deprecated"] is True


def test_from_config_accepts_status_and_deprecated_alias() -> None:
    config = VersionConfig.from_config(
        {
            "versioning": {
                "enabled": True,
                "versions": [
                    {"id": "v3", "latest": True, "status": "current"},
                    {"id": "v2", "status": "preview"},
                    {"id": "v1", "deprecated": True},
                ],
            }
        }
    )

    assert [version.status for version in config.versions] == [
        "current",
        "preview",
        "deprecated",
    ]
    assert [version.deprecated for version in config.versions] == [False, False, True]


def test_string_versions_keep_latest_current_and_older_legacy() -> None:
    config = VersionConfig.from_config({"versioning": {"enabled": True, "versions": ["v3", "v2"]}})

    assert [version.status for version in config.versions] == ["current", "legacy"]


def test_first_version_inferred_as_current_when_latest_omitted() -> None:
    config = VersionConfig(enabled=True, versions=[Version(id="v1")])

    assert config.versions[0].latest is True
    assert config.versions[0].status == "current"


def test_invalid_status_says_what_to_use() -> None:
    with pytest.raises(
        ValueError, match="Expected one of: current, deprecated, eol, legacy, preview"
    ):
        VersionConfig.from_config(
            {
                "versioning": {
                    "enabled": True,
                    "versions": [{"id": "v1", "status": "unsupported"}],
                }
            }
        )
