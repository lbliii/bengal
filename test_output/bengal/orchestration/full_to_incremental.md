# full_to_incremental

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/orchestration/full_to_incremental.py

Bridge helpers for transitioning from full builds to incremental runs.

⚠️  TEST UTILITIES ONLY
========================
These utilities are primarily used in tests to simulate incremental passes
without invoking the full BuildOrchestrator.

**Not for production use:**
- Writes placeholder output for test verification
- Skips full rendering pipeline
- Use BuildOrchestrator.run() for production incremental builds

**Primary consumers:**
- tests/integration/test_full_to_incremental_sequence.py
- Test scenarios validating incremental build flows

*Note: Template has undefined variables. This is fallback content.*
