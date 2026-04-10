# Epic: ty Diagnostic Reduction — From 2,654 to 1,913

**Status**: Complete (PR #208)
**Created**: 2026-04-10
**Completed**: 2026-04-10
**Result**: 2,654 → 1,913 diagnostics (28% reduction, 741 eliminated)
**PR**: #208

---

## Outcome

This epic reduced ty diagnostics from 2,654 to 1,913 across 5 sprints in a single
day. The remaining ~1,913 diagnostics are nearly all ty checker limitations that
cannot be fixed without upstream improvements to ty itself.

### What Worked

| Technique | Diagnostics Eliminated | Notes |
|-----------|----------------------|-------|
| `list[PageLike]` → `Sequence[PageLike]` for input params | ~200 | Covariance fix — real type correctness improvement |
| `Config \| dict[str, Any]` → `Any` for config params | ~50 | TypedDict covariance — honest about actual acceptance |
| PageLike protocol expansion (plain_text, kind, etc.) | ~300 | Made implicit contracts explicit |
| `BuildStatsLike` protocol addition | ~20 | Missing abstraction |
| ASTNode test type narrowing | ~100 | Added assert guards before subscript access |
| Misc return type / signature fixes | ~70 | Various genuine type corrections |

### What Didn't Work

| Technique | Result | Lesson |
|-----------|--------|--------|
| SiteLike protocol expansion | +204 diagnostics (reverted) | Test mocks don't implement new attrs — always verify downstream |
| Sequence conversions in orchestration | 0 reduction | ty can't structurally match Page to PageLike regardless of container variance |
| `Iterator[T]` → `Generator[T, None, None]` for @contextmanager | Net zero | ty doesn't understand @contextmanager decorator — swaps one diagnostic category for another |

### Remaining Diagnostics (1,913) — The Floor

| Category | Count | Root Cause | Fixable? |
|----------|-------|------------|----------|
| `invalid-argument-type` | 852 | Page doesn't structurally match PageLike in generic/inference contexts | No — ty limitation |
| `unresolved-attribute` | 507 | hasattr() doesn't narrow types | No — ty limitation |
| `invalid-assignment` | 298 | List invariance on dataclass fields, read-only protocol attrs | Partially — but remaining cases are ty limitation |
| `invalid-return-type` | 44 | ParamSpec decorators, @contextmanager inference | No — ty limitation |
| `not-subscriptable` | 35 | Protocol objects in tests | No — ty limitation |
| `unresolved-import` | 29 | Optional deps (typer, lunr, babel, etc.) | No — deps not installed |
| `call-non-callable` | 29 | hasattr narrowing fallout | No — ty limitation |
| `invalid-type-arguments` | 11 | DirectiveOptions structural matching | No — ty limitation |
| `invalid-method-override` | 10 | Liskov violations in CLI widgets | Could fix but low value |
| Other | 98 | Various | Mixed |

### Key Decision: Do Not Promote Rules to Error

The original plan (Sprint 5) called for promoting `invalid-argument-type`, `unresolved-attribute`, and `invalid-assignment` from `warn` to `error`. **This is not viable** — the remaining diagnostics are ty false positives, not real type bugs. Promoting would require widespread `# ty: ignore` suppression, which is worse than `warn`.

**Recommendation**: Wait for ty to mature (structural protocol matching, hasattr narrowing, @contextmanager inference), then re-evaluate promotion.

---

## Sprint History

| Sprint | Focus | Before | After | Key Changes |
|--------|-------|--------|-------|-------------|
| 0 | Triage & classify all diagnostics | 2,654 | 2,654 | Created diagnostic inventory, updated stale pyproject.toml comments |
| 1 | Hot functions — PageLike protocol, list invariance, ASTNode tests | 2,654 | 2,023 | Expanded PageLike, Sequence covariance, test type narrowing |
| 2 | rendering module | 2,023 | 2,023 | Context manager return types, i18n callable widening |
| 3 | core + orchestration + config | 2,023 | 1,977 | Config param widening (dict → Any), Generator return types |
| 4 | Remaining source modules (analysis, cache, postprocess) | 1,977 | 1,916 | Broad Sequence covariance, LogLevel return type, site wrapper fixes |
| 5 | Final squeeze + pyproject.toml | 1,916 | 1,913 | Autodoc config widening, more Sequence conversions, linkcheck bug fix |

---

## Relationship to Other Plans

| Plan | Status | Relationship |
|------|--------|-------------|
| `rfc-ty-type-checker-adoption.md` | Implemented | Prerequisite — ty adopted, this was "Phase 2: Fix Type Errors" |
| `rfc-ty-type-hardening.md` | Superseded by this epic | Earlier draft at ~540 errors; this epic covers the full 2,654 → 1,913 journey |
| `plan-protocol-driven-typing.md` | Partially completed by this epic | Phase 1 (protocol extensions) done; Phase 2 (migration) partially done; Phases 3-7 remain but low ROI given ty limitations |
| `rfc-protocol-driven-typing.md` | Partially completed by this epic | Same as above |
| `sprint-0-ty-triage.md` | Complete | Diagnostic inventory used throughout this epic |
| `investigation-ruff-format-except-parenthesis.md` | Complete | Documented PEP 758 syntax behavior discovered during this epic |
| `epic-stale-code-refresh.md` | Complete (predecessor) | Reduced diagnostics from 837 → 715; this epic continued from 2,654 |

---

## Changelog

- 2026-04-10: Draft created from fresh `uv run ty check` analysis (2,654 diagnostics)
- 2026-04-10: Sprints 0-5 completed. Final count: 1,913. Status → Complete.
