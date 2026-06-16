"""
Surgical warm-rebuild state mutation (persistent resident Site).

Design: ``plan/rfc-persistent-resident-site.md`` · Epic: #522.

The warm dev-loop today tears the Site down (`SiteRunner.prepare_for_rebuild`)
and rebuilds it from disk on every edit, so cost scales with total site size
rather than change size. The persistent-resident-Site model instead keeps the
built Site in memory and *surgically mutates only what changed*, with a
conservative fallback to the full teardown rebuild.

This module defines the contract that makes that safe:

* :class:`SurgicalRebuildPlan` — an ``IncrementalPlan``-shaped result describing
  what a surgical rebuild would touch, or *why it cannot* (``fallback_reasons``).
* :class:`SiteStateMutator` — given the resident Site + the changed paths, either
  mutates the resident state in place and returns an empty-fallback plan, or
  returns a plan with non-empty ``fallback_reasons`` so the caller does a full
  teardown rebuild instead.

**The contract (steward: "conservative fallback with reasons", "warm equals
cold"):** a caller MUST treat ``plan.is_fallback`` as "do the full teardown
rebuild". A surgical result is only valid when the mutator can *prove* it equals
a full rebuild; otherwise it names a reason and bails. Each change-type is
enabled only after a committed byte-parity test (see
``tests/integration/warm_build/surgical_parity.py``).

**Phase 0 (this commit):** the skeleton + contract only. ``apply()`` always
returns a fallback plan (no change-type is enabled yet), and this module is NOT
wired into the dev-server build path — so behavior is identical to today. Later
phases (frontmatter → data → template → … → structural, per the RFC) fill in
real in-place mutation behind per-change-type parity gates and wire the gate into
``bengal/server/build_trigger.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from bengal.build.contracts.dependency_index import DependencyReadIndex
    from bengal.protocols.core import SiteLike

logger = get_logger(__name__)

# Phase 0 sentinel: no surgical change-type is enabled yet, so every change
# falls back to the full teardown rebuild. Replaced per-type in later phases.
_PHASE0_FALLBACK = "surgical warm rebuild not enabled yet (RFC persistent-resident-site, phase 0)"


@dataclass(frozen=True, slots=True)
class SurgicalRebuildPlan:
    """Immutable result of attempting a surgical warm rebuild.

    Mirrors the ``IncrementalPlan`` shape from
    ``rfc-snapshot-build-plan-handoff.md``. When ``fallback_reasons`` is
    non-empty the surgical path declined to handle the change and the caller
    must perform a full teardown rebuild; the reasons are observable for
    diagnostics (steward: "conservative fallback with reasons").

    Attributes:
        changed_inputs: The source paths that triggered this rebuild.
        affected_pages: Page keys (content-relative source paths) whose output
            must be re-rendered. Empty on a pure fallback.
        affected_outputs: Output keys (site-relative output paths) that must be
            (re)written, including site-wide artifacts. Empty on a pure fallback.
        fallback_reasons: Non-empty iff the surgical path declined; each entry
            names *why* a full rebuild is required.
    """

    changed_inputs: tuple[Path, ...] = ()
    affected_pages: tuple[str, ...] = ()
    affected_outputs: tuple[str, ...] = ()
    fallback_reasons: tuple[str, ...] = ()

    @property
    def is_fallback(self) -> bool:
        """True when the caller must perform a full teardown rebuild."""
        return bool(self.fallback_reasons)

    @classmethod
    def fallback(cls, changed_inputs: Iterable[Path], reason: str) -> SurgicalRebuildPlan:
        """Build a plan that declines surgery for ``reason``."""
        return cls(changed_inputs=tuple(changed_inputs), fallback_reasons=(reason,))


@dataclass(slots=True)
class SiteStateMutator:
    """Surgically mutate a resident Site for a warm rebuild (or decline).

    Holds a reference to the resident ``site`` (mutated in place by later phases)
    and, when available, the ``dependency_index`` used to resolve which pages and
    outputs a changed input affects without scanning the whole site.

    Phase 0: :meth:`apply` always declines (returns a fallback plan). No resident
    state is mutated and the dev-server build path does not call this yet, so the
    warm build behaves exactly as before.
    """

    site: SiteLike
    dependency_index: DependencyReadIndex | None = None
    _enabled_change_types: frozenset[str] = field(default_factory=frozenset)

    def apply(self, changed_paths: Iterable[Path]) -> SurgicalRebuildPlan:
        """Attempt a surgical warm rebuild for ``changed_paths``.

        Returns a :class:`SurgicalRebuildPlan`. While ``plan.is_fallback`` is
        True the caller must run the full teardown rebuild
        (``site.prepare_for_rebuild()`` + ``site.build(incremental=True)``).

        Phase 0 always returns a fallback plan — the eligibility gate and
        in-place mutation land per change-type in later phases, each behind a
        byte-parity proof.
        """
        changed = tuple(changed_paths)
        # No change-type is enabled yet: decline conservatively.
        logger.debug(
            "surgical_rebuild_declined",
            reason=_PHASE0_FALLBACK,
            changed=[str(p) for p in changed],
        )
        return SurgicalRebuildPlan.fallback(changed, _PHASE0_FALLBACK)
