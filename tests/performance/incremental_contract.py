"""Reusable loader for incremental correctness contract cases."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "tests" / "performance" / "incremental_contract.toml"


@dataclass(frozen=True, slots=True)
class IncrementalContractCase:
    """One warm-build correctness case from the canonical contract."""

    id: str
    change: str
    expected: str
    proof_paths: tuple[str, ...]
    state_surfaces: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IncrementalContract:
    """Parsed incremental correctness contract."""

    version: int
    updated: str
    owner: str
    description: str
    invariants: dict[str, str]
    cases: tuple[IncrementalContractCase, ...]

    def case(self, case_id: str) -> IncrementalContractCase:
        """Return one contract case by id."""
        for case in self.cases:
            if case.id == case_id:
                return case
        raise KeyError(case_id)


def _as_case(payload: dict[str, Any]) -> IncrementalContractCase:
    return IncrementalContractCase(
        id=payload["id"],
        change=payload["change"],
        expected=payload["expected"],
        proof_paths=tuple(payload["proof_paths"]),
        state_surfaces=tuple(payload["state_surfaces"]),
    )


def load_incremental_contract(path: Path = CONTRACT_PATH) -> IncrementalContract:
    """Load the canonical incremental correctness contract."""
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    return IncrementalContract(
        version=payload["version"],
        updated=str(payload["updated"]),
        owner=payload["owner"],
        description=payload["description"],
        invariants=dict(payload["invariants"]),
        cases=tuple(_as_case(case) for case in payload["cases"]),
    )
