# Epic: Sharp Edges Remediation — Make Bengal Powerful, Ergonomic, Intuitive, and Reliable

**Status**: Draft
**Created**: 2026-04-13
**Target**: v0.4.0
**Estimated Effort**: 35-50 hours
**Dependencies**: Parallel-safe with epic-test-coverage-remediation (Sprint 5 here overlaps with Sprint 4 there on CLI tests)
**Source**: Full-codebase sharp-edges audit (2026-04-13)

---

## Why This Matters

Bengal aims to be the documentation generator you trust without thinking. An audit of the CLI, effects system, caching layer, and build orchestration found **12 sharp edges** spanning correctness, reliability, and ergonomics. The scariest are silent: incremental builds that miss dependency changes produce stale HTML, and the user's only recourse is `bengal clean && bengal build` — which they don't know to run until they notice the output is wrong.

### Consequences

1. **Stale incremental output** — `Effect.from_dict` uses a fragile `/` heuristic to distinguish paths from template names, silently misclassifying entries like `partials/sidebar.html`. `for_page_render` accepts `None` for `cascade_sources` and `data_files`, so parent `_index.md` and `data/*.yaml` changes may not trigger rebuilds.
2. **Raw tracebacks from the dev server** — `bengal serve` has no top-level error handler around `site.serve()`. Any unexpected exception during the always-on command shows a Python traceback instead of a friendly message.
3. **24 `return None` sites across CLI commands** — Commands inconsistently return `None` vs structured dicts, breaking `--json` output and making success/failure ambiguous for scripts.
4. **30 flags on `bengal build`** with 5 overlapping output-mode flags (`--quiet`, `--verbose`, `--fast`, `--full-output`, `--dashboard`) whose interactions are undocumented and unvalidated.
5. **7 silent `except OSError: pass` handlers** in production code paths — missing translations, skipped upgrade checks, and lost provenance data with no user feedback.
6. **Provenance recovery samples only 10 pages** — sites with 100+ pages can have stale provenance entries for pages 11-100, producing wrong output after recovery.

### Evidence Table

| Layer | Finding | Proposal Impact |
|-------|---------|-----------------|
| Effects | `from_dict` path-vs-string heuristic misclassifies template names with `/` | FIXES (Sprint 1) |
| Effects | `for_page_render` accepts `None` cascade_sources/data_files, losing deps | FIXES (Sprint 1) |
| Provenance | Recovery samples only 10 pages, misses stale entries | FIXES (Sprint 1) |
| CLI/serve | No try-except around `site.serve()` | FIXES (Sprint 2) |
| CLI | 24 `return None` across 10 command files | FIXES (Sprint 2) |
| CLI/build | 5 overlapping output-mode flags, undocumented interactions | FIXES (Sprint 3) |
| CLI | 6/16 commands have `--dry-run`, 10 don't — inconsistent | MITIGATES (Sprint 3) |
| CLI | Tri-state flags (`--incremental/--no-incremental`) have hidden auto-detect default | FIXES (Sprint 3) |
| Cache | `site_root` set AFTER `BuildCache.load()` — race window for wrong cache keys | FIXES (Sprint 1) |
| Cache | Corrupted `.tmp` tracer file → empty tracer → all pages appear unchanged | FIXES (Sprint 1) |
| Error handling | 7 silent `except OSError: pass` in production code | FIXES (Sprint 4) |
| Testing | 5 CLI test files for 16 command groups (0.17 test ratio) | DEFERRED to epic-test-coverage-remediation |

---

### Invariants

These must remain true throughout or we stop and reassess:

1. **Incremental correctness**: `bengal build` (incremental) must produce byte-identical output to `bengal clean && bengal build` for any content/config change. Validated by golden-file comparison in CI.
2. **No raw tracebacks in default mode**: Every CLI command must route unhandled exceptions through `handle_exception()`. Validated by `rg 'Traceback \(most recent' tests/integration/` returning zero hits in CLI smoke tests.
3. **All commands return structured dicts**: No CLI command in `bengal/cli/milo_commands/` returns `None`. Validated by `rg 'return None' bengal/cli/milo_commands/` returning zero hits.

---

## Target Architecture

### Effects: Type-safe dependency tracking
```python
# Before: fragile string heuristic
depends_on=frozenset(
    Path(d) if "/" in d or "\\" in d else d  # "partials/sidebar.html" → Path (WRONG)
)

# After: explicit type tag in serialization
depends_on=frozenset(
    Path(d["path"]) if d["type"] == "path" else d["name"]
    for d in data.get("depends_on", [])
)
```

### CLI: Consistent return contracts
```python
# Before: some return None, some return dict
def serve(...) -> dict:
    site.serve(...)
    return None  # Breaks --json, ambiguous

# After: all commands return structured result
def serve(...) -> dict:
    site.serve(...)
    return {"status": "stopped", "message": "Server shut down"}
```

### CLI: Validated output modes
```
--quiet       → minimal (errors + summary)
--verbose     → detailed per-file output
--fast        → implies --quiet (documented)
--full-output → traditional non-interactive (mutually exclusive with --dashboard)
--dashboard   → TUI (mutually exclusive with --full-output, --quiet, --verbose)
```
All conflicts validated upfront with clear error messages.

---

## Sprint Structure

| Sprint | Focus | Effort | Risk | Ships Independently? |
|--------|-------|--------|------|---------------------|
| 0 | Design: dependency serialization format, CLI return contract | 4h | Low | Yes (RFC only) |
| 1 | Fix incremental correctness: effects, provenance, cache init | 10-14h | High | Yes |
| 2 | CLI error handling: serve wrapper, return contracts | 8-10h | Medium | Yes |
| 3 | CLI ergonomics: flag validation, output modes, help text | 8-12h | Low | Yes |
| 4 | Silent failure remediation: replace `pass` with logging/warnings | 4-6h | Low | Yes |

---

## Sprint 0: Design & Validate

**Goal**: Solve the hard serialization and contract problems on paper before touching code.

### Task 0.1 — Design Effect dependency serialization format

The current `to_dict`/`from_dict` round-trip loses type information (Path vs string). Design a tagged format that preserves types without breaking existing cache files.

**Constraints**: Must be backward-compatible (old caches degrade gracefully to full rebuild, not crash). Must handle cross-platform path separators.

**Acceptance**: Design doc in `plan/` with before/after examples, migration strategy, and backward-compat behavior.

### Task 0.2 — Define CLI return contract

Survey all 16 commands' return values. Define a standard return shape: `{"status": "ok"|"error"|"skipped", "message": str, ...command-specific keys}`. Decide what `serve` and `dashboard` (long-running) commands return on exit.

**Acceptance**: Table of all 16 commands with current return type and proposed return type.

### Task 0.3 — Map output-mode flag interactions

Document all valid combinations of `--quiet`, `--verbose`, `--fast`, `--full-output`, `--dashboard`. Define which combos are errors. Design validation function.

**Acceptance**: Truth table of all 32 flag combinations (5 binary flags) with expected behavior or error.

---

## Sprint 1: Incremental Correctness

**Goal**: Eliminate silent stale output from incremental builds. This is the highest-risk sprint because it touches the cache hot path.

### Task 1.1 — Fix Effect.from_dict serialization round-trip

Replace the `/`-heuristic in `bengal/effects/effect.py:102-104` with tagged serialization. Update `to_dict` to emit `{"type": "path", "path": str}` or `{"type": "template", "name": str}`. Update `from_dict` to consume both old (string) and new (dict) formats for backward compat.

**Files**: `bengal/effects/effect.py`
**Acceptance**: `python -c "from bengal.effects.effect import Effect; e = Effect.for_page_render(...); assert e == Effect.from_dict(e.to_dict())"` passes for template names containing `/`. Old cache files still load without error.

### Task 1.2 — Make cascade_sources and data_files required in for_page_render

Change `cascade_sources` and `data_files` from `None`-default optionals to required parameters (empty frozenset if none). Audit all call sites to pass explicit values.

**Files**: `bengal/effects/effect.py`, all callers of `for_page_render`
**Acceptance**: `rg 'for_page_render\(' bengal/ --type py` shows no calls missing cascade_sources or data_files. `rg 'cascade_sources: frozenset.*None' bengal/effects/effect.py` returns zero hits.

### Task 1.3 — Fix cache_manager initialization order

Move `self.cache.site_root = self.site.root_path` to before any cache access in `bengal/orchestration/incremental/cache_manager.py:128-129`. Either pass site_root to `BuildCache.load()` or set it immediately after.

**Files**: `bengal/orchestration/incremental/cache_manager.py`, `bengal/cache/build_cache/core.py`
**Acceptance**: `site_root` is set before `file_fingerprints` is accessed (verified by adding assertion in `_cache_key`). Full test suite passes.

### Task 1.4 — Harden EffectTracer.load against corruption

`bengal/effects/tracer.py:346-348` already handles `JSONDecodeError` by returning empty tracer, but this silently loses all build history. Add a warning log and write a `.corrupted` backup so users can report the issue.

**Files**: `bengal/effects/tracer.py`
**Acceptance**: Corrupted effects.json triggers warning log (not silent). `ls .bengal/state/effects.json.corrupted` exists after corruption.

### Task 1.5 — Fix provenance recovery sampling

Replace the 10-page sample in `bengal/orchestration/build/provenance_filter.py:593` with a full scan, or at minimum a statistically meaningful sample (sqrt(n) pages, randomly selected).

**Files**: `bengal/orchestration/build/provenance_filter.py`
**Acceptance**: Site with 100 pages where page 50 has stale provenance → page 50 is rebuilt. Test case in `tests/unit/orchestration/`.

---

## Sprint 2: CLI Error Handling & Return Contracts

**Goal**: No raw tracebacks; all commands return structured results.

### Task 2.1 — Wrap serve command in error handler

Add try/except around `site.serve()` in `bengal/cli/milo_commands/serve.py:96-103` using the existing `handle_exception()` pattern from build.

**Files**: `bengal/cli/milo_commands/serve.py`
**Acceptance**: `bengal serve` with a deliberately broken config shows a friendly error message, not a traceback. `rg 'site\.serve\(' bengal/cli/milo_commands/serve.py` shows the call is inside a try block.

### Task 2.2 — Standardize return values across all 16 commands

Replace all 24 `return None` sites with structured dict returns. Each command returns `{"status": "ok"|"error"|"skipped", "message": str}` at minimum.

**Files**: All files in `bengal/cli/milo_commands/`
**Acceptance**: `rg 'return None' bengal/cli/milo_commands/` returns zero hits. Each command's return type annotation is `-> dict`.

### Task 2.3 — Wrap dashboard launch paths in error handlers

Both `serve.py:84-94` and `build.py` dashboard paths lack error handling. Wrap both.

**Files**: `bengal/cli/milo_commands/serve.py`, `bengal/cli/milo_commands/build.py`
**Acceptance**: Dashboard crash shows friendly message, not traceback.

---

## Sprint 3: CLI Ergonomics

**Goal**: Reduce flag confusion; make the CLI predictable and self-documenting.

### Task 3.1 — Validate output-mode flag combinations on build

Add upfront validation (before site loading) for mutually exclusive output flags. Use the truth table from Sprint 0.

**Files**: `bengal/cli/milo_commands/build.py`
**Acceptance**: `bengal build --fast --full-output` prints a clear error and exits with code 2 before any site loading. `bengal build --dashboard --quiet` prints a clear error.

### Task 3.2 — Document tri-state flag defaults in help text

Update `--incremental` and `--assets-pipeline` descriptions to state the default behavior: "Default: auto-detect (enabled when cache exists)".

**Files**: `bengal/cli/milo_commands/build.py`
**Acceptance**: `bengal build --help` shows default behavior for tri-state flags.

### Task 3.3 — Improve help text for complex flags

Add one-sentence explanations for `--environment`, `--traceback`, `--explain` vs `--explain-json` vs `--dry-run`, and other flags with terse descriptions.

**Files**: `bengal/cli/milo_commands/build.py`, `bengal/cli/milo_commands/serve.py`
**Acceptance**: `bengal build --help` shows actionable descriptions (not just value lists).

### Task 3.4 — Document --fast implies --quiet

Make the `--fast` flag description explicit: "Fast mode: quiet output, max parallelism. Implies --quiet."

**Files**: `bengal/cli/milo_commands/build.py`
**Acceptance**: `bengal build --help | grep fast` shows "Implies --quiet".

---

## Sprint 4: Silent Failure Remediation

**Goal**: Replace silent exception swallowing with logged warnings so debugging is possible.

### Task 4.1 — Add logger.warning to OSError handlers in production code

Replace `except OSError: pass` with `except OSError: logger.debug("...", path=..., error=...)` in:
- `bengal/cli/milo_commands/i18n.py:93`
- `bengal/cli/helpers/upgrade_check.py:103`
- `bengal/orchestration/build/provenance_filter.py:164`
- `bengal/server/dev_server.py:1192`
- `bengal/server/reload_controller.py:362`

Keep `bengal/utils/io/file_lock.py:310` as-is (lock cleanup should be silent).

**Files**: 5 files listed above
**Acceptance**: `rg 'except OSError:\s*$' bengal/ --type py -A1 | rg '^\s*pass$'` returns only the file_lock.py hit (and any intentional cases with inline comments explaining why).

### Task 4.2 — Log warning on empty EffectTracer load

When `cache_manager.py` loads an EffectTracer with zero effects from an existing file, log a warning — this likely means corruption or a first-build-after-upgrade.

**Files**: `bengal/orchestration/incremental/cache_manager.py`
**Acceptance**: Empty tracer loaded from existing file triggers `logger.warning("effect_tracer_empty_after_load", ...)`.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Effect serialization change breaks existing caches | Medium | Medium | Sprint 1.1 handles old format gracefully; worst case is one full rebuild |
| Making cascade_sources required breaks callers we miss | Medium | High | Sprint 1.2 uses `rg` to audit all call sites; CI catches missing args |
| serve error handler catches too broadly, masks bugs | Low | Medium | Sprint 2.1 catches only Exception, re-raises KeyboardInterrupt/SystemExit |
| Return contract change breaks milo-cli integration | Low | High | Sprint 0.2 surveys milo's expectations before changing |
| Flag validation rejects valid user workflows | Low | Medium | Sprint 0.3 truth table reviewed before implementation |

---

## Success Metrics

| Metric | Current | After Sprint 1 | After Sprint 4 |
|--------|---------|-----------------|-----------------|
| `return None` in CLI commands | 24 | 24 | 0 |
| Silent `except OSError: pass` handlers | 7 | 7 | 1 (file_lock only) |
| Provenance recovery page sample | 10 (fixed) | sqrt(n) or full | sqrt(n) or full |
| Output-mode flag combos validated | 0 of 32 | 0 of 32 | all invalid combos rejected |
| Commands with error-wrapped main call | ~8 of 16 | ~8 of 16 | 16 of 16 |
| Effect round-trip fidelity | Lossy (path heuristic) | Lossless (tagged) | Lossless (tagged) |

---

## Relationship to Existing Work

- **epic-test-coverage-remediation** — parallel, complementary. That epic's Sprint 4 (CLI test coverage) validates this epic's Sprint 2-3 changes. Coordinate to avoid duplicating CLI test infrastructure.
- **Recent PRs #222-#224** — fixed stale CLI references and hardened error handling. This epic continues that trajectory with deeper structural fixes.

---

## Changelog

- 2026-04-13: Draft created from sharp-edges audit
