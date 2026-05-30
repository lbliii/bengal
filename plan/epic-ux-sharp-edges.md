# Epic: UX Sharp Edges — Make Failures Visible and Choices Obvious

**Status**: Active
**Created**: 2026-04-13
**Updated**: 2026-05-30
**Target**: v0.4.0 (beta)
**Estimated Effort**: 24-36 hours
**Dependencies**: None (all sprints ship independently against current main)
**Source**: Codebase audit of CLI, directives, incremental build, scaffolding, and template API
**Lifts**: J10 (Developer Experience/CLI) from 4.3 → 4.8, J4 (Custom Directives) from 4.2 → 4.5
**2026-05-28 Check**: Kept as the current user-visible polish bucket. Completed Agent DX and template overlay work moved to `plan/complete/`; do not duplicate those shipped fixes here.

---

## Why This Matters

Bengal's internal architecture is excellent — snapshot engine, lock hierarchy, provenance system — but the surfaces users actually touch have accumulated friction that makes the tool feel unreliable even when it's working correctly.

**Core problem**: Silent failures and unclear choices erode user trust.

### Consequences

1. **Unknown directives render as generic `<div>` with no warning** — typos in content (`{nots}` instead of `{note}`) produce wrong output silently; users only discover them by visual inspection
2. **Unknown directive options are silently dropped** — `:clase:` instead of `:class:` is ignored; 28 fields across 8 option classes have no unknown-key detection
3. **`bengal build` exposes 30 flags** with undocumented conflicts (`--dev` vs `--theme-dev` vs `--profile`; 9 overlapping output modes) — new users can't tell which flags matter
4. **37 command invocations return `None`** — no structured output for scripting or CI; `check --changed` with no changes returns `None` silently
5. **Incremental build falls back to full rebuild without info-level logging** when template dependencies are missing or fingerprinted assets change — users think incremental is broken
6. **Scaffolded sites have `baseurl: https://example.com`** hardcoded, no description field, and no build config — first build produces a site with placeholder URLs
7. **QUICKSTART.md links to `ARCHITECTURE.md`** (lines 268, 316) which doesn't exist; references `bengal template-dev` commands that were renamed to `bengal theme`
8. **`check` has 3 aliases** (`v`, `validate`, `lint`) — users think there are 4 different validation tools

### Evidence Table

| Source | Finding | Proposal Impact |
|--------|---------|-----------------|
| Directive renderer (directives.py:149-160) | Unknown directives render as generic div, no warning | FIXES (Sprint 1) |
| Directive options (options.py:64-106) | Unknown option keys silently dropped | FIXES (Sprint 1) |
| Build command (build.py:11-48) | 30 flags, 9 overlapping output modes | FIXES (Sprint 3) |
| CLI commands (milo_commands/*.py) | 37 return-None paths vs 54 return-dict | FIXES (Sprint 4) |
| Provenance filter (provenance_filter.py:374-376) | Template fallback to full rebuild, no info log | FIXES (Sprint 2) |
| Asset fingerprint (provenance_filter.py:775) | Asset change forces full rebuild, logged after-the-fact | FIXES (Sprint 2) |
| Scaffolding (new.py:75-81) | Hardcoded example.com, missing fields | FIXES (Sprint 5) |
| QUICKSTART.md (lines 268, 316, 301-304) | Dead links, outdated commands | FIXES (Sprint 5) |
| CLI registration (milo_app.py:70-76) | check/validate/lint/v all same command | MITIGATES (Sprint 3) |
| Template context (site_wrappers.py:64-83) | Missing keys return "" silently | UNRELATED (separate RFC) |

---

### Invariants

These must remain true throughout or we stop and reassess:

1. **Full test suite green**: All 4,000+ tests pass after every sprint merge — no regressions
2. **Build performance unchanged**: Full and incremental build times within 5% of current baseline on test-large (100+ pages)
3. **Backwards compatibility**: No existing bengal.toml, content file, or template breaks — all changes are additive (new warnings, new output fields, new defaults)

---

## Target Architecture

After this epic, Bengal follows the **loud-by-default** principle:

- **Directives**: Unknown names emit a warning in build output and render with a visible `<!-- bengal: unknown directive "X" -->` HTML comment. Unknown options emit a warning with suggestion (did-you-mean). Strict mode promotes these to errors.
- **Incremental builds**: Every fallback-to-full-rebuild decision is logged at INFO level with the reason. `bengal build --explain` shows a summary of what was rebuilt and why.
- **CLI flags**: Build command organized into flag groups (Core, Output, Performance, Debug). Conflicting flags validated at parse time with clear error messages.
- **Command output**: All commands return `dict` with at minimum `{"status": "ok"|"skipped"|"error", "message": "..."}`. JSON mode always produces valid output.
- **Scaffolding**: `bengal new site` produces a site that builds cleanly with zero edits. `baseurl` defaults to `""` (valid for local dev). Config includes commented examples for common settings.
- **Documentation**: All QUICKSTART.md links resolve. CLI command names match current reality.

---

## Sprint Structure

| Sprint | Focus | Effort | Risk | Ships Independently? |
|--------|-------|--------|------|---------------------|
| 0 | Design: warning taxonomy, output contract | 2-3h | Low | Yes (RFC only) |
| 1 | Directive warnings for unknown names/options | 4-6h | Low | Yes |
| 2 | Incremental build transparency logging | 3-5h | Low | Yes |
| 3 | Build flag grouping and conflict validation | 4-6h | Medium | Yes |
| 4 | Command return-value standardization | 4-6h | Low | Yes |
| 5 | Scaffolding and documentation fixes | 3-5h | Low | Yes |
| 6 | CLI responsiveness and Milo upstreaming | 4-8h | Medium | Yes |

---

## Sprint 0: Design — Warning Taxonomy and Output Contract

**Goal**: Establish the patterns all other sprints follow, so we don't invent 5 different approaches.

### Task 0.1 — Define warning severity levels

Decide how Bengal surfaces problems to users:

| Level | When | Example |
|-------|------|---------|
| INFO | Transparent decision | "Incremental: rebuilding 12 pages (template changed)" |
| WARNING | Likely mistake, build continues | "Unknown directive 'nots' — did you mean 'note'?" |
| ERROR (strict only) | Same as WARNING but halts in `--strict` | Same |

**Acceptance**: Written decision in this plan's changelog or a standalone RFC. No code.

### Task 0.2 — Define command output contract

All commands must return:

```python
{"status": "ok" | "skipped" | "error", "message": str, **command_specific_fields}
```

**Acceptance**: Type definition written (can be a TypedDict or Protocol). No code changes yet.

### Task 0.3 — Audit flag conflicts in build command

List every pair of flags that interact or conflict. Document the resolution rule for each.

**Acceptance**: Table of flag interactions added to this plan.

---

## Sprint 1: Directive Warnings for Unknown Names and Options

**Goal**: Make directive typos visible so users find them during build, not during visual inspection.

### Task 1.1 — Warn on unknown directive names

**Files**: `bengal/parsing/backends/patitas/renderers/directives.py` (around line 149)

When a directive name isn't in the registry:
- Emit WARNING via build logger: `Unknown directive "{name}" in {file}:{line}`
- Include fuzzy-match suggestion if edit distance ≤ 2 from a registered directive
- Render an HTML comment `<!-- bengal: unknown directive "{name}" -->` before the generic div
- In `--strict` mode, promote to error

**Acceptance**:
- `bengal build` on a file with `{nots}` shows warning in console output
- `bengal build --strict` on same file exits non-zero
- `rg 'unknown directive' bengal/parsing/` returns the new warning code
- New test in `tests/unit/rendering/` verifies warning emission

### Task 1.2 — Warn on unknown directive option keys

**Files**: `bengal/parsing/backends/patitas/directives/options.py` (around line 64)

When `from_raw()` encounters a key not in the dataclass fields:
- Emit WARNING: `Unknown option "clase" for directive "note" — did you mean "class"?`
- Fuzzy-match against known field names
- In `--strict` mode, promote to error

**Acceptance**:
- `bengal build` on a file with `:clase:` option shows warning
- Unknown options still silently dropped (warning only, no behavior change)
- New test verifies warning for each option class

---

## Sprint 2: Incremental Build Transparency

**Goal**: When incremental builds fall back to full rebuild, tell the user why.

### Task 2.1 — Log template-dependency fallback

**Files**: `bengal/orchestration/build/provenance_filter.py` (around line 374-376)

When `cache.template_dependencies` is empty and we force full rebuild:
- Log at INFO: `"Incremental: full rebuild required — template dependency data not yet cached (first build after cache clear)"`

**Acceptance**:
- `bengal build --verbose` after `bengal clean --cache` shows the info message
- Second `bengal build --verbose` does NOT show it (dependencies now cached)

### Task 2.2 — Log asset-fingerprint cascade

**Files**: `bengal/orchestration/build/provenance_filter.py` (around line 775)

When fingerprinted asset changes force all-page rebuild:
- Log at INFO: `"Incremental: rebuilding all pages — fingerprinted asset changed: {asset_name}"`
- Log BEFORE setting `incremental=False`, not after

**Acceptance**:
- Change a CSS file, run `bengal build --verbose`, see the asset name in the log
- Log appears before "Building N pages" message

### Task 2.3 — Log cascade-source resolution failures

**Files**: `bengal/build/provenance/filter.py` (around line 486-491)

When a cascade source file can't be found:
- Upgrade from silent `pass` to WARNING: `"Cascade source missing: {path} — descendant pages may not rebuild correctly"`

**Acceptance**:
- Delete an `_index.md`, run incremental build, see warning in output
- New test verifies warning emission

### Task 2.4 — Enhance `--explain` output

Add a summary section to `--explain` output showing:
- Pages rebuilt vs skipped (count + percentage)
- Reason breakdown: content changed (N), template changed (N), cascade changed (N), asset cascade (N)

**Acceptance**:
- `bengal build --explain` shows rebuild reason summary
- JSON variant (`--explain-json`) includes same data

---

## Sprint 3: Build Flag Grouping and Conflict Validation

**Goal**: Make the build command's 30 flags navigable and catch conflicts at parse time.

### Task 3.1 — Validate mutually exclusive flag combinations

**Files**: `bengal/cli/milo_commands/build.py` (top of function body)

Add validation at the start of `build()`:
- `--memory-optimized` + `--perf-profile` → error (already exists at line 97-99, keep)
- `--verbose` + `--quiet` → error: "Cannot use --verbose and --quiet together"
- `--explain` + `--explain-json` → resolve: `--explain-json` wins (superset)
- `--dev` + `--profile` → error: "--dev is shorthand for --profile dev; use one or the other"
- `--theme-dev` + `--profile` → error: same pattern

**Acceptance**:
- `bengal build --verbose --quiet` shows clear error message and exits non-zero
- `bengal build --dev --profile writer` shows clear error message
- New parametrized test covers each conflict pair

### Task 3.2 — Document flag groups in help text

Group flags with section headers in the help output (if milo-cli supports it) or add a preamble comment:

```
Core:     --source, --config, --environment, --profile
Speed:    --incremental/--no-incremental, --no-parallel, --fast, --memory-optimized
Output:   --verbose, --quiet, --full-output, --explain, --explain-json
Debug:    --debug, --traceback, --perf-profile, --profile-templates, --log-file
Advanced: --assets-pipeline, --build-version, --all-versions, --clean-output, --dry-run, --validate
```

**Acceptance**:
- `bengal build --help` output has visual grouping
- Groups match the table above (adjustable during implementation)

### Task 3.3 — Reduce alias confusion for check command

**Files**: `bengal/cli/milo_app.py` (around line 70-76)

Keep `check` as canonical, keep `v` as short alias, remove `validate` and `lint` aliases. Add deprecation warning if users invoke via old names (if milo-cli supports alias deprecation, otherwise just remove).

**Acceptance**:
- `bengal check` works
- `bengal v` works
- `bengal validate` either shows deprecation warning or is removed
- `bengal lint` either shows deprecation warning or is removed

---

## Sprint 4: Command Return-Value Standardization

**Goal**: All CLI commands return structured data so JSON mode and CI pipelines always get useful output.

### Task 4.1 — Define CommandResult type

**Files**: `bengal/cli/utils/` (new or existing types module)

```python
class CommandResult(TypedDict):
    status: Literal["ok", "skipped", "error"]
    message: str
```

Commands can extend with additional fields.

**Acceptance**:
- Type exists and is importable
- No runtime behavior change yet

### Task 4.2 — Retrofit top-priority commands

Fix the highest-impact `return None` paths:
- `serve` → return `{"status": "ok", "message": "Server started", "host": ..., "port": ...}`
- `clean` → return `{"status": "ok", "message": "Cleaned output directory", "removed": [...]}`
- `check --changed` with no changes → return `{"status": "skipped", "message": "No changed files found"}`
- `fix --dry-run` → return `{"status": "ok", "message": "Dry run complete", "fixes_available": N}`

**Acceptance**:
- `bengal clean --force 2>&1 | python -m json.tool` produces valid JSON (if JSON output mode active)
- `bengal check --changed` with no changes returns status "skipped" in JSON mode
- Each retrofitted command has a test verifying the return dict

### Task 4.3 — Retrofit remaining commands

Fix `i18n`, `content`, remaining `fix` paths, and any other `return None` commands.

**Acceptance**:
- `rg 'return None' bengal/cli/milo_commands/` returns zero hits (or only for `serve` blocking loop)

---

## Sprint 5: Scaffolding and Documentation Fixes

**Goal**: First-run experience produces a working site and documentation matches reality.

### Task 5.1 — Fix scaffolded site config

**Files**: `bengal/cli/milo_commands/new.py`, scaffold templates

- Change `baseurl` from `https://example.com` to `""` (valid for local dev)
- Add `description` field with placeholder: `"A new Bengal site"`
- Add commented examples for common settings (build.incremental, features.search, etc.)

**Acceptance**:
- `bengal new site test-site && cd test-site && bengal build` succeeds with zero warnings
- Generated `site.yaml` has no `example.com` reference
- Generated config has commented examples

### Task 5.2 — Fix QUICKSTART.md dead links

**Files**: `QUICKSTART.md`

- Line 268, 316: Remove references to `ARCHITECTURE.md` (doesn't exist) or create it
- Lines 301-304: Replace `bengal template-dev` with `bengal theme`
- Verify all other command references match current CLI

**Acceptance**:
- `rg 'ARCHITECTURE.md' QUICKSTART.md` returns zero hits (or file exists)
- `rg 'template-dev' QUICKSTART.md` returns zero hits
- All `bengal` commands mentioned in QUICKSTART.md are valid

### Task 5.3 — Clarify --theme vs --template in new site

**Files**: `bengal/cli/milo_commands/new.py`

Update descriptions:
- `--theme` → `"Visual theme (colors, layout): default, ..."`
- `--template` → `"Site structure (directories, starter content): default, blog, docs, ..."`

**Acceptance**:
- `bengal new site --help` clearly distinguishes the two flags

---

## Sprint 6: CLI Responsiveness and Milo Upstreaming

**Status**: In progress
**Started**: 2026-05-30
**Goal**: Make common CLI interactions feel instant while preserving Bengal's
Milo command contract and identifying framework fixes that should move
upstream.

### Evidence

Initial profiling on 2026-05-30 showed three Bengal-visible costs:

| Path | Finding | Owner |
|------|---------|-------|
| `bengal --help`, `bengal new`, `bengal --version` | Bengal called `build_parser()`, which resolved every lazy command schema before rendering metadata output. | Bengal mitigation now, Milo long-term |
| Branded help and unknown-command output | Kida help/error rendering imported and compiled the output template stack for cheap metadata paths. | Bengal |
| Ordinary command execution | Milo's parser construction resolved all registered lazy commands before running one selected command. | Bengal mitigation now, Milo long-term |

### Bengal-Owned Work

| Task | Status | Proof |
|------|--------|-------|
| Registry-only root/group/leaf help for cheap paths | Done | `tests/unit/cli/test_milo_parser_construction.py::test_fast_cli_metadata_paths_do_not_build_full_parser` |
| Fast `--version` without parser construction | Done | `tests/integration/test_cli_help.py::test_cli_version_runs` |
| Selected-command parser that resolves only the invoked command schema | Done | `tests/unit/cli/test_milo_parser_construction.py::test_selected_command_execution_does_not_build_full_parser` and published CLI smoke |
| Root option parity guard between fast path and Milo parser | Done | `tests/unit/cli/test_milo_parser_construction.py::test_fast_root_help_options_match_milo_parser` |
| Keep full-tree modes on Milo full registry | Done | `--llms-txt`, completions, and MCP still route through `super().run()` |
| Changelog fragment | Done | `changelog.d/cli-help-startup.fixed.md` |

### Upstream Milo CLI Candidates

These should move to Milo so Bengal can delete its local selected-parser bridge:

1. **Shallow root/group help**: root and group help should render from registered
   command metadata without resolving leaf schemas.
2. **Selected-command parser construction**: execution should parse global
   options and command path first, then resolve only the selected lazy command's
   schema.
3. **Lazy command schema contract**: expose a first-class way to precompute or
   persist command schemas so `tools/list`, completions, and parser generation
   can stay lazy by default.
4. **Public root option metadata API**: expose root built-in options as data so
   custom renderers do not need to duplicate them.
5. **Renderer separation**: help/error formatting should allow a text-only fast
   path and a richer renderer without forcing template-engine imports for
   metadata commands.

### Not Now

- Do not optimize `bengal cache hash` by narrowing input globs in this sprint.
  The slow path is mostly real cache-key work reading configured inputs,
  including autodoc sources; changing it risks cache invalidation semantics.
- Do not replace `bengal.__version__`'s package-metadata source in this sprint.
  That touches release metadata assumptions and should be a separate
  release-risk review if startup still needs more reduction after Milo fixes.
- Do not remove the full parser conflict test. It remains the installed-wheel
  drift guard for the v0.3.1 failure mode.

### Acceptance

- `bengal --version`, root help, group help, and leaf help do not call
  `build_parser()`.
- Running a selected command does not call `build_parser()` unless it uses a
  full-tree built-in mode.
- Published CLI smoke coverage passes.
- Timing proof records before/after measurements, but no flaky timing assertion
  is added to the fast suite.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Directive warnings break existing sites that use custom directive names | Medium | High | Sprint 1: warnings only (not errors) by default; strict mode opt-in |
| Flag validation rejects currently-working flag combos | Low | High | Sprint 3: audit real-world usage in tests before adding validation |
| Return-value changes break existing CLI consumers | Low | Medium | Sprint 4: additive only — commands that returned None now return dict; no existing field removed |
| milo-cli doesn't support flag grouping in help | Medium | Low | Sprint 3: fall back to docstring-level grouping if framework doesn't support it |
| Incremental logging adds overhead | Low | Low | Sprint 2: all logging is conditional on level; no computation unless DEBUG/INFO enabled |
| Local selected parser drifts from Milo built-in root options | Low | Medium | Sprint 6: parity test compares fast-path options to `build_parser()` |
| Local selected parser drifts from Milo execution semantics | Medium | Medium | Sprint 6: published CLI smoke tests cover advertised command execution |

---

## Success Metrics

| Metric | Current | After Sprint 2 | After Sprint 5 | After Sprint 6 |
|--------|---------|-----------------|-----------------|----------------|
| Silent failure points (unknown directive + options + return None) | 37+ None returns + 0 directive warnings | 37 None returns + directive warnings active | 0 None returns + directive warnings active | Unchanged |
| Build flag conflicts caught at parse time | 1 (memory + perf) | 1 | 5+ validated pairs | Unchanged |
| Incremental fallback decisions logged at INFO | 0 | 3+ (template, asset, cascade) | 3+ | Unchanged |
| Scaffolded site builds with zero warnings | No | No | Yes | Unchanged |
| Dead documentation links | 4+ (ARCHITECTURE.md x2, template-dev x2) | 4+ | 0 | Unchanged |
| CLI metadata/help paths avoid full parser construction | No | No | No | Yes |
| Selected command execution avoids full parser construction | No | No | No | Yes |
| J10 (Developer Experience/CLI) maturity score | 4.3 | 4.5 | 4.8 | 4.8 |

---

## Relationship to Existing Work

- **ROADMAP.md** — This epic is not on the current roadmap's top 10 but lifts J10 (Developer Experience/CLI) from 4.3 to 4.8 and J4 (Custom Directives) from 4.2 to 4.5. Can be interleaved with Epic 5 (Theme Ecosystem) since both improve user-facing surfaces.
- **epic-immutable-page-pipeline.md** — No dependency; this epic doesn't touch page internals.
- **rfc-cli-upgrade-notifications.md** — Sprint 3 flag work should be coordinated with any CLI changes from upgrade notifications.
- **plan-production-maturity.md** — This epic contributes to the "all journeys at 5.0" goal.

---

## Changelog

- 2026-04-13: Initial draft from codebase audit
- 2026-05-30: Added Sprint 6 for CLI responsiveness, local Bengal mitigations,
  and Milo upstream candidates.
