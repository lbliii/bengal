# Sprint 0: Sharp Edges Design — Solve Hard Problems on Paper

**Parent**: [epic-sharp-edges-remediation.md](epic-sharp-edges-remediation.md)
**Created**: 2026-04-13
**Status**: Draft

---

## Task 0.1: Effect Dependency Serialization Format

### Problem

`Effect.depends_on` holds a mixed `frozenset[Path | str]`. Serialization (`to_dict`) flattens both to plain strings. Deserialization (`from_dict`) uses a fragile heuristic to recover types:

```python
# effect.py:102-104
Path(d) if "/" in d or "\\" in d else d
```

This breaks for template names that contain `/` (e.g., `partials/nav.html`, `layouts/blog/post.html`) — they get silently converted to `Path` objects instead of staying as strings. The dependency graph loses template edges, so template changes don't trigger rebuilds.

### Current Behavior

```
to_dict: Path("content/page.md")  → "content/page.md"
to_dict: "partials/nav.html"      → "partials/nav.html"

from_dict: "content/page.md"      → Path("content/page.md")  ✓ (has /)
from_dict: "partials/nav.html"    → Path("partials/nav.html") ✗ (WRONG — is template name, not path)
from_dict: "base.html"            → "base.html"               ✓ (no /)
```

### Proposed Format: Tagged Serialization

```python
# to_dict (new)
"depends_on": [
    {"t": "p", "v": "content/page.md"},        # Path
    {"t": "s", "v": "partials/nav.html"},       # str (template name)
    {"t": "s", "v": "base.html"},               # str (template name)
]

# from_dict (new)
depends_on=frozenset(
    Path(d["v"]) if d["t"] == "p" else d["v"]
    for d in data.get("depends_on", [])
)
```

Short keys (`t`/`v`) minimize JSON size since effects files can contain thousands of entries.

### Backward Compatibility

Old cache files store `depends_on` as `["content/page.md", "base.html"]` (plain strings). The new `from_dict` must handle both:

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Effect:
    raw_deps = data.get("depends_on", [])
    deps: list[Path | str] = []
    for d in raw_deps:
        if isinstance(d, dict):
            # New tagged format
            deps.append(Path(d["v"]) if d["t"] == "p" else d["v"])
        else:
            # Legacy plain string — fall back to old heuristic
            # This is lossy but only for one build cycle; the next
            # save writes the new format.
            deps.append(Path(d) if "/" in d or "\\" in d else d)
    return cls(
        outputs=frozenset(Path(p) for p in data.get("outputs", [])),
        depends_on=frozenset(deps),
        invalidates=frozenset(data.get("invalidates", [])),
        operation=data.get("operation", ""),
        metadata=data.get("metadata", {}),
    )
```

**Migration path**: First build after upgrade uses legacy heuristic (same as today). After that build completes and saves, all subsequent loads use the tagged format. Worst case: one build cycle where a template change to `partials/nav.html` doesn't trigger rebuilds — identical to current behavior.

### Impact on `for_page_render` Parameters

While fixing serialization, also tighten the `for_page_render` API:

**Current** (effect.py:118-119):
```python
cascade_sources: frozenset[Path] | None = None,
data_files: frozenset[Path] | None = None,
```

**Proposed**:
```python
cascade_sources: frozenset[Path] = frozenset(),
data_files: frozenset[Path] = frozenset(),
```

This makes the caller explicitly pass empty frozensets instead of relying on `None`. The two production call sites already pass values:

1. `render_integration.py:165-166` — uses `frozenset_or_none()` which returns `frozenset | None`. Change to just `frozenset(self._context.cascade_sources)`.
2. `tracer.py:428-434` — doesn't pass these kwargs at all (uses defaults). This is the snapshot-based path; cascade/data info needs to be added to the snapshot or this path should pass empty frozensets explicitly.

**Test call sites** (11 in test files) — all pass without these kwargs, so they'll use the new `frozenset()` default. No test changes needed.

---

## Task 0.2: CLI Return Contract

### Current State

All 16 command files annotate `-> dict` but behavior varies:

| Pattern | Commands | Count |
|---------|----------|-------|
| Always returns dict | build, cache, check, clean, fix, inspect, new | 7 |
| Returns dict OR None | codemod, content, debug, i18n, theme, upgrade, version | 7 |
| Always returns None | serve | 1 |
| Not applicable (helper only) | config (5 sub-commands, all return dict) | 1 |

**24 `return None` statements** across 10 files violate the `-> dict` annotation.

### Proposed Standard Return Shape

```python
{
    "status": "ok" | "error" | "skipped",
    "message": str,  # Human-readable summary
    # ...command-specific keys
}
```

### Categories of `return None` and How to Fix

**Category A: Early exit when prerequisite missing (13 sites)**

Example: `content_sources` returns `None` when no sources configured.

```python
# Before (content.py:30)
return None

# After
return {"status": "skipped", "message": "No content sources configured"}
```

These are straightforward — replace `None` with a `"skipped"` dict.

**Files**: content.py (4), i18n.py (5), version.py (2), codemod.py (1), debug.py (1)

**Category B: Long-running commands that don't meaningfully "return" (4 sites)**

`serve.py` returns `None` because `site.serve()` blocks until Ctrl+C. The dashboard path also returns `None`.

```python
# After
return {"status": "ok", "message": "Server stopped"}
```

This is reachable when the server shuts down gracefully (Ctrl+C, port conflict, etc.).

**Files**: serve.py (2), theme.py:465,486 (asset watch mode — also long-running)

**Category C: Conditional paths that forgot to return (7 sites)**

`upgrade.py:55,58` returns `None` on user-cancelled upgrade. `debug.py:350` returns `None` from sandbox debug. `theme.py:339` returns `None` from theme test.

```python
# After (upgrade.py)
return {"status": "skipped", "message": "Upgrade cancelled"}
```

**Files**: upgrade.py (2), debug.py (1), theme.py (2), version.py (2)

### SystemExit Code Convention

Current usage is mostly consistent. Formalize it:

| Exit Code | Meaning | Current Usage |
|-----------|---------|---------------|
| 0 | Success | (implicit — no raise) |
| 1 | Runtime error (bad config, missing file, build failure) | ~30 sites, correct |
| 2 | Usage error (invalid flag combination) | build.py, serve.py, correct |

**One fix needed**: `check.py:312` passes a string to `SystemExit()`:
```python
raise SystemExit(f"Template validation failed: {len(errors)} error(s)")
```
This should be:
```python
cli.error(f"Template validation failed: {len(errors)} error(s)")
raise SystemExit(1)
```

---

## Task 0.3: Output-Mode Flag Interaction Truth Table

### The Five Flags

| Flag | Default | Effect |
|------|---------|--------|
| `--quiet` | `False` | Minimal output: errors + summary only |
| `--verbose` | `False` | Detailed per-file output |
| `--fast` | `False` | Implies `--quiet`, max parallelism |
| `--full-output` | `False` | Traditional non-interactive (no live progress) |
| `--dashboard` | `False` | Interactive Textual TUI |

### Current Validation

Only **one** combination is validated:
```python
if verbose and quiet:
    cli.error("--verbose and --quiet cannot be used together")
```

`--fast` silently sets `quiet = True` (line 93), which means `--fast --verbose` passes validation but then `verbose` is effectively ignored because the CLI output object is created with `quiet=True`.

### Truth Table (32 combinations)

Key: OK = valid, ERR = reject with message, IMP = implicit resolution

| quiet | verbose | fast | full_output | dashboard | Result | Behavior |
|-------|---------|------|-------------|-----------|--------|----------|
| 0 | 0 | 0 | 0 | 0 | **OK** | Default: live progress bar |
| 1 | 0 | 0 | 0 | 0 | **OK** | Quiet: errors + summary |
| 0 | 1 | 0 | 0 | 0 | **OK** | Verbose: per-file detail |
| 1 | 1 | 0 | 0 | 0 | **ERR** | "Cannot use --quiet with --verbose" |
| 0 | 0 | 1 | 0 | 0 | **OK** | Fast: quiet + max speed |
| 1 | 0 | 1 | 0 | 0 | **IMP** | Redundant (fast implies quiet), OK |
| 0 | 1 | 1 | 0 | 0 | **ERR** | "Cannot use --verbose with --fast (fast implies quiet)" |
| 1 | 1 | 1 | 0 | 0 | **ERR** | "Cannot use --verbose with --quiet" |
| 0 | 0 | 0 | 1 | 0 | **OK** | Full output: traditional non-interactive |
| 1 | 0 | 0 | 1 | 0 | **OK** | Quiet full output: errors + summary, non-interactive |
| 0 | 1 | 0 | 1 | 0 | **OK** | Verbose full output: per-file detail, non-interactive |
| 1 | 1 | 0 | 1 | 0 | **ERR** | "Cannot use --quiet with --verbose" |
| 0 | 0 | 1 | 1 | 0 | **OK** | Fast full output: quiet + non-interactive + max speed |
| 0 | 0 | 0 | 0 | 1 | **OK** | Dashboard: interactive TUI |
| 1 | 0 | 0 | 0 | 1 | **ERR** | "Cannot use --quiet with --dashboard" |
| 0 | 1 | 0 | 0 | 1 | **ERR** | "Cannot use --verbose with --dashboard" |
| 0 | 0 | 1 | 0 | 1 | **ERR** | "Cannot use --fast with --dashboard" |
| 0 | 0 | 0 | 1 | 1 | **ERR** | "Cannot use --full-output with --dashboard" |
| *(all other dashboard combos)* | | | | | **ERR** | Dashboard is mutually exclusive with all output modifiers |

### Simplified Rule Set

Instead of checking all 32 combinations, implement these **4 rules** (checked in order):

1. `--dashboard` is mutually exclusive with `--quiet`, `--verbose`, `--fast`, `--full-output`
2. `--verbose` is mutually exclusive with `--quiet` and `--fast`
3. `--fast` implies `--quiet` (document this in help text)
4. All other combinations are valid

### Proposed Validation Function

```python
def _validate_output_flags(
    quiet: bool, verbose: bool, fast: bool, full_output: bool, dashboard: bool, cli
) -> None:
    """Validate output-mode flag combinations. Raises SystemExit(2) on conflict."""
    if dashboard:
        conflicts = []
        if quiet: conflicts.append("--quiet")
        if verbose: conflicts.append("--verbose")
        if fast: conflicts.append("--fast")
        if full_output: conflicts.append("--full-output")
        if conflicts:
            cli.error(f"--dashboard cannot be used with {', '.join(conflicts)}")
            raise SystemExit(2)

    if verbose and quiet:
        cli.error("--verbose and --quiet cannot be used together")
        raise SystemExit(2)

    if verbose and fast:
        cli.error("--verbose and --fast cannot be used together (--fast implies --quiet)")
        raise SystemExit(2)
```

### Help Text Improvements

```python
quiet: Annotated[bool, Description(
    "Minimal output — only errors and final summary"
)] = False,
verbose: Annotated[bool, Description(
    "Show per-file build details (incompatible with --quiet, --fast)"
)] = False,
fast: Annotated[bool, Description(
    "Maximum speed: implies --quiet, disables live progress"
)] = False,
full_output: Annotated[bool, Description(
    "Traditional line-by-line output instead of live progress bar"
)] = False,
dashboard: Annotated[bool, Description(
    "Launch interactive TUI dashboard (incompatible with other output flags)"
)] = False,
```

### Tri-State Flag Help Text

```python
incremental: Annotated[bool, Description(
    "Force incremental build using cache. Default: auto-detect (enabled when cache exists)"
)] = False,
no_incremental: Annotated[bool, Description(
    "Force full rebuild, ignoring cache. Default: auto-detect"
)] = False,
assets_pipeline: Annotated[bool, Description(
    "Force Node-based assets pipeline. Default: auto-detect (enabled when package.json exists)"
)] = False,
no_assets_pipeline: Annotated[bool, Description(
    "Disable Node-based assets pipeline. Default: auto-detect"
)] = False,
```

---

## Summary: What Sprint 1 Needs From This Design

| Task 0.x | Decision | Sprint 1 Action |
|----------|----------|-----------------|
| 0.1 | Tagged `{"t": "p"/"s", "v": "..."}` format with legacy fallback | Implement in `effect.py:to_dict` and `from_dict` |
| 0.1 | Change `cascade_sources`/`data_files` to default `frozenset()` | Update `effect.py` + 2 production callers |
| 0.2 | Standard `{"status", "message", ...}` return shape | Fix 24 `return None` sites in Sprint 2 |
| 0.2 | Fix `check.py:312` SystemExit with string arg | Fix in Sprint 2 |
| 0.3 | 4-rule validation function | Implement in Sprint 3 |
| 0.3 | Updated help text for 9 flags | Implement in Sprint 3 |
