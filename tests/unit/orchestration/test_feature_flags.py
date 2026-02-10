"""Tests for build runtime feature flag policy."""

from bengal.orchestration.build.feature_flags import resolve_build_feature_flags


def test_resolve_build_feature_flags_defaults_for_cold_build(monkeypatch):
    monkeypatch.delenv("BENGAL_LEAN_COLD_BUILD", raising=False)
    monkeypatch.delenv("BENGAL_USE_PIPELINE_TIMING_HINTS", raising=False)

    flags = resolve_build_feature_flags(incremental=False)
    assert flags.lean_cold_build is True
    assert flags.use_timing_hints is False


def test_resolve_build_feature_flags_defaults_for_incremental(monkeypatch):
    monkeypatch.delenv("BENGAL_LEAN_COLD_BUILD", raising=False)
    monkeypatch.delenv("BENGAL_USE_PIPELINE_TIMING_HINTS", raising=False)

    flags = resolve_build_feature_flags(incremental=True)
    assert flags.use_timing_hints is True


def test_resolve_build_feature_flags_env_override(monkeypatch):
    monkeypatch.setenv("BENGAL_USE_PIPELINE_TIMING_HINTS", "1")
    flags = resolve_build_feature_flags(incremental=False)
    assert flags.use_timing_hints is True


def test_merkle_advisory_defaults_enabled(monkeypatch):
    monkeypatch.delenv("BENGAL_USE_MERKLE_ADVISORY", raising=False)
    flags = resolve_build_feature_flags(incremental=True)
    assert flags.use_merkle_advisory is True


def test_merkle_advisory_env_disable(monkeypatch):
    monkeypatch.setenv("BENGAL_USE_MERKLE_ADVISORY", "0")
    flags = resolve_build_feature_flags(incremental=True)
    assert flags.use_merkle_advisory is False


def test_merkle_enforcement_defaults_disabled(monkeypatch):
    monkeypatch.delenv("BENGAL_USE_MERKLE_ENFORCEMENT", raising=False)
    flags = resolve_build_feature_flags(incremental=True)
    assert flags.use_merkle_enforcement is False


def test_merkle_enforcement_env_enable(monkeypatch):
    monkeypatch.setenv("BENGAL_USE_MERKLE_ENFORCEMENT", "1")
    flags = resolve_build_feature_flags(incremental=True)
    assert flags.use_merkle_enforcement is True
