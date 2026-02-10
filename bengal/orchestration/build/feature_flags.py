"""Build-time feature flags and runtime policy selection."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_flag(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class BuildFeatureFlags:
    """Resolved feature flag set for a single build."""

    use_kida_block_hashes: bool
    use_patitas_recursive_diff: bool
    use_timing_hints: bool
    lean_cold_build: bool


def resolve_build_feature_flags(*, incremental: bool) -> BuildFeatureFlags:
    """Resolve feature flags with a cold-vs-incremental runtime policy."""
    # Keep cold builds lean by default (lower scheduler/cache orchestration overhead),
    # while preserving richer diff/scheduling in incremental mode.
    lean_cold_build = _env_flag("BENGAL_LEAN_COLD_BUILD", default=True)
    is_cold_mode = lean_cold_build and not incremental

    return BuildFeatureFlags(
        use_kida_block_hashes=_env_flag("BENGAL_USE_KIDA_BLOCK_HASHES", default=True),
        use_patitas_recursive_diff=_env_flag("BENGAL_USE_PATITAS_RECURSIVE_DIFF", default=True),
        use_timing_hints=_env_flag("BENGAL_USE_PIPELINE_TIMING_HINTS", default=not is_cold_mode),
        lean_cold_build=lean_cold_build,
    )
