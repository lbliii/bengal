"""Schema checks for the incremental correctness contract."""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import pytest

from tests.performance.incremental_contract import (
    CONTRACT_PATH,
    IncrementalContract,
    load_incremental_contract,
)

ROOT = Path(__file__).resolve().parents[3]

REQUIRED_CASES = {
    "no-op",
    "single-content-edit",
    "template-edit",
    "asset-edit",
    "sidecar-edit",
    "config-edit",
}
REQUIRED_CASE_FIELDS = {
    "id",
    "change",
    "expected",
    "proof_paths",
    "state_surfaces",
}


@pytest.fixture(scope="module")
def incremental_contract() -> IncrementalContract:
    return load_incremental_contract(CONTRACT_PATH)


def test_incremental_contract_covers_required_cases(incremental_contract) -> None:
    case_ids = {case.id for case in incremental_contract.cases}

    assert incremental_contract.version >= 1
    assert REQUIRED_CASES.issubset(case_ids)


def test_incremental_contract_cases_have_proof_and_state_surfaces(
    incremental_contract,
) -> None:
    raw_cases = load_incremental_contract(CONTRACT_PATH).cases

    for case in raw_cases:
        assert not REQUIRED_CASE_FIELDS.difference(field.name for field in fields(case))
        assert case.proof_paths, f"{case.id} needs proof paths"
        assert case.state_surfaces, f"{case.id} needs state surfaces"
        for proof_path in case.proof_paths:
            assert (ROOT / proof_path).exists(), (
                f"{case.id} references missing proof path: {proof_path}"
            )


def test_incremental_contract_case_lookup_uses_canonical_fixture(
    incremental_contract,
) -> None:
    case = incremental_contract.case("template-edit")

    assert "template" in case.change.lower()
    assert "provenance" in case.state_surfaces

    with pytest.raises(KeyError):
        incremental_contract.case("missing")
