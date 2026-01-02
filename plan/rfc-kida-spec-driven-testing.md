# RFC: Kida Spec-Driven Testing Framework

**Status**: Draft  
**Author**: Bengal Team  
**Created**: 2026-01-02  
**Target**: Kida 1.0  
**Reference**: [Patitas CommonMark Compliance](rfc-patitas-commonmark-compliance.md)

## Executive Summary

To ensure Kida becomes the most reliable and Jinja2-compatible template engine for free-threaded Python, we propose moving from traditional imperative unit tests to a **declarative, spec-driven testing framework**.

By adopting the same patterns used in our **Patitas** (Markdown) parser, we can decouple test data from test logic, enable precise compatibility metrics, and drastically reduce the cost of adding new features.

**Scope**: This RFC targets **pure template rendering tests** (template + context → output). Complex scenarios requiring Python fixtures (thread safety, error handling, inheritance chains) remain as traditional Python tests.

## Background

### Current State

Kida has **34 test files** with traditional imperative tests:

| Category | Files | Tests (approx) |
|----------|-------|----------------|
| Basic/Core | 8 | ~150 |
| Match/Patterns | 4 | ~80 |
| Filters/Expressions | 4 | ~60 |
| Loops/Conditionals | 4 | ~70 |
| Inheritance/Scoping | 5 | ~90 |
| Edge Cases/Errors | 5 | ~80 |
| Thread Safety/Async | 4 | ~40 |
| **Total** | **34** | **~570** |

### Current Limitations

1. **High Boilerplate**: Every test requires `Environment` setup and manual assertions:
   ```python
   def test_render_filter(self):
       env = Environment()
       template = env.from_string("{{ name | upper }}")
       result = template.render(name="hello")
       assert result == "HELLO"
   ```

2. **Fragile Comparisons**: Tests rely on exact string matches, failing on trivial whitespace differences.

3. **Opacity of Compliance**: No quantified metric for Jinja2 compatibility. Cannot answer: "What percentage of Jinja2 features does Kida support?"

4. **Duplicate Logic**: Similar test patterns repeated across files without shared infrastructure.

### Proven Pattern: Patitas CommonMark Compliance

The Patitas parser uses spec-driven testing with excellent results:

- **652 spec examples** loaded from JSON
- **Baseline tracking**: 42.4% → targeting 97%
- **Parametrized tests**: One test function, hundreds of cases
- **HTML normalization**: Semantic comparison, not string equality
- **Clear roadmap**: Section-by-section compliance metrics

## Proposal: The Kida Spec (`kida_spec.json`)

### 1. Spec Schema Definition

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["section", "example", "template", "expected", "category"],
    "properties": {
      "section": {
        "type": "string",
        "description": "Feature category (e.g., 'Filters', 'Pattern Matching')"
      },
      "example": {
        "type": "integer",
        "description": "Unique example number within section"
      },
      "template": {
        "type": "string",
        "description": "Kida/Jinja2 template source"
      },
      "context": {
        "type": "object",
        "description": "Variables passed to template.render()",
        "default": {}
      },
      "expected": {
        "type": "string",
        "description": "Expected rendered output"
      },
      "category": {
        "type": "string",
        "enum": ["kida-native", "jinja2-compat"],
        "description": "Feature origin for compliance tracking"
      },
      "output_type": {
        "type": "string",
        "enum": ["text", "html", "json"],
        "default": "text",
        "description": "Output type for normalization strategy"
      },
      "autoescape": {
        "type": "boolean",
        "default": false,
        "description": "Whether autoescape is enabled"
      },
      "jinja2_version": {
        "type": ["string", "null"],
        "default": null,
        "description": "Jinja2 version this test was extracted from (null for kida-native)"
      },
      "notes": {
        "type": "string",
        "description": "Optional notes about the test case"
      }
    }
  }
}
```

### 2. Example Spec Entries

```json
[
  {
    "section": "Pattern Matching",
    "example": 1,
    "template": "{% match x %}{% case 1 %}One{% case _ %}Other{% end %}",
    "context": {"x": 1},
    "expected": "One",
    "category": "kida-native",
    "output_type": "text",
    "notes": "Kida-only feature, no Jinja2 equivalent"
  },
  {
    "section": "Filters",
    "example": 24,
    "template": "{{ name | upper }}",
    "context": {"name": "bengal"},
    "expected": "BENGAL",
    "category": "jinja2-compat",
    "jinja2_version": "3.1.2"
  },
  {
    "section": "Conditionals",
    "example": 5,
    "template": "{% if show %}<div>visible</div>{% endif %}",
    "context": {"show": true},
    "expected": "<div>visible</div>",
    "category": "jinja2-compat",
    "output_type": "html",
    "autoescape": true
  },
  {
    "section": "Filters",
    "example": 30,
    "template": "{{ data | tojson }}",
    "context": {"data": {"a": 1, "b": 2}},
    "expected": "{\"a\": 1, \"b\": 2}",
    "category": "jinja2-compat",
    "output_type": "json"
  }
]
```

### 3. Output Normalization Strategy

Different output types require different normalization:

| Output Type | Normalization Rules |
|-------------|---------------------|
| `text` | Strip leading/trailing whitespace, normalize line endings |
| `html` | Attribute ordering, self-closing tags, whitespace in non-pre blocks |
| `json` | Parse and re-serialize with sorted keys |

**Implementation**: Create `tests/_testing/kida_normalize.py`:

```python
"""Kida output normalization for spec-driven testing."""

import json
import re


def normalize_output(output: str, output_type: str = "text") -> str:
    """Normalize template output for comparison.

    Args:
        output: Raw template output
        output_type: One of "text", "html", "json"

    Returns:
        Normalized output string
    """
    match output_type:
        case "text":
            return normalize_text(output)
        case "html":
            return normalize_html(output)
        case "json":
            return normalize_json(output)
        case _:
            return normalize_text(output)


def normalize_text(text: str) -> str:
    """Normalize plain text output."""
    result = text.strip()
    result = result.replace("\r\n", "\n")
    # Collapse multiple blank lines to single
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result


def normalize_html(html: str) -> str:
    """Normalize HTML for semantic comparison.

    Handles:
    - Attribute ordering (alphabetical)
    - Self-closing tag style (<br> vs <br />)
    - Whitespace in non-preformatted blocks
    """
    result = html.strip()

    # Normalize self-closing tags: <br /> -> <br>
    result = re.sub(r"<(br|hr|img|input|meta|link)(\s[^>]*)?\s*/?>", r"<\1\2>", result)

    # Normalize empty self-closing: <tag /> -> <tag>
    result = re.sub(r"\s*/>", ">", result)

    # Normalize line endings
    result = result.replace("\r\n", "\n")

    # Sort attributes alphabetically for consistent comparison
    def sort_attrs(match: re.Match[str]) -> str:
        tag = match.group(1)
        attrs_str = match.group(2)
        if not attrs_str:
            return match.group(0)

        attr_pattern = re.compile(r'(\w+)=("[^"]*"|\'[^\']*\'|[^\s>]+)')
        attrs = attr_pattern.findall(attrs_str)
        if not attrs:
            return match.group(0)

        attrs.sort(key=lambda x: x[0])
        sorted_attrs = " ".join(f"{k}={v}" for k, v in attrs)
        return f"<{tag} {sorted_attrs}>"

    result = re.sub(r"<(\w+)(\s[^>]+)>", sort_attrs, result)

    return result


def normalize_json(json_str: str) -> str:
    """Normalize JSON for comparison."""
    try:
        data = json.loads(json_str)
        return json.dumps(data, sort_keys=True, separators=(", ", ": "))
    except json.JSONDecodeError:
        # Fall back to text normalization if not valid JSON
        return normalize_text(json_str)
```

### 4. Test Runner Implementation

```python
# tests/rendering/kida/test_kida_spec.py
"""Kida Spec-Driven Tests.

Runs declarative test cases from kida_spec.json against the Kida engine.

Usage:
    # Run all spec tests
    pytest tests/rendering/kida/test_kida_spec.py -v

    # Run specific section
    pytest tests/rendering/kida/test_kida_spec.py -k "Filters"

    # Run single example
    pytest tests/rendering/kida/test_kida_spec.py -k "example_024"

    # Run only Jinja2 compatibility tests
    pytest tests/rendering/kida/test_kida_spec.py -k "jinja2_compat"
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from bengal.rendering.kida import Environment
from tests._testing.kida_normalize import normalize_output

if TYPE_CHECKING:
    pass


# Load the Kida spec
SPEC_PATH = Path(__file__).parent / "kida_spec.json"
SPEC_TESTS: list[dict[str, Any]] = json.loads(SPEC_PATH.read_text())

# Track known issues - skip entire sections
KNOWN_ISSUES: dict[str, str] = {
    # Example: "Macros": "Not yet implemented"
}

# Track specific examples expected to fail
XFAIL_EXAMPLES: dict[int, str] = {
    # Example: 42: "Known bug with nested match"
}


def pytest_generate_tests(metafunc: Any) -> None:
    """Generate test parameters from spec examples."""
    if "example" in metafunc.fixturenames:
        ids = [
            f"example_{ex['example']:03d}_{ex['section'].replace(' ', '_')}_{ex['category']}"
            for ex in SPEC_TESTS
        ]
        metafunc.parametrize("example", SPEC_TESTS, ids=ids)


class TestKidaSpec:
    """Kida specification tests."""

    @pytest.fixture
    def env(self) -> Environment:
        """Create a fresh Environment for each test."""
        return Environment()

    def test_kida_example(self, env: Environment, example: dict[str, Any]) -> None:
        """Test a single Kida spec example."""
        template_src = example["template"]
        context = example.get("context", {})
        expected = example["expected"]
        example_num = example["example"]
        section = example["section"]
        output_type = example.get("output_type", "text")
        autoescape = example.get("autoescape", False)

        # Check for known issues at section level
        if section in KNOWN_ISSUES:
            pytest.skip(f"Section '{section}': {KNOWN_ISSUES[section]}")

        # Check for specific xfail examples
        if example_num in XFAIL_EXAMPLES:
            pytest.xfail(XFAIL_EXAMPLES[example_num])

        # Configure environment
        if autoescape:
            env = Environment(autoescape=True)

        # Compile and render
        template = env.from_string(template_src)
        actual = template.render(**context)

        # Normalize and compare
        expected_norm = normalize_output(expected, output_type)
        actual_norm = normalize_output(actual, output_type)

        assert actual_norm == expected_norm, (
            f"\n\nExample {example_num} ({section}) failed:\n"
            f"\n--- Template ---\n{template_src!r}\n"
            f"\n--- Context ---\n{context!r}\n"
            f"\n--- Expected ---\n{expected!r}\n"
            f"\n--- Actual ---\n{actual!r}\n"
            f"\n--- Expected (normalized) ---\n{expected_norm!r}\n"
            f"\n--- Actual (normalized) ---\n{actual_norm!r}\n"
        )


class TestSpecMetrics:
    """Tests to track compliance metrics."""

    def test_total_examples(self) -> None:
        """Verify spec is loaded correctly."""
        assert len(SPEC_TESTS) > 0, "Spec file is empty"

    def test_example_structure(self) -> None:
        """Verify all examples have required fields."""
        required = {"section", "example", "template", "expected", "category"}
        for ex in SPEC_TESTS:
            missing = required - set(ex.keys())
            assert not missing, f"Example {ex.get('example')} missing: {missing}"

    def test_categories_valid(self) -> None:
        """Verify all categories are valid."""
        valid = {"kida-native", "jinja2-compat"}
        for ex in SPEC_TESTS:
            assert ex["category"] in valid, f"Invalid category: {ex['category']}"


def generate_compliance_report() -> str:
    """Generate compliance report by section and category."""
    env = Environment()
    results: dict[str, dict[str, dict[str, int]]] = {}

    for example in SPEC_TESTS:
        section = example["section"]
        category = example["category"]

        if section not in results:
            results[section] = {
                "kida-native": {"passed": 0, "failed": 0},
                "jinja2-compat": {"passed": 0, "failed": 0},
            }

        if section in KNOWN_ISSUES:
            continue

        try:
            template = env.from_string(example["template"])
            actual = template.render(**example.get("context", {}))
            output_type = example.get("output_type", "text")

            expected_norm = normalize_output(example["expected"], output_type)
            actual_norm = normalize_output(actual, output_type)

            if expected_norm == actual_norm:
                results[section][category]["passed"] += 1
            else:
                results[section][category]["failed"] += 1
        except Exception:
            results[section][category]["failed"] += 1

    # Generate report
    lines = [
        "# Kida Spec Compliance Report",
        "",
        "## By Section",
        "",
        "| Section | Kida-Native | Jinja2-Compat | Total |",
        "|---------|-------------|---------------|-------|",
    ]

    total_kida_passed = 0
    total_kida_total = 0
    total_jinja_passed = 0
    total_jinja_total = 0

    for section, cats in sorted(results.items()):
        kp = cats["kida-native"]["passed"]
        kf = cats["kida-native"]["failed"]
        jp = cats["jinja2-compat"]["passed"]
        jf = cats["jinja2-compat"]["failed"]

        kt = kp + kf
        jt = jp + jf

        krate = f"{kp}/{kt}" if kt > 0 else "N/A"
        jrate = f"{jp}/{jt}" if jt > 0 else "N/A"
        total = f"{kp + jp}/{kt + jt}"

        total_kida_passed += kp
        total_kida_total += kt
        total_jinja_passed += jp
        total_jinja_total += jt

        lines.append(f"| {section} | {krate} | {jrate} | {total} |")

    lines.extend([
        "",
        "## Summary",
        "",
        f"**Kida-Native**: {total_kida_passed}/{total_kida_total} "
        f"({total_kida_passed/total_kida_total*100:.1f}%)" if total_kida_total > 0 else "N/A",
        f"**Jinja2-Compat**: {total_jinja_passed}/{total_jinja_total} "
        f"({total_jinja_passed/total_jinja_total*100:.1f}%)" if total_jinja_total > 0 else "N/A",
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_compliance_report())
```

### 5. Compliance Metrics & Baselines

#### Category Definitions

| Category | Description | Source |
|----------|-------------|--------|
| `kida-native` | Features unique to Kida (match, pipelines, let/export) | Manual spec creation |
| `jinja2-compat` | Features matching Jinja2 behavior | Extracted from Jinja2 3.1.x tests |

#### Baseline Targets

| Metric | Baseline | Target | Notes |
|--------|----------|--------|-------|
| Kida-Native Pass Rate | TBD | 100% | All native features must work |
| Jinja2-Compat Pass Rate | TBD | 95% | Allow documented deviations |
| Total Spec Examples | 0 | 400+ | ~200 kida-native, ~200 jinja2-compat |

## Implementation Plan

### Phase 1: Infrastructure (Sprint 1)

**Goal**: Create spec runner and establish initial baseline

**Tasks**:
1. Create `tests/_testing/kida_normalize.py` with output normalization
2. Create `tests/rendering/kida/test_kida_spec.py` spec runner
3. Create initial `kida_spec.json` with schema validation
4. Migrate 10-20 simple tests from `test_kida_basic.py` as proof of concept

**Deliverables**:
- [ ] Normalization module with text/html/json support
- [ ] Parametrized test runner with baseline reporting
- [ ] Initial spec with ~50 examples
- [ ] CI integration for compliance metrics

**Exit Criteria**: Spec runner works, initial baseline established

---

### Phase 2: Kida-Native Migration (Sprint 2)

**Goal**: Convert all Kida-native feature tests to spec

**Files to migrate** (convertible tests only):
- `test_kida_match.py` → Pattern matching examples
- `test_kida_pipeline.py` → Pipeline syntax examples
- `test_kida_modern_syntax.py` → let/export examples

**Migration Criteria**:

| Migrate to Spec | Keep as Python |
|-----------------|----------------|
| Simple template → output | Thread safety tests |
| No fixtures required | Error handling (expected exceptions) |
| Deterministic output | Tests requiring `env_with_loader` fixture |
| Single render call | Inheritance chain tests |
| | Async/concurrent tests |

**Tasks**:
1. Audit each test file for migratable tests
2. Convert ~100 tests to spec entries
3. Add `expected_error` support for parse/render errors
4. Validate no coverage loss (run both old and new)

**Deliverables**:
- [ ] ~150 kida-native spec entries
- [ ] Error testing support in spec format
- [ ] Migration audit document

**Exit Criteria**: All simple kida-native tests in spec, complex tests documented

---

### Phase 3: Jinja2 Test Analysis (Sprint 3)

**Goal**: Analyze Jinja2 test suite for extractable tests

**Approach**:
1. Clone Jinja2 3.1.x repository
2. Analyze `tests/` directory structure
3. Categorize tests by extractability

**Jinja2 Test Categories**:

| Category | Extractable? | Example |
|----------|--------------|---------|
| Simple render tests | ✅ Yes | `test_filters.py::test_upper` |
| Loader tests | ❌ No | Require filesystem fixtures |
| Extension tests | ❌ No | Require custom extensions |
| Error tests | ⚠️ Partial | Can extract expected error type |
| Sandbox tests | ❌ No | Security context required |

**Tasks**:
1. Write extraction script for simple Jinja2 tests
2. Document Jinja2 version pinned for baseline (3.1.2)
3. Create mapping of Jinja2 test → spec entry
4. Identify intentional Kida deviations

**Deliverables**:
- [ ] Jinja2 test extractability report
- [ ] Extraction script (`scripts/extract_jinja2_tests.py`)
- [ ] List of intentional deviations

**Exit Criteria**: Clear picture of what can be extracted from Jinja2

---

### Phase 4: Jinja2 Compatibility Baseline (Sprint 4)

**Goal**: Import extractable Jinja2 tests and establish baseline

**Tasks**:
1. Run extraction script on Jinja2 3.1.2 tests
2. Add ~200 jinja2-compat spec entries
3. Run full spec, document failures
4. Triage failures into: bug, intentional deviation, not-yet-implemented

**Deliverables**:
- [ ] ~200 jinja2-compat spec entries
- [ ] Jinja2 Compatibility Baseline Report
- [ ] Prioritized fix list

**Exit Criteria**: Baseline Jinja2 compatibility metric established

---

### Phase 5: Legacy Test Decommissioning (Sprint 5)

**Goal**: Remove redundant Python tests, keep necessary ones

**Approach**:
1. For each migrated test, verify spec coverage
2. Mark Python test as `@pytest.mark.redundant` temporarily
3. Run both, confirm no coverage loss
4. Delete redundant tests

**Tests to Keep as Python**:

| File | Reason |
|------|--------|
| `test_kida_thread_safety.py` | Concurrent execution |
| `test_kida_async_features.py` | Async/await patterns |
| `test_kida_error_handling.py` | Exception assertions |
| `test_kida_inheritance.py` | Multi-file templates |
| `test_kida_bytecode_cache.py` | Cache behavior |
| `test_kida_auto_reload.py` | File watching |

**Deliverables**:
- [ ] Redundant tests removed
- [ ] Python test files reduced from 34 to ~12
- [ ] No coverage regression

**Exit Criteria**: Clean test suite with no redundancy

---

### Phase 6: CI Integration & Reporting (Sprint 6)

**Goal**: Automated compliance tracking in CI

**Tasks**:
1. Add compliance report generation to CI
2. Create baseline tracking (store metrics over time)
3. Add PR checks for compliance regression
4. Generate visual compliance dashboard

**Deliverables**:
- [ ] CI job: `generate-kida-compliance-report`
- [ ] PR comment with compliance delta
- [ ] Historical baseline tracking
- [ ] Badge: "Jinja2 Compat: X%"

**Exit Criteria**: Compliance metrics visible in every PR

## Benefits

| Benefit | Before | After |
|---------|--------|-------|
| **Adding edge case** | Write Python function, setup, assertions | Add JSON object to spec |
| **Compliance visibility** | "We think it's compatible" | "95.2% Jinja2 compatible" |
| **Test maintenance** | Edit Python across 34 files | Edit single JSON file |
| **Flaky tests** | String equality fails on whitespace | Normalized comparison |
| **Onboarding** | Read 34 test files | Read spec.json + schema |

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Jinja2 tests not extractable** | Medium | Medium | Phase 3 analysis before commitment; accept lower extraction rate |
| **Normalization edge cases** | High | Low | Iterative refinement; add `output_type` field for fine-grained control |
| **Coverage regression** | Medium | High | Run both old and new tests in parallel before decommissioning |
| **Complex tests can't be JSON** | Certain | Low | Keep Python tests for complex scenarios; document criteria clearly |
| **Spec maintenance burden** | Low | Medium | Schema validation; IDE support for JSON editing |

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Spec examples | 400+ | Count entries in `kida_spec.json` |
| Kida-native pass rate | 100% | `pytest -k kida_native` |
| Jinja2-compat pass rate | 95% | `pytest -k jinja2_compat` |
| Python test files reduced | 34 → 12 | File count |
| Time to add edge case | <30 seconds | Manual timing |
| CI compliance report | Every PR | GitHub Actions |

## Appendix A: Test Migration Checklist

For each existing test file:

- [ ] Count total tests
- [ ] Identify migratable tests (simple render)
- [ ] Identify non-migratable tests (fixtures, errors, async)
- [ ] Create spec entries for migratable tests
- [ ] Verify spec tests pass
- [ ] Mark Python tests as redundant
- [ ] Run both, confirm same coverage
- [ ] Delete redundant Python tests
- [ ] Update test count tracking

## Appendix B: Intentional Deviations from Jinja2

Document here any intentional differences from Jinja2 behavior:

| Feature | Jinja2 Behavior | Kida Behavior | Rationale |
|---------|-----------------|---------------|-----------|
| `{% end %}` | Not supported | Alias for `{% endif %}` etc. | Cleaner syntax |
| `{% match %}` | Not supported | Pattern matching | Kida-native feature |
| `{% let %}` | Not supported | Persistent variable | Improved scoping |
| `{% export %}` | Not supported | Scope promotion | Improved scoping |
| Block scoping | Jinja2 scoping rules | Python-like scoping | More intuitive |

## Appendix C: Jinja2 Version Compatibility

**Pinned Version**: Jinja2 3.1.2 (latest stable as of 2026-01)

**Version-Specific Notes**:
- Jinja2 3.0 introduced async support (we test this separately)
- Jinja2 3.1 changed some whitespace handling
- Tests extracted from 3.1.x may not match 2.x behavior

**Future**: When Jinja2 3.2 releases, create new spec version and migration guide.

## References

- [Patitas CommonMark Compliance RFC](rfc-patitas-commonmark-compliance.md)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [Jinja2 Test Suite](https://github.com/pallets/jinja/tree/main/tests)
- [CommonMark Spec](https://spec.commonmark.org/) (pattern reference)
