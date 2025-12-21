# RFC: CLI Output Experience (ASCII-first, cat+mouse branding, semantic styling)

**Status**: Draft  
**Created**: 2025-12-21  
**Author**: AI Assistant  
**Confidence**: 86% 🟢

---

## Executive Summary

Bengal’s CLI output is informative but inconsistent: multiple subsystems bypass `CLIOutput`, several headings/icons are hardcoded (including emoji), and styling/casing varies across build, post-processing, health checks, and summaries. This RFC proposes a unified output experience that is **ASCII-first** (cat + mouse for branding), with **semantic styling** (colors/bolding/casing used consistently and meaningfully) and **no silent gaps**.

**Recommendation**: Adopt an **icon policy** (ASCII by default, emoji opt-in), route build output through `CLIOutput`, and standardize section headers, phase lines, and summaries.

---

## Problem Statement

### 1) Output is not centralized (multiple code paths print directly)

- Post-processing prints a hardcoded emoji header via `print()`/`reporter.log()` instead of `CLIOutput`:
  - `bengal/bengal/orchestration/postprocess.py:118-123`

### 2) Emojis are embedded in core output and summaries (hard to disable cleanly)

- Stats display uses emoji headings and emoji-based “performance grade” tokens:
  - `bengal/bengal/orchestration/stats/display.py:186-188` (📊 Content Statistics)
  - `bengal/bengal/orchestration/stats/display.py:254-264` (🚀/⚡/🐌)
  - `bengal/bengal/orchestration/stats/display.py:321-327` (📈 Throughput)
  - `bengal/bengal/orchestration/stats/display.py:332` (📂 Output)
- Rich build summary has additional emoji headings:
  - `bengal/bengal/orchestration/summary.py:388-438` (Build Complete + 📂 Output)

### 3) Icon defaults are emoji in `CLIOutput` (even when we want ASCII-only)

`CLIOutput` currently defaults several methods to emoji:
- `success(icon="✨")`, `warning(icon="⚠️")`, `error(icon="❌")`, `tip(icon="💡")`, `path(icon="📂")`
  - `bengal/bengal/output/core.py:243-334`

### 4) Style tokens exist, but usage is inconsistent and sometimes bypassed

Bengal already has a semantic Rich theme with named tokens (`header`, `success`, `warning`, `error`, `bengal`, `mouse`, etc.):
- `bengal/bengal/utils/rich_console.py:21-55`

However, some output uses raw strings with embedded emoji and hardcoded casing (e.g., “BUILD COMPLETE (WITH WARNINGS)”):
- `bengal/bengal/orchestration/stats/display.py:157-183`

---

## Goals

1. **ASCII-first output** by default:
   - Keep the Bengal cat (`ᓚᘏᗢ`) as the primary brand marker (already supported by `CLIOutput.header`)
   - Keep the mouse (`ᘛ⁐̤ᕐᐷ`) for error headers (already supported by `CLIOutput.error_header`)
2. **No silent gaps**: every potentially slow build step emits a phase line with ms.
3. **Semantic styling**: colors/bolding/casing communicate meaning consistently.
4. **Centralization**: orchestrators and summaries use `CLIOutput` APIs, not raw `print()`/emoji strings.
5. **Opt-in emoji**: users can enable emoji if they want, without impacting ASCII-default users.

## Non-Goals

- Rewriting the build pipeline or health check logic.
- Changing log output emitted via structured logging.
- Removing Rich support (we keep Rich, but ensure plain output is equally readable).

---

## Current State (Evidence)

### Branding support exists (cat + mouse)

- Cat header is explicitly supported:
  - `bengal/bengal/output/core.py:110-143`
- Mouse error header is explicitly supported:
  - `bengal/bengal/output/core.py:297-320`

### Emojis are currently “on” for Rich console

The Rich console is created with emoji support enabled:
- `bengal/bengal/utils/rich_console.py:79-85`

---

## Design Options

### Option A: ASCII-first default + emoji opt-in (Recommended)

**What**:
- Default icon set uses ASCII (`✓`, `!`, `x`, `->`) plus cat and mouse for branding.
- Emoji are only used when a user explicitly opts in (config or env var).
- Replace hardcoded emoji section headers with `CLIOutput.subheader(...)` and/or dedicated section helpers.

**Pros**:
- Matches stated preference: cat + mouse, minimal emoji noise.
- Intended to remain copy/paste friendly and reduce reliance on emoji rendering quirks.
- Easier to make casing and emphasis meaningful.

**Cons**:
- Requires touching multiple call sites that currently print emoji strings.

### Option B: Keep emoji default, but centralize output

**Pros**: minimal behavior change.  
**Cons**: does not address “I’m not sure I want emojis.”

### Option C: Profile-based icons (Writer ASCII, Developer emoji, etc.)

**Pros**: flexible defaults for personas.  
**Cons**: introduces complexity; surprising if output changes based on profile.

---

## Proposed Design (Option A)

### 1) Icon policy

Introduce a small “icon set” layer consumed by `CLIOutput`:
- **brand.mascot**: `ᓚᘏᗢ` (cat)
- **brand.error_mascot**: `ᘛ⁐̤ᕐᐷ` (mouse)
- **status.success**: `✓`
- **status.warning**: `!`
- **status.error**: `x`
- **path.arrow**: `↪` (already used in plain output paths)

Scope:
- `CLIOutput.success/warning/error/tip/path/phase/subheader` should default to the active icon set instead of hardcoded emoji defaults.

### 2) Semantic styling rules (colors/bolding/casing)

Use the existing semantic Rich theme tokens and make the *meaning* consistent:
- **Casing**:
  - Section titles: sentence case (“Post-processing”, “Content statistics”, “Build complete”)
  - Phase names: title case (“Track assets”, “Post-process”) or consistent sentence case; pick one and apply everywhere.
- **Bolding**:
  - Bold only: headers, phase labels, and error headings.
  - Avoid bolding entire large blocks (“BUILD COMPLETE (WITH WARNINGS)” currently does this in some paths).
- **Color semantics**:
  - Preserve existing semantic palette + theme mapping (`header`, `success`, `warning`, `error`, `mouse`, `bengal`)
    - `bengal/bengal/utils/rich_console.py:21-55`

### 3) Centralize section headers (remove hardcoded emoji headings)

Replace:
- `print("\n🔧 Post-processing:")` and `reporter.log("\n🔧 Post-processing:")`
  - `bengal/bengal/orchestration/postprocess.py:118-123`

With:
- `cli.subheader("Post-processing", icon=None)` (or a dedicated helper `cli.section("Post-processing")`)

Similarly, replace emoji headings in:
- `bengal/bengal/orchestration/stats/display.py` (Content Statistics, Build Configuration, Performance, Throughput, Output)
- `bengal/bengal/orchestration/summary.py` (rich summary footer headings)

### 4) No silent gaps: phase lines are required for any step that can take noticeable time

Policy:
- Every build “phase” must emit `cli.phase(..., duration_ms=...)`.
- If a phase is conditional (e.g., only on incremental), it should still emit a phase line when it runs.

---

## Implementation Plan (Incremental)

1. **Introduce icon configuration and defaults**
   - Add an icon set concept to `CLIOutput` (ASCII default).
   - Add an opt-in for emoji (env var or config).
2. **Stop bypassing `CLIOutput`**
   - Replace post-process header print with `CLIOutput`-based section header.
3. **Normalize build summary output**
   - Replace emoji headings/casing in `orchestration/stats/display.py` and `orchestration/summary.py` with semantic section helpers.
4. **Document output conventions**
   - Add a short “CLI Output Conventions” doc (or embed in `COLOR_PALETTE.md`) describing casing, icons, and meaning.

---

## Risks & Mitigations

- **Risk**: Snapshot-like tests that assert exact output text may fail after formatting changes.
  - **Mitigation**: Update tests to assert semantic content rather than exact emoji strings; keep stable indentation and ordering.
- **Risk**: Users relying on emoji for quick scanning may dislike the change.
  - **Mitigation**: Provide an opt-in emoji mode.

---

## Success Criteria

- Default build output contains **no emoji** except:
  - `ᓚᘏᗢ` (header) and `ᘛ⁐̤ᕐᐷ` (error header).
- Every build step that can take time emits a visible phase line with ms.
- “Build complete” section is consistent across Rich/plain, full/incremental builds.

---

## Confidence (Scoring)

**Confidence** is based on: Evidence (40) + Consistency (30) + Recency (15) + Tests (15).

- **Evidence (36/40)**: Strong code evidence of current output sources and theme tokens:
  - `bengal/bengal/orchestration/stats/display.py:186-333`
  - `bengal/bengal/orchestration/postprocess.py:118-123`
  - `bengal/bengal/output/core.py:243-334`
  - `bengal/bengal/utils/rich_console.py:21-85`
- **Consistency (26/30)**: Multiple call sites confirm the same pattern (some centralized, some bypassing).
- **Recency (12/15)**: Files appear actively used in current builds (consistent with observed build output).
- **Tests (12/15)**: Output behavior is partially covered indirectly; RFC proposes changes likely requiring test updates.

**Total**: 86% 🟢
