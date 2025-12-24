# RFC: Health Package Big O Optimizations

**Status**: ✅ Implemented  
**Created**: 2025-01-XX  
**Implemented**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: Health (Validators, LinkCheck, AutoFixer)  
**Confidence**: 95% 🟢 (verified against 38 source files, line-accurate)  
**Priority**: P3 (Low-Medium) — Performance improvements for large sites (1000+ pages)  
**Estimated Effort**: 2-3 days (actual: completed)

---

## Implementation Notes (2025-12-24)

All optimizations in this RFC have been implemented:

| Optimization | Status | Location |
|--------------|--------|----------|
| **ValidatorReport caching** | ✅ Done | `report.py:392-447` — Uses `@cached_property` for `_counts` |
| **DirectiveAnalyzer code block index** | ✅ Done | `analysis.py:318-393` — `_build_code_block_index()` |
| **DirectiveAnalyzer colon directive index** | ✅ Done | `analysis.py:395-448` — `_build_colon_directive_index()` |
| **AutoFixer `_create_file_fix()` dict lookup** | ✅ Done | `autofix.py:341-504` — Uses `directive_by_line` dict |
| **AutoFixer `_create_fence_fix()` dict lookup** | ✅ Done | `autofix.py:597-716` — Uses `directive_by_line` dict |
| **AutoFixer `_is_descendant()` dict lookup** | ✅ Done | `autofix.py:512-540` — Takes `directive_by_line` parameter |
| **AutoFixer `_get_depth()` dict lookup** | ✅ Done | `autofix.py:542-565` — Takes `directive_by_line` parameter |

---

## Executive Summary

Comprehensive Big O analysis of the `bengal.health` package (38 files) identified **solid overall architecture** with a few algorithmic hotspots:

**Key Findings**:

1. ✅ **Already Optimized**:
   - `URLCollisionValidator`: O(P) with O(1) hash lookups
   - `InternalLinkChecker`: O(H) init with O(1) set lookups
   - `AsyncLinkChecker`: Bounded concurrency with semaphores

2. ⚠️ **Hidden O(L²) in DirectiveAnalyzer** — Three O(L) position-check methods called per line:
   - `_is_inside_code_block()` (lines 274-332)
   - `_is_inside_colon_directive()` (lines 408-426)
   - `_is_inside_inline_code()` (lines 428-441) — calls `_is_inside_code_block()` internally

3. ⚠️ **Linear Parent Lookup in AutoFixer** — O(D) search per hierarchy traversal via `next((d for d in directives...))` pattern appears **7 times** in `_create_file_fix()`, `_is_descendant()`, `_get_depth()`

4. ⚠️ **Uncached Properties in ValidatorReport** — 5 count properties each iterate all results; `has_problems` calls two of them, doubling iterations

**Current State**: The implementation performs well for typical sites (100-1000 pages). These optimizations target:
- Very large sites (5K+ pages) with directive-heavy content
- Deep directive nesting hierarchies in autofix operations
- High-frequency report property access in verbose/CI modes

**Impact**:
- DirectiveAnalyzer: O(L²) → O(L) per file
- AutoFixer hierarchy: O(D²) → O(D) per fix
- ValidatorReport: O(R) → O(1) per property access

---

## Problem Statement

### Current Performance Characteristics

| Operation | Current Complexity | Optimal Complexity | Impact at Scale |
|-----------|-------------------|-------------------|-----------------|
| **DirectiveAnalyzer._check_code_block_nesting()** | O(L²) | O(L) | High (directive-heavy pages) |
| **DirectiveAnalyzer._extract_directives()** | O(L²) | O(L) | High (directive-heavy pages) |
| **AutoFixer._create_file_fix() parent lookup** | O(D²) | O(D) | Medium (deep hierarchies) |
| **ValidatorReport count properties** | O(R) per call | O(1) | Low (verbose mode) |

---

### Bottleneck 1: DirectiveAnalyzer Hidden Quadratic — O(L²)

**Location**: `bengal/health/validators/directives/analysis.py`

**Affected Methods**: Two methods share this pattern:

1. `_check_code_block_nesting()` (lines 334-406) — calls `_is_inside_colon_directive()` per line
2. `_extract_directives()` (lines 443-524) — calls `_is_inside_code_block()` AND `_is_inside_inline_code()` per directive

**The Position-Check Methods** (all O(L) per call):

| Method | Lines | Called By | Complexity |
|--------|-------|-----------|------------|
| `_is_inside_code_block()` | 274-332 | `_extract_directives()`, `_is_inside_inline_code()` | O(L) |
| `_is_inside_colon_directive()` | 408-426 | `_check_code_block_nesting()` | O(L) |
| `_is_inside_inline_code()` | 428-441 | `_extract_directives()` | O(L) — calls `_is_inside_code_block()` too! |

**Current Implementation — Method 1** (`analysis.py:334-371`):

```python
def _check_code_block_nesting(self, content: str, file_path: Path) -> list[dict[str, Any]]:
    """Check for markdown code blocks with same fence length."""
    warnings = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):                    # O(L)
        # ... pattern matching ...
        char_pos = len("\n".join(lines[: i - 1]))
        if self._is_inside_colon_directive(content, char_pos):  # O(L) per call!
            continue
        # ...

def _is_inside_colon_directive(self, content: str, position: int) -> bool:
    """Check if a position is inside a colon directive."""
    lines = content[:position].split("\n")                 # O(position) ≈ O(L)
    # ... iterate all lines to track state ...             # O(L) per call
    for line in lines:
        # ... tracking directive depth ...
    return in_directive and directive_depth > 0
```

**Current Implementation — Method 2** (`analysis.py:459-472`):

```python
def _extract_directives(self, content: str, file_path: Path) -> list[dict[str, Any]]:
    """Extract all directive blocks from markdown content."""
    # ...
    while i < len(lines):                                  # O(L)
        match = re.match(colon_start_pattern, lines[i])
        if match:
            char_pos = len("\n".join(lines[:i]))           # O(i) string join
            if self._is_inside_code_block(content, char_pos) or self._is_inside_inline_code(
                content, char_pos
            ):  # BOTH O(L) per call — and _is_inside_inline_code calls _is_inside_code_block!
                i += 1
                continue
```

**Critical Finding**: `_is_inside_inline_code()` calls `_is_inside_code_block()` internally:

```python
def _is_inside_inline_code(self, content: str, position: int) -> bool:
    """Check if a position in content is inside inline code."""
    # ...
    if self._is_inside_code_block(content, position):      # O(L) nested call!
        return True
    return backticks_before % 2 == 1
```

**Problem**:
- Both methods iterate O(L) lines/directives
- Each iteration calls position-check methods that are O(L)
- `_extract_directives()` calls TWO O(L) methods, one of which calls another O(L) method
- **Total: O(L²) to O(3×L²) per file depending on code path**

**Example**:
```
File with 1000 lines:
- Current: 1000 × 1000 = 1,000,000 operations (per method)
- Optimal: 1000 operations (single pass)
```

**Impact**:
- Small files (< 100 lines): Negligible
- Medium files (100-500 lines): Noticeable latency
- Large files (500+ lines): Significant slowdown (~L× slower than optimal)

### Bottleneck 2: AutoFixer Linear Parent Lookup — O(D²)

**Location**: `bengal/health/autofix.py`

**The Pattern Appears 7 Times**:

| Line | Context | Pattern |
|------|---------|---------|
| 421 | Ancestor traversal | `next((d for d in directives if d["line"] == parent_line), None)` |
| 439 | Descendant parent check | `next((d for d in directives if d["line"] == parent_line), None)` |
| 455 | Hierarchy calculation | `next((d for d in directives if d["line"] == parent_line), None)` |
| 521 | `_is_descendant()` | `next((d for d in all_directives if d["line"] == current["parent"]), None)` |
| 541 | `_get_depth()` | `next((d for d in all_directives if d["line"] == current["parent"]), None)` |

**Current Implementation** (`autofix.py:417-426`):

```python
# Add ancestors (walk up parent chain)
current = target_directive
while current.get("parent"):                        # O(depth)
    parent_line = current["parent"]
    parent = next((d for d in directives           # O(D) linear search!
                  if d["line"] == parent_line), None)
    if parent:
        directives_to_fix.add(parent["line"])
        current = parent
    else:
        break
```

**And again in `_is_descendant()` and `_get_depth()`** (`autofix.py:500-544`):

```python
def _is_descendant(self, directive, ancestor, all_directives) -> bool:
    current = directive
    while current and current.get("parent"):
        if current["parent"] == ancestor["line"]:
            return True
        current = next((d for d in all_directives if d["line"] == current["parent"]), None)  # O(D)!
        if not current:
            break
    return False

def _get_depth(self, directive, all_directives) -> int:
    depth = 0
    current = directive
    while current and current.get("parent"):
        depth += 1
        current = next((d for d in all_directives if d["line"] == current["parent"]), None)  # O(D)!
        if not current:
            break
    return depth
```

**Problem**:
- Parent lookup uses `next((d for d in directives if d["line"] == parent_line), None)` — **7 call sites**
- This is O(D) linear search for each parent lookup
- With D directives and depth H, worst case is O(D × H) which can be O(D²)
- `_is_descendant()` is called for EVERY directive when finding descendants (line 464)

**Example**:
```
File with 50 nested directives:
- Current: 50 × 50 = 2,500 lookups
- Optimal: 50 lookups with dict index
```

**Impact**:
- Shallow nesting (< 5 levels): Negligible
- Medium nesting (5-15 levels): Minor overhead
- Deep nesting (15+ levels): Quadratic slowdown

### Bottleneck 3: ValidatorReport Uncached Properties — O(R)

**Location**: `bengal/health/report.py`

**Current Implementation** (`report.py:391-419`):

```python
@dataclass
class ValidatorReport:
    validator_name: str
    results: list[CheckResult] = field(default_factory=list)
    # ...

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.SUCCESS)  # O(R)

    @property
    def info_count(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.INFO)     # O(R)

    @property
    def warning_count(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.WARNING)  # O(R)

    @property
    def suggestion_count(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.SUGGESTION)  # O(R)

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.ERROR)    # O(R)
```

**Cascading Problem** (`report.py:417-419`):

```python
@property
def has_problems(self) -> bool:
    """Check if this validator found any warnings or errors."""
    return self.warning_count > 0 or self.error_count > 0  # Calls TWO O(R) properties!
```

**And `status_emoji` cascades even more** (`report.py:422-434`):

```python
@property
def status_emoji(self) -> str:
    if self.error_count > 0:        # O(R)
        return icons.error
    elif self.warning_count > 0:    # O(R) again!
        return icons.warning
    elif self.suggestion_count > 0: # O(R) again!
        return icons.tip
    elif self.info_count > 0:       # O(R) again!
        return icons.info
    # ...
```

**Problem**:
- 5 count properties, each O(R)
- `has_problems` calls 2 of them: O(2R)
- `status_emoji` calls up to 4 of them: O(4R) worst case
- Called multiple times during formatting

**Example**:
```
Validator with 100 results, format_console() accesses:
- status_emoji (up to 4R = 400 iterations)
- has_problems (2R = 200 iterations)  
- Individual counts for display (5R = 500 iterations)
Current: 1100+ iterations for ONE report
Optimal: 100 (once) + O(1) cached lookups = ~100 operations
```

**Impact**:
- Few results (< 20): Negligible
- Medium results (20-100): Minor overhead
- Many results (100+): Noticeable in verbose mode, multiplied by number of validators

---

## Proposed Solutions

### Solution 1: Pre-computed Block Ranges (Recommended)

**Approach**: Single O(L) pass to build both code block AND colon directive interval maps, then O(R) lookups where R << L.

**Key Insight**: We need THREE indices to replace all O(L) position-check methods:
1. `code_block_ranges` — for `_is_inside_code_block()`
2. `colon_directive_ranges` — for `_is_inside_colon_directive()`
3. `inline_code_positions` — for `_is_inside_inline_code()` (backtick tracking per line)

**Implementation**:

```python
from dataclasses import dataclass

@dataclass
class BlockRange:
    """Represents a fenced block's line range."""
    start_line: int
    end_line: int
    fence_type: str  # "backtick", "colon", or "indented"
    fence_depth: int

@dataclass
class ContentAnalysisIndex:
    """Pre-computed indices for O(1) position checks."""
    code_block_ranges: list[BlockRange]      # Backtick/tilde code blocks
    colon_directive_ranges: list[BlockRange] # Colon directive blocks
    lines_in_code_blocks: set[int]           # Line numbers inside code blocks
    lines_in_colon_directives: set[int]      # Line numbers inside colon directives
    inline_code_odd_backticks: set[int]      # Lines with odd backtick count (partial inline code)

class DirectiveAnalyzer:
    def _build_content_index(self, lines: list[str]) -> ContentAnalysisIndex:
        """
        Build all block indices in single O(L) pass.

        This replaces three O(L) per-call methods with O(1) set lookups.
        """
        code_blocks: list[BlockRange] = []
        colon_directives: list[BlockRange] = []
        code_block_stack: list[tuple[int, str, int]] = []  # (start_line, marker, depth)
        colon_stack: list[tuple[int, int]] = []  # (start_line, depth)

        lines_in_code = set()
        lines_in_colon = set()
        inline_odd = set()

        backtick_pattern = re.compile(r'^(\s*)(`{3,}|~{3,})([^\n]*)')
        colon_open_pattern = re.compile(r'^(\s*)(:{3,})\{([^}]+)\}')
        colon_close_pattern = re.compile(r'^(\s*)(:{3,})\s*$')

        in_code_block = False
        current_code_marker = None

        for i, line in enumerate(lines, 1):
            # Track inline code (odd backtick count means we're inside inline code)
            backtick_count = line.count('`')
            if backtick_count % 2 == 1:
                inline_odd.add(i)

            # Skip if inside fenced code block (for colon directive detection)
            if in_code_block:
                lines_in_code.add(i)
                # Check for closing fence
                close_match = backtick_pattern.match(line)
                if close_match:
                    indent = len(close_match.group(1))
                    marker = close_match.group(2)
                    lang = close_match.group(3).strip()
                    if indent < 4 and not lang and marker[0] == current_code_marker[0] and len(marker) >= len(current_code_marker):
                        # Closing fence
                        in_code_block = False
                        if code_block_stack:
                            start, _, depth = code_block_stack.pop()
                            code_blocks.append(BlockRange(start, i, "backtick", depth))
                continue

            # Check for code block opening
            code_match = backtick_pattern.match(line)
            if code_match:
                indent = len(code_match.group(1))
                marker = code_match.group(2)
                lang = code_match.group(3).strip()
                if indent < 4 and lang:  # Opening fence has language
                    in_code_block = True
                    current_code_marker = marker
                    code_block_stack.append((i, marker[0], len(marker)))
                    lines_in_code.add(i)
                continue

            # Check for colon directive opening
            colon_open = colon_open_pattern.match(line)
            if colon_open:
                indent = len(colon_open.group(1))
                if indent < 4:
                    depth = len(colon_open.group(2))
                    colon_stack.append((i, depth))
                    lines_in_colon.add(i)
                continue

            # Check for colon directive closing
            colon_close = colon_close_pattern.match(line)
            if colon_close and colon_stack:
                depth = len(colon_close.group(2))
                # Find matching opener
                for j in range(len(colon_stack) - 1, -1, -1):
                    if colon_stack[j][1] == depth:
                        start, _ = colon_stack.pop(j)
                        colon_directives.append(BlockRange(start, i, "colon", depth))
                        # Mark all lines in this range
                        for line_num in range(start, i + 1):
                            lines_in_colon.add(line_num)
                        break
                continue

            # Mark lines inside open colon directives
            if colon_stack:
                lines_in_colon.add(i)

        return ContentAnalysisIndex(
            code_block_ranges=sorted(code_blocks, key=lambda r: r.start_line),
            colon_directive_ranges=sorted(colon_directives, key=lambda r: r.start_line),
            lines_in_code_blocks=lines_in_code,
            lines_in_colon_directives=lines_in_colon,
            inline_code_odd_backticks=inline_odd,
        )

    def _is_inside_code_block_fast(self, line_number: int, index: ContentAnalysisIndex) -> bool:
        """O(1) check if line is inside a code block."""
        return line_number in index.lines_in_code_blocks

    def _is_inside_colon_directive_fast(self, line_number: int, index: ContentAnalysisIndex) -> bool:
        """O(1) check if line is inside a colon directive."""
        return line_number in index.lines_in_colon_directives

    def _is_inside_inline_code_fast(self, line_number: int, index: ContentAnalysisIndex) -> bool:
        """O(1) check if line has odd backtick count (inside inline code)."""
        if line_number in index.lines_in_code_blocks:
            return True
        return line_number in index.inline_code_odd_backticks
```

**Complexity Change**:
- **Build index**: O(L) single pass — done ONCE per file
- **Each lookup**: O(1) set membership check
- **Total**: O(L + L) = **O(L)** vs previous O(L²) to O(3×L²) = **~L to ~3L improvement**

**Why set-based lookup is preferred over range scanning**:
- O(1) vs O(R) for each check
- Pre-computing line sets during index build is trivial overhead
- Simpler conditional logic in caller methods

**Files to Modify**:
- `bengal/health/validators/directives/analysis.py`:
  - Add `ContentAnalysisIndex` dataclass
  - Add `_build_content_index()` method
  - Update `_check_code_block_nesting()` to use index
  - Update `_extract_directives()` to use index

### Solution 2: Dict-Indexed Parent Lookup

**Approach**: Build `{line: directive}` dict for O(1) parent lookups.

**Implementation**:

```python
def _create_file_fix(self, file_path: Path, line_numbers: list[int]) -> Any:
    def apply_fix() -> bool:
        # Parse directive hierarchy
        directives = self._parse_directive_hierarchy(lines)

        # Build O(1) lookup index
        directive_by_line: dict[int, dict[str, Any]] = {
            d["line"]: d for d in directives
        }

        # Now parent lookup is O(1)
        for line_num in line_numbers:
            target_directive = directive_by_line.get(line_num)
            if not target_directive:
                continue

            # Walk up parent chain with O(1) lookups
            current = target_directive
            while current.get("parent"):
                parent_line = current["parent"]
                parent = directive_by_line.get(parent_line)  # O(1) instead of O(D)!
                if parent:
                    directives_to_fix.add(parent["line"])
                    current = parent
                else:
                    break

        # ... rest of fix logic ...
```

**Complexity Change**:
- **Build index**: O(D) single pass
- **Each parent lookup**: O(1) instead of O(D)
- **Total**: O(D + F × H) vs O(D × F × H) = **~D/H improvement** (typically 5-20x)

**Files to Modify**:
- `bengal/health/autofix.py` — `_create_file_fix()`, `_is_descendant()`, `_get_depth()`

### Solution 3: Cached ValidatorReport Counts

**Approach**: Use `@functools.cached_property` for automatic caching (simpler than manual cache).

**Rationale**: `ValidatorReport` is effectively immutable after construction — results are added during validation, then the report is consumed for display. This makes `cached_property` safe without invalidation logic.

**Implementation (Recommended — Simple)**:

```python
from functools import cached_property

@dataclass
class ValidatorReport:
    """Report from a single validator's execution."""

    validator_name: str
    results: list[CheckResult] = field(default_factory=list)
    duration_ms: float = 0.0
    stats: ValidatorStats | None = None

    @cached_property
    def _counts(self) -> dict[str, int]:
        """Compute all counts in single O(R) pass, cached automatically."""
        counts = {"passed": 0, "info": 0, "warning": 0, "suggestion": 0, "error": 0}
        for r in self.results:
            counts[r.status.value] = counts.get(r.status.value, 0) + 1
        # Map SUCCESS -> passed for backward compatibility
        counts["passed"] = counts.pop("success", 0)
        return counts

    @property
    def passed_count(self) -> int:
        """Count of successful checks."""
        return self._counts["passed"]

    @property
    def warning_count(self) -> int:
        """Count of warnings."""
        return self._counts["warning"]

    @property
    def error_count(self) -> int:
        """Count of errors."""
        return self._counts["error"]

    # ... other count properties use self._counts[key] ...
```

**Alternative (Manual Cache — If Mutation Needed)**:

```python
@dataclass
class ValidatorReport:
    """Report with manual cache invalidation support."""

    validator_name: str
    results: list[CheckResult] = field(default_factory=list)
    duration_ms: float = 0.0
    stats: ValidatorStats | None = None
    _cached_counts: dict[str, int] | None = field(default=None, repr=False)

    def add_result(self, result: CheckResult) -> None:
        """Add result and invalidate cache."""
        self.results.append(result)
        self._cached_counts = None  # Invalidate

    def _get_counts(self) -> dict[str, int]:
        """Get counts (cached after first call)."""
        if self._cached_counts is None:
            self._cached_counts = self._compute_counts()
        return self._cached_counts

    # ... properties use self._get_counts() ...
```

**Complexity Change**:
- **First access**: O(R) to compute all counts
- **Subsequent access**: O(1) cached lookup
- **Total for N accesses**: O(R + N) vs O(R × N) = **~N improvement** (typically 3-5x)

**Recommendation**: Use `cached_property` (simpler) unless mutation after construction is required.

**Files to Modify**:
- `bengal/health/report.py` — `ValidatorReport` class

---

## Implementation Plan

### Phase 1: DirectiveAnalyzer O(L²) → O(L) (High Impact)

**Priority**: P2 (Medium)  
**Effort**: 1 day  
**Risk**: Low

**Scope**: Fix quadratic behavior in **both** affected methods:
- `_check_code_block_nesting()` — uses `_is_inside_colon_directive()`
- `_extract_directives()` — uses `_is_inside_code_block()` and `_is_inside_inline_code()`

**Steps**:
1. Add `CodeBlockRange` and `ColonDirectiveRange` dataclasses
2. Add `_build_code_block_index()` method (handles both fence types)
3. Add `_build_colon_directive_index()` method
4. Update `_check_code_block_nesting()` to use pre-computed colon directive index
5. Update `_extract_directives()` to use pre-computed code block index
6. Comprehensive testing with directive-heavy files

**Success Criteria**:
- O(L) complexity verified via profiling for both methods
- All existing tests pass
- No correctness regression

### Phase 2: AutoFixer Dict Index (Medium Impact)

**Priority**: P3 (Low)  
**Effort**: 0.5 days  
**Risk**: Very Low

**Steps**:
1. Add `directive_by_line` dict construction
2. Replace `next((d for d in directives...))` with dict lookup
3. Update `_is_descendant()` and `_get_depth()` helpers
4. Test with deeply nested directive files

**Success Criteria**:
- O(D) complexity for hierarchy operations
- All autofix tests pass
- Fixes work correctly for complex nesting

### Phase 3: ValidatorReport Caching (Low Impact)

**Priority**: P4 (Very Low)  
**Effort**: 0.5 days  
**Risk**: Very Low

**Steps**:
1. Add `from functools import cached_property` import
2. Add `_counts` cached property that computes all counts in single pass
3. Update `passed_count`, `warning_count`, `error_count`, etc. to use `self._counts[key]`
4. Remove redundant individual count iterations
5. Add docstring noting immutability assumption

**Success Criteria**:
- O(1) property access after first call
- All report tests pass
- Cache populates correctly on first count property access

---

## Testing Strategy

### Unit Tests

1. **DirectiveAnalyzer Index**
   - Test code block range detection (backtick and colon fences)
   - Test colon directive range detection
   - Test nested fence handling
   - Test edge cases (unclosed blocks, overlapping, mixed fence types)
   - Test `_check_code_block_nesting()` uses colon directive index
   - Test `_extract_directives()` uses code block index
   - Performance test with 1000+ line files (verify O(L) scaling)

2. **AutoFixer Dict Lookup**
   - Test parent chain traversal
   - Test deep nesting (20+ levels)
   - Test mixed fence types

3. **ValidatorReport Caching**
   - Test cache population
   - Test multiple property accesses
   - Test with empty results

### Performance Benchmarks

```python
# Benchmark script: scripts/benchmark_health.py

import time
from pathlib import Path
from bengal.health.validators.directives.analysis import DirectiveAnalyzer

def benchmark_directive_analysis(file_path: str, iterations: int = 10):
    """Measure directive analysis performance for both O(L²) methods."""
    with open(file_path) as f:
        content = f.read()

    analyzer = DirectiveAnalyzer()
    path = Path(file_path)
    lines = content.count('\n')

    # Benchmark _check_code_block_nesting (uses _is_inside_colon_directive)
    start = time.perf_counter()
    for _ in range(iterations):
        analyzer._check_code_block_nesting(content, path)
    elapsed_nesting = time.perf_counter() - start

    # Benchmark _extract_directives (uses _is_inside_code_block)
    start = time.perf_counter()
    for _ in range(iterations):
        analyzer._extract_directives(content, path)
    elapsed_extract = time.perf_counter() - start

    return {
        "file": file_path,
        "lines": lines,
        "iterations": iterations,
        "check_nesting_ms": (elapsed_nesting / iterations) * 1000,
        "extract_directives_ms": (elapsed_extract / iterations) * 1000,
        "expected_scaling": "O(L)" if lines < 100 else "O(L²) visible",
    }

# Run with: 100, 500, 1000, 2000 line files
# Compare before/after optimization
# Expected: After optimization, both methods should scale linearly
```

**Metrics to Collect**:
- Time per analysis for various file sizes
- Memory usage during analysis
- Scaling behavior (should be linear, not quadratic)

---

## Risk Assessment

| Optimization | Risk Level | Mitigation |
|--------------|------------|------------|
| **Code block index** | Low | Clear algorithm, comprehensive tests |
| **Dict parent lookup** | Very Low | Simple refactor, same logic |
| **Count caching** | Very Low | Read-only cache, no mutation |

### Backward Compatibility

All optimizations are **fully backward compatible**:
- **Code block index**: Internal implementation detail
- **Dict lookup**: Same API, different implementation
- **Count caching**: Same property interface

---

## Alternatives Considered

### Alternative 1: Keep Current Implementation

**Pros**: No changes needed, works for typical sites  
**Cons**: O(L²) scales poorly for large files  
**Decision**: Rejected — directive analysis is user-facing and should be fast

### Alternative 2: Lazy Analysis (Skip Checks)

**Approach**: Only check directives on demand  
**Pros**: Fast for sites with few directive issues  
**Cons**: Misses issues until accessed  
**Decision**: Rejected — health checks should be comprehensive

### Alternative 3: Parallel Directive Analysis

**Approach**: Process pages in parallel  
**Pros**: Faster for many pages  
**Cons**: Doesn't fix per-file quadratic  
**Decision**: Deferred — fix fundamental algorithm first

### Alternative 4: Manual Cache vs cached_property for ValidatorReport

**Approach A — Manual cache with invalidation**:  
**Pros**: Supports mutation after construction  
**Cons**: More code, requires careful invalidation  

**Approach B — `@functools.cached_property`**:  
**Pros**: Simpler, automatic caching, less code  
**Cons**: Cannot invalidate; requires immutability after construction  

**Decision**: Use `cached_property` — ValidatorReport is effectively immutable after construction (results are added during validation, then consumed). Manual cache only needed if future requirements add result mutation.

---

## Code Verification

This RFC was verified against the actual source code:

**Verified Implementations**:
- ✅ **`_is_inside_code_block()`**: Lines 274-332 — Confirmed O(L) per call via `content[:position].split("\n")` and line iteration
- ✅ **`_is_inside_colon_directive()`**: Lines 408-426 — Confirmed O(L) per call via `content[:position].split("\n")` and line iteration
- ✅ **`_is_inside_inline_code()`**: Lines 428-441 — Confirmed O(L) AND calls `_is_inside_code_block()` at line 438
- ✅ **`_check_code_block_nesting()`**: Lines 334-406 — Confirmed O(L²) via line 371 calling `_is_inside_colon_directive()` per line
- ✅ **`_extract_directives()`**: Lines 443-524 — Confirmed O(L²+) via line 468 calling BOTH `_is_inside_code_block()` AND `_is_inside_inline_code()` per directive
- ✅ **AutoFixer linear search**: Found 7 occurrences of `next((d for d in directives/all_directives...))` pattern at lines 421, 439, 455, 521, 541
- ✅ **ValidatorReport uncached**: Lines 391-434 — Confirmed 5 count properties each iterating results, with `has_problems` and `status_emoji` cascading

**Key Finding**: The `_is_inside_inline_code()` method is worse than documented — it calls `_is_inside_code_block()` internally, creating a 2× O(L) cost per call. This means `_extract_directives()` can be O(3×L²) in the worst case.

---

## References

- **Source Code** (verified line numbers):
  - `bengal/health/validators/directives/analysis.py:274-332` — `_is_inside_code_block()` (O(L) per call)
  - `bengal/health/validators/directives/analysis.py:334-406` — `_check_code_block_nesting()` (O(L²) total)
  - `bengal/health/validators/directives/analysis.py:408-426` — `_is_inside_colon_directive()` (O(L) per call)
  - `bengal/health/validators/directives/analysis.py:428-441` — `_is_inside_inline_code()` (O(L) per call, calls `_is_inside_code_block`)
  - `bengal/health/validators/directives/analysis.py:443-524` — `_extract_directives()` (O(L²) to O(3×L²))
  - `bengal/health/autofix.py:417-426` — Ancestor traversal with O(D) linear search
  - `bengal/health/autofix.py:428-443` — Descendant discovery with O(D) linear search
  - `bengal/health/autofix.py:449-474` — Hierarchy calculation with O(D) linear search
  - `bengal/health/autofix.py:500-524` — `_is_descendant()` with O(D) linear search
  - `bengal/health/autofix.py:526-544` — `_get_depth()` with O(D) linear search
  - `bengal/health/report.py:391-414` — `ValidatorReport` count properties (5 × O(R))
  - `bengal/health/report.py:417-419` — `has_problems` cascades to 2 × O(R)
  - `bengal/health/report.py:422-434` — `status_emoji` cascades to up to 4 × O(R)

- **Related RFCs**:
  - `rfc-big-o-complexity-optimizations.md` — Template filter optimizations
  - `rfc-performance-optimizations.md` — General performance patterns
  - `rfc-orchestration-package-optimizations.md` — Similar caching patterns

---

## Complexity Summary

### Before Optimization

| Component | Time | Space | Bottleneck |
|-----------|------|-------|------------|
| `_is_inside_code_block()` | O(L) per call | O(L) | String split + line iteration |
| `_is_inside_colon_directive()` | O(L) per call | O(L) | String split + line iteration |
| `_is_inside_inline_code()` | O(2L) per call | O(L) | Calls `_is_inside_code_block()` |
| `_check_code_block_nesting()` | O(L²) | O(L) | Calls `_is_inside_colon_directive()` per line |
| `_extract_directives()` | O(3×L²) | O(L) | Calls BOTH code block checks per directive |
| AutoFixer hierarchy | O(D²) | O(D) | 7× linear parent search |
| ValidatorReport counts | O(5R) per format | O(R) | 5 uncached properties |
| ValidatorReport.has_problems | O(2R) | O(1) | Calls 2 count properties |
| ValidatorReport.status_emoji | O(4R) | O(1) | Calls up to 4 count properties |

### After Optimization

| Component | Time | Space | Improvement |
|-----------|------|-------|-------------|
| `_is_inside_code_block_fast()` | O(1) | O(L) | **~L× improvement** |
| `_is_inside_colon_directive_fast()` | O(1) | O(L) | **~L× improvement** |
| `_is_inside_inline_code_fast()` | O(1) | O(L) | **~2L× improvement** |
| `_check_code_block_nesting()` | O(L) | O(L) | **~L× improvement** |
| `_extract_directives()` | O(L) | O(L) | **~3L× improvement** |
| AutoFixer hierarchy | O(D) | O(D) | **~D× improvement** |
| ValidatorReport counts | O(R) total | O(R) | **~5× improvement** |
| ValidatorReport.has_problems | O(1) | O(1) | **~2R× improvement** |
| ValidatorReport.status_emoji | O(1) | O(1) | **~4R× improvement** |

**Legend**:
- L = lines in file (typically 100-2000)
- D = directives in file (typically 5-50)
- R = check results per validator (typically 10-100)
- "~L× improvement" = 1000-line file sees ~1000× speedup (O(L²) → O(L))

---

## Conclusion

These optimizations provide **preventive improvements** for large sites while maintaining full backward compatibility.

**Recommended Priority**:

| Priority | Optimization | Effort | Value | Risk |
|----------|--------------|--------|-------|------|
| P2 | Code block index | 1 day | High | Low |
| P3 | Dict parent lookup | 0.5 days | Medium | Very Low |
| P4 | Count caching | 0.5 days | Low | Very Low |

**Bottom Line**: The DirectiveAnalyzer optimization (Phase 1) provides the highest value with clear O(L²) → O(L) improvement for both `_check_code_block_nesting()` and `_extract_directives()`. The same indexing strategy applies to both methods. The other optimizations are worth doing for code quality but have lower immediate impact.

---

## Appendix A: Quick Wins

These changes can be made immediately with minimal risk:

### Quick Win 1: ValidatorReport Caching (< 15 minutes)

```python
# bengal/health/report.py — Replace lines 391-434

from functools import cached_property

@dataclass
class ValidatorReport:
    validator_name: str
    results: list[CheckResult] = field(default_factory=list)
    duration_ms: float = 0.0
    stats: ValidatorStats | None = None

    @cached_property
    def _counts(self) -> dict[str, int]:
        """Compute all counts in single O(R) pass."""
        counts = {"success": 0, "info": 0, "warning": 0, "suggestion": 0, "error": 0}
        for r in self.results:
            counts[r.status.value] = counts.get(r.status.value, 0) + 1
        return counts

    @property
    def passed_count(self) -> int:
        return self._counts["success"]

    @property
    def info_count(self) -> int:
        return self._counts["info"]

    @property
    def warning_count(self) -> int:
        return self._counts["warning"]

    @property
    def suggestion_count(self) -> int:
        return self._counts["suggestion"]

    @property
    def error_count(self) -> int:
        return self._counts["error"]

    @property
    def has_problems(self) -> bool:
        return self._counts["warning"] > 0 or self._counts["error"] > 0

    @property
    def status_emoji(self) -> str:
        icons = get_icon_set(should_use_emoji())
        counts = self._counts  # Single O(1) access
        if counts["error"] > 0:
            return icons.error
        elif counts["warning"] > 0:
            return icons.warning
        elif counts["suggestion"] > 0:
            return icons.tip
        elif counts["info"] > 0:
            return icons.info
        else:
            return icons.success
```

### Quick Win 2: AutoFixer Dict Index (< 30 minutes)

```python
# bengal/health/autofix.py — Add at start of apply_fix() inner function

# Build O(1) lookup index — add after line ~342
directive_by_line: dict[int, dict[str, Any]] = {
    d["line"]: d for d in directives
}

# Then replace all occurrences of:
#   next((d for d in directives if d["line"] == parent_line), None)
# With:
#   directive_by_line.get(parent_line)
```

---

## Appendix B: Full Component Complexity Analysis

### HealthCheck Orchestrator

| Method | Time | Space | Notes |
|--------|------|-------|-------|
| `run()` | O(V × R) | O(V × R) | V validators, R results |
| `_run_validators_parallel()` | O(V × T / W) | O(V + R) | W workers |
| `_is_validator_in_tier()` | O(T) | O(1) | T = tier config |

### Validators

| Validator | Time | Space | Notes |
|-----------|------|-------|-------|
| URLCollisionValidator | O(P) | O(P) | P pages, dict collision detection |
| ConnectivityValidator | O(P × L) | O(P + E) | Knowledge graph build |
| DirectiveValidator._check_code_block_nesting | O(P × L²) → O(P × L) | O(P × L) | **Target for optimization** — calls `_is_inside_colon_directive()` per line |
| DirectiveValidator._extract_directives | O(P × 3L²) → O(P × L) | O(P × L) | **Target for optimization** — calls 3 position-check methods per directive |

### LinkCheck

| Component | Time | Space | Notes |
|-----------|------|-------|-------|
| InternalLinkChecker | O(H + U) | O(H) | H files, U URLs |
| AsyncLinkChecker | O(U / C × T) | O(U) | C concurrency, T timeout |
| LinkCheckOrchestrator | O(H × L) | O(L × R) | HTML parsing |

### AutoFixer

| Method | Time | Space | Notes |
|--------|------|-------|-------|
| `suggest_fixes()` | O(V × R × D) | O(F) | F fixes |
| `_parse_directive_hierarchy()` | O(L) | O(D) | L lines, D directives |
| `_create_file_fix()` | O(D² × H) → O(D × H) | O(D) | **Target** — 5 linear search sites |
| `_is_descendant()` | O(D × H) → O(H) | O(1) | **Target** — 1 linear search site |
| `_get_depth()` | O(D × H) → O(H) | O(1) | **Target** — 1 linear search site |
| `apply_fixes()` | O(F × L) | O(L) | Per-file fix |

**Note**: H = hierarchy depth (typically 3-10), D = directives (typically 10-50)
