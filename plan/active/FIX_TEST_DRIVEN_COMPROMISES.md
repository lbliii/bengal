# Fix Test-Driven Compromises - Action Plan
**Date**: October 16, 2025  
**Branch**: `enh/stability-test-cicd-and-scripts`  
**Related**: CODE_REVIEW_2025-10-16.md  
**Priority**: High (block merge)  

## Overview

Address 3 instances where code was simplified to satisfy tests rather than implementing robust solutions. These fixes will improve code quality and test coverage before merging the stability branch.

**Total Estimated Time**: 2-3 hours  
**Risk Level**: Low (isolated changes, well-understood scope)

---

## Phase 1: Critical - Pygments Test Restoration 🔴

**Priority**: HIGH - Must fix before merge  
**Estimated Time**: 45 minutes  
**Files**: `tests/unit/rendering/test_pygments_patch.py`

### Problem
Test was weakened to avoid fixing syntax error in try/finally block. Lost critical coverage:
- No verification of `PygmentsPatch.apply()` return value
- No check of `PygmentsPatch.is_patched()` state
- Lost idempotency tests (applying patch multiple times)
- Generic lexer check could pass without patch applied

### Solution

#### Step 1: Create Proper Fixture (10 min)
```python
@pytest.fixture
def clean_pygments_state():
    """Ensure clean state before/after each test."""
    PygmentsPatch.restore()  # Start clean
    yield
    PygmentsPatch.restore()  # Cleanup after test
```

#### Step 2: Restore Original Test Logic (20 min)
```python
def test_patch_can_be_applied(clean_pygments_state):
    """Test that patch can be applied successfully."""
    result = PygmentsPatch.apply()

    assert result is True, "First application should succeed"
    assert PygmentsPatch.is_patched() is True, "Patch should be active"

def test_patch_is_idempotent(clean_pygments_state):
    """Test that applying patch multiple times is safe."""
    result1 = PygmentsPatch.apply()
    result2 = PygmentsPatch.apply()
    result3 = PygmentsPatch.apply()

    assert result1 is True, "First application succeeds"
    assert result2 is False, "Already applied"
    assert result3 is False, "Still already applied"
    assert PygmentsPatch.is_patched() is True

def test_patch_affects_codehilite_module(clean_pygments_state):
    """Test that patch modifies the codehilite module."""
    try:
        import markdown.extensions.codehilite
    except ImportError:
        pytest.skip("markdown-codehilite extension not available")

    PygmentsPatch.apply()
    assert PygmentsPatch.is_patched() is True
```

#### Step 3: Add New Edge Case Tests (15 min)
```python
def test_restore_returns_to_original_state(clean_pygments_state):
    """Test that restore fully reverses the patch."""
    PygmentsPatch.apply()
    assert PygmentsPatch.is_patched() is True

    PygmentsPatch.restore()
    assert PygmentsPatch.is_patched() is False

def test_patch_after_restore_works(clean_pygments_state):
    """Test patch can be reapplied after restoration."""
    PygmentsPatch.apply()
    PygmentsPatch.restore()

    result = PygmentsPatch.apply()
    assert result is True
    assert PygmentsPatch.is_patched() is True
```

### Verification
```bash
pytest tests/unit/rendering/test_pygments_patch.py -v
# Should show 5+ tests passing with full coverage
```

### Commit
```bash
git add tests/unit/rendering/test_pygments_patch.py
git commit -m "tests(rendering): restore full Pygments patch coverage with proper fixtures; fix syntax error without weakening assertions"
```

---

## Phase 2: Medium Priority - Native HTML Parser 🟡

**Priority**: MEDIUM - Can defer to follow-up PR if time-constrained  
**Estimated Time**: 60-90 minutes  
**Files**: `bengal/rendering/parsers/native_html.py`

### Problem
Toggle-based state tracking is fragile:
- Won't handle nested `<code>` or `<pre>` blocks
- Fails on malformed HTML (unclosed tags)
- Minimal implementation that barely satisfies current tests

### Solution Options

#### Option A: Document as Test-Only (Quick - 15 min)
**Recommended if time-constrained**

1. Add prominent warning to class docstring:
```python
class NativeHTMLParser(HTMLParser):
    """
    Stdlib HTML parser for validation. Mimics bs4 for decompose and get_text.

    ⚠️  TEST/VALIDATION ONLY
    ============================
    This parser uses simplified state tracking and is NOT suitable for:
    - Nested code/pre blocks
    - Malformed HTML
    - Production HTML parsing

    Use BeautifulSoup4 or lxml for production parsing.
    Primarily used in test fixtures and basic link validation.
    """
```

2. Add module-level constant:
```python
# native_html.py (top of file)
"""
Native HTML parser for testing and simple validation.

⚠️  This is a simplified parser for test fixtures. Use bs4/lxml for production.
"""

_PARSER_PURPOSE = "test-only"  # Flag for documentation
```

3. Update factory to log warning:
```python
# factory.py
def get_html_parser(backend: str | None = None) -> callable:
    if backend == ParserBackend.NATIVE:
        logger.warning(
            "Using NativeHTMLParser (test-only). "
            "Install beautifulsoup4 for robust parsing."
        )
        return lambda content: NativeHTMLParser().feed(content)
```

**Verification**: Check that documentation is clear in code review

**Commit**:
```bash
git add bengal/rendering/parsers/native_html.py bengal/rendering/parsers/factory.py
git commit -m "docs(rendering): mark NativeHTMLParser as test-only; warn of limitations (nested blocks, malformed HTML)"
```

#### Option B: Implement Proper Stack-Based Parser (Robust - 90 min)
**Defer to follow-up PR unless critical**

1. Replace toggle with stack:
```python
class NativeHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.document: list[str] = []
        self.code_block_stack: list[str] = []  # Track nesting

    def handle_starttag(self, tag, attrs):
        if tag in ("code", "pre"):
            self.code_block_stack.append(tag)
        if not self.code_block_stack:
            self.document.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if tag in ("code", "pre") and self.code_block_stack:
            if self.code_block_stack[-1] == tag:
                self.code_block_stack.pop()
        if not self.code_block_stack:
            self.document.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.code_block_stack:
            self.document.append(data)
```

2. Add comprehensive tests:
```python
def test_native_parser_nested_code_blocks():
    parser = NativeHTMLParser()
    html = "<p>Text <code>outer <code>nested</code></code> more</p>"
    parser.feed(html)
    # Verify correct handling
```

**Verification**: Run full test suite + new edge case tests

**Commit**: Separate PR - "refactor(rendering): implement stack-based state tracking in NativeHTMLParser for nested block support"

### Recommendation
**Choose Option A** for this PR (document limitations). File follow-up issue for Option B if native parser sees production use.

---

## Phase 3: Low Priority - Incremental Test Code Documentation 🟢

**Priority**: LOW - Document before merge, refactor optional  
**Estimated Time**: 30 minutes  
**Files**: `bengal/orchestration/incremental.py`

### Problem
Test-specific code lives in production class:
- `process()` method added for test bridge
- `_write_output()` writes placeholder "Updated" content
- No clear indication these are not production code paths

### Solution

#### Step 1: Add Prominent Documentation (15 min)
```python
def process(self, change_type: str, changed_paths: set) -> None:
    """
    Bridge-style process for testing incremental invalidation.

    ⚠️  TEST BRIDGE ONLY
    ========================
    This method is a lightweight adapter used in tests to simulate an
    incremental pass without invoking the entire site build orchestrator.

    - Writes placeholder output ("Updated") for verification
    - Does not perform full rendering or asset processing
    - Use full_build() or run() for production builds

    Primarily consumed by:
    - tests/integration/test_full_to_incremental_sequence.py
    - bengal/orchestration/full_to_incremental.py (test bridge)

    Args:
        change_type: One of "content", "template", "config"
        changed_paths: Paths that changed (ignored for config)
    """
```

#### Step 2: Add Runtime Warning (10 min)
```python
def process(self, change_type: str, changed_paths: set) -> None:
    """..."""
    if not self.tracker:
        raise RuntimeError("Tracker not initialized - call initialize() first")

    # Warn if called outside test context
    import sys
    if "pytest" not in sys.modules:
        logger.warning(
            "IncrementalOrchestrator.process() is a test bridge. "
            "Use full_build() for production."
        )

    # ... rest of implementation
```

#### Step 3: Optional - Move to Test Helper (Future PR - 45 min)
**Defer unless significant production confusion occurs**

Create `tests/helpers/incremental_bridge.py`:
```python
class IncrementalTestBridge:
    """Test-specific bridge for incremental build testing."""

    def __init__(self, orchestrator: IncrementalOrchestrator):
        self.orch = orchestrator

    def process_change(self, change_type: str, changed_paths: set):
        """Simulate incremental change for testing."""
        # Move process() logic here
```

Update tests to use bridge:
```python
from tests.helpers.incremental_bridge import IncrementalTestBridge

bridge = IncrementalTestBridge(orchestrator)
bridge.process_change("content", {changed_file})
```

### Recommendation
**Do Steps 1-2** for this PR. File follow-up issue for Step 3 if test/prod separation becomes critical.

### Verification
```bash
# Check documentation renders clearly
grep -A 10 "TEST BRIDGE ONLY" bengal/orchestration/incremental.py
```

### Commit
```bash
git add bengal/orchestration/incremental.py
git commit -m "docs(orchestration): mark IncrementalOrchestrator.process() as test bridge with runtime warning; clarify production vs test usage"
```

---

## Phase 4: Cleanup - Mark Incomplete Stubs 🟢

**Priority**: LOW - Prevent confusion  
**Estimated Time**: 15 minutes  
**Files**: `bengal/rendering/plugins/tables.py`, `bengal/core/page/cascade.py`

### Problem
Skeletal implementations staged without clear WIP markers.

### Solution

#### TablePlugin (5 min)
```python
class TablePlugin:
    """
    Modular table rendering for directives.

    ⚠️  WIP: Skeleton implementation for REN-002 fix.
    TODO: Complete render_table() with actual HTML generation.
    """

    @staticmethod
    def render_table(data: dict, table_id: str | None = None) -> str:
        # TODO: Implement full table rendering
        # Current: placeholder for multi-table ID isolation
        if not table_id:
            table_id = f"data-table-{uuid.uuid4().hex[:8]}"

        # PLACEHOLDER: Replace with actual table HTML
        return f'<div class="bengal-data-table-wrapper" data-table-id="{table_id}">TODO: Render table</div>'
```

#### CascadeScope (5 min)
```python
class CascadeScope:
    """
    Metadata cascade with depth limiting to prevent leaks.

    ⚠️  WIP: Prepared for ORC-003 fix (nested section metadata leak).
    TODO: Integrate into Section.apply_cascade() and add tests.
    """
```

### Verification
Search for TODO markers:
```bash
grep -r "TODO.*Render table\|TODO.*Integrate" bengal/
```

### Commit
```bash
git add bengal/rendering/plugins/tables.py bengal/core/page/cascade.py
git commit -m "docs: mark TablePlugin and CascadeScope as WIP with TODO markers for incomplete implementations"
```

---

## Execution Plan

### Sequence
1. **Phase 1** (Critical) - Complete first, blocks merge
2. **Phase 2** (Medium) - Option A (document-only), defer Option B
3. **Phase 3** (Low) - Steps 1-2 only, defer Step 3
4. **Phase 4** (Cleanup) - Quick documentation pass

### Time Breakdown
- Phase 1: 45 min (required)
- Phase 2: 15 min (Option A - document)
- Phase 3: 30 min (Steps 1-2)
- Phase 4: 15 min
- **Total**: ~1.75 hours for merge-ready state

### Testing Strategy
After each phase:
```bash
# Run affected tests
pytest tests/unit/rendering/test_pygments_patch.py -v
pytest tests/integration/test_full_to_incremental_sequence.py -v

# Full suite verification
./scripts/run-tests.sh -v --tb=short -x
```

### Final Commit Message (After All Phases)
```bash
git add -A
git commit -m "fix(tests): restore Pygments patch coverage, document test-only code (native parser, incremental bridge), mark WIP stubs

- tests/rendering: Fix syntax error with proper fixtures, restore full assertion coverage
- parsers: Mark NativeHTMLParser as test-only with limitation warnings
- orchestration: Document IncrementalOrchestrator.process() as test bridge
- plugins/page: Add WIP markers to TablePlugin and CascadeScope skeletons

Addresses CODE_REVIEW_2025-10-16.md findings before merge."
```

---

## Success Criteria

- [ ] Pygments tests pass with full coverage (5+ test cases)
- [ ] All test-only code has prominent warnings
- [ ] WIP stubs clearly marked
- [ ] No new linter errors
- [ ] Full test suite passes: `./scripts/run-tests.sh`
- [ ] Documentation searchable: `grep "TEST.*ONLY\|WIP" bengal/**/*.py`

---

## Follow-Up Issues (Future PRs)

1. **Issue**: Implement stack-based NativeHTMLParser
   - **Labels**: enhancement, rendering, tests
   - **Priority**: P2 (if parser sees production use)
   - **Estimate**: 2 hours

2. **Issue**: Extract test bridge to tests/helpers/
   - **Labels**: refactor, tests, tech-debt
   - **Priority**: P3 (nice-to-have)
   - **Estimate**: 1 hour

3. **Issue**: Complete TablePlugin implementation
   - **Labels**: bug, REN-002, rendering
   - **Priority**: P1 (blocks multi-table support)
   - **Estimate**: 3 hours

4. **Issue**: Integrate CascadeScope into Section
   - **Labels**: bug, ORC-003, core
   - **Priority**: P1 (blocks nested metadata fix)
   - **Estimate**: 2 hours

---

## Changelog Entry (After Completion)

Add to `CHANGELOG.md` under `[Unreleased]`:

```markdown
### Fixed
- Restored full test coverage for Pygments patch (removed weakened assertions)
- Improved documentation for test-only code paths (native parser, incremental bridge)

### Documentation
- Marked NativeHTMLParser limitations (nested blocks not supported)
- Added runtime warnings for test bridge methods in production context
- Clarified WIP status of TablePlugin and CascadeScope

### Technical Debt
- Identified follow-up work: stack-based HTML parser, test helper extraction
```

---

## Completion

After all phases:
1. Run full test suite: `./scripts/run-tests.sh`
2. Update `CHANGELOG.md`
3. Move this plan to `plan/completed/`
4. Move `CODE_REVIEW_2025-10-16.md` to `plan/completed/`
5. Update `plan/active/BUG_TRACKER_2025-10-15.md` with fixed issues
6. Push branch for review

**Status**: Ready to execute  
**Blocked by**: None  
**Blocks**: Branch merge to main
