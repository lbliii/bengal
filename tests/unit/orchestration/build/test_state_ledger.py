"""Tests for the build-state ledger contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.orchestration.build.state_ledger import BUILD_STATE_LEDGER, get_state_surface

ROOT = Path(__file__).resolve().parents[4]
REQUIRED_SURFACES = {
    "change-census",
    "provenance",
    "page-artifacts",
    "output-collector",
    "template-fingerprints",
    "render-context-cache",
}


def test_build_state_ledger_names_required_surfaces() -> None:
    surface_ids = {surface.id for surface in BUILD_STATE_LEDGER}

    assert REQUIRED_SURFACES.issubset(surface_ids)
    assert len(surface_ids) == len(BUILD_STATE_LEDGER)


def test_build_state_ledger_proofs_exist() -> None:
    for surface in BUILD_STATE_LEDGER:
        assert surface.owner.startswith("bengal.")
        assert surface.storage
        assert surface.write_phase
        assert surface.read_phase
        assert surface.incremental_role
        assert surface.proof
        for proof_path in surface.proof:
            assert (ROOT / proof_path).exists(), (
                f"{surface.id} references missing proof path: {proof_path}"
            )


def test_get_state_surface_returns_by_id() -> None:
    surface = get_state_surface("provenance")

    assert surface.owner == "bengal.build.provenance"


def test_get_state_surface_rejects_unknown_id() -> None:
    with pytest.raises(KeyError):
        get_state_surface("unknown")
