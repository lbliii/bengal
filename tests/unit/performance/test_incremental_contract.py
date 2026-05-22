"""Schema checks for the incremental correctness contract."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = ROOT / "tests" / "performance" / "incremental_contract.toml"

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


def _load_contract() -> dict:
    return tomllib.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_incremental_contract_covers_required_cases() -> None:
    contract = _load_contract()
    case_ids = {case["id"] for case in contract["cases"]}

    assert contract["version"] >= 1
    assert REQUIRED_CASES.issubset(case_ids)


def test_incremental_contract_cases_have_proof_and_state_surfaces() -> None:
    contract = _load_contract()

    for case in contract["cases"]:
        missing_fields = REQUIRED_CASE_FIELDS.difference(case)
        assert not missing_fields, f"{case.get('id', '<missing>')} missing {missing_fields}"
        assert case["proof_paths"], f"{case['id']} needs proof paths"
        assert case["state_surfaces"], f"{case['id']} needs state surfaces"
        for proof_path in case["proof_paths"]:
            assert (ROOT / proof_path).exists(), (
                f"{case['id']} references missing proof path: {proof_path}"
            )
