# Future Refactor: Move Test Helpers to Dedicated Module

**Status**: 📋 Deferred - Future PR  
**Priority**: Low  
**Effort**: ~30 minutes  
**Related**: CODE_REVIEW_2025-10-16.md (Item #3: Incremental Process Method)

## Context

The `IncrementalOrchestrator` class in `bengal/orchestration/incremental.py` contains test-specific methods:
- `process(change_type: str, changed_paths: set)` - Test bridge for simulating incremental invalidation
- `_write_output(path: Path, context: BuildContext)` - Helper that writes diagnostic test output

These are clearly documented as test-only (with `⚠️ TEST BRIDGE ONLY` warnings), but ideally should live in `tests/helpers/` instead of production code.

## Current State (v0.1.2)

✅ Already handled well:
- Clear documentation with `⚠️` warnings
- Runtime guard: warns if called outside pytest
- Diagnostic markers added (timestamp + source/output paths)
- Tests don't depend on internals, just call the methods

⚠️ Architectural concern:
- Test code lives in production module
- Slightly increases cognitive load when reading orchestrator
- Non-standard to have test helpers in prod code

## Proposed Future State

Move to `tests/helpers/incremental_bridge.py`:

```python
"""Test bridge for incremental orchestrator testing."""
from datetime import datetime
from pathlib import Path
from bengal.utils.build_context import BuildContext
from bengal.orchestration.incremental import IncrementalOrchestrator

class IncrementalTestBridge:
    """Lightweight adapter for testing incremental invalidation without full orchestrator."""

    def __init__(self, site):
        self.orch = IncrementalOrchestrator(site)
        self.orch.initialize(enabled=True)

    def process(self, change_type: str, changed_paths: set) -> None:
        """Process incremental change for testing."""
        # (Move process() logic here)

    @staticmethod
    def write_test_output(site, path: Path, context: BuildContext) -> None:
        """Write diagnostic placeholder for test verification."""
        # (Move _write_output() logic here)
```

Then update tests:
```python
from tests.helpers.incremental_bridge import IncrementalTestBridge

bridge = IncrementalTestBridge(site)
bridge.process("content", changed_paths)
```

## Why Defer

1. **Working well now**: Current implementation is documented and functional
2. **Low impact**: Only 2 methods, easy to refactor later
3. **No blocker**: Not preventing any development or testing
4. **Can batch**: Pair with other test infrastructure improvements

## When to Revisit

- If adding more test bridges for other orchestrators
- If test module reorganization is happening
- During next stability/architecture pass

## Related Files

- `bengal/orchestration/incremental.py:388-482` - Current test methods
- `tests/integration/test_full_to_incremental_sequence.py` - Primary consumer
- `bengal/orchestration/full_to_incremental.py` - Bridge helper (public entry point)

## Notes

The diagnostic output improvement (commit `f33bb3c`) makes the current approach even more acceptable to defer - the output is now clearly marked as test-only with useful debugging info.
