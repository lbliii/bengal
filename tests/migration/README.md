# Migration Tests

This directory contains tests for verifying HTML parity between the Bengal/mistune and Patitas directive implementations.

## Purpose

These tests ensure that migrating from mistune to Patitas produces **identical HTML output** for all directives. This is critical for a seamless migration without breaking existing documentation.

## Test Structure

```
tests/migration/
├── __init__.py
├── conftest.py                  # Fixtures and pytest hooks
├── test_directive_parity.py     # Main parity tests (40+ cases)
├── test_directive_edge_cases.py # Edge case tests
├── golden_files/                # Expected HTML output
│   └── *.html
└── README.md                    # This file
```

## Running Tests

### Run All Migration Tests

```bash
pytest tests/migration/ -v
```

### Run Only Parity Tests

```bash
pytest tests/migration/test_directive_parity.py -v
```

### Run Only Edge Case Tests

```bash
pytest tests/migration/test_directive_edge_cases.py -v
```

### Run a Specific Test

```bash
pytest tests/migration/test_directive_parity.py::test_html_parity[note_basic] -v
```

## Golden Files

Golden files contain expected HTML output for Patitas directive rendering.

### Generate/Update Golden Files

```bash
pytest tests/migration/ --update-golden-files
```

This will:
1. Run Patitas rendering for each test case
2. Save output to `golden_files/<test_name>.html`
3. Skip the test (since we're updating, not comparing)

### Compare Against Golden Files

```bash
pytest tests/migration/test_directive_parity.py::test_golden_file -v
```

## Test Categories

### Parity Tests (`test_html_parity`)

Compare Patitas output directly against mistune output. Tests fail if there are any semantic HTML differences.

### Golden File Tests (`test_golden_file`)

Compare Patitas output against saved golden files. Useful for:
- CI/CD verification
- Detecting unintended changes
- Historical reference

### Edge Case Tests

Handle unusual inputs:
- Empty content
- Special characters in titles
- Unicode content
- Very long content
- Deeply nested directives
- Malformed syntax

## HTML Normalization

The `normalize_html()` function handles:
- Whitespace normalization (outside pre/code)
- Attribute order sorting
- Self-closing tag standardization
- Blank line removal

This allows comparison of semantically equivalent HTML even with different formatting.

## Fixtures

| Fixture | Description |
|---------|-------------|
| `render_with_mistune` | Render markdown using mistune backend |
| `render_with_patitas` | Render markdown using Patitas backend |
| `assert_html_equal` | Assert two HTML strings are semantically equal |
| `compare_backends` | Compare output from both backends |
| `golden_file_path` | Path to golden file for current test |
| `update_golden_files` | True if `--update-golden-files` flag passed |

## Adding New Test Cases

1. Add test case tuple to `DIRECTIVE_TEST_CASES` in `test_directive_parity.py`:

```python
(
    "my_new_test",
    """\
:::{note} Title
Content here.
:::
""",
),
```

2. Run tests to verify parity:

```bash
pytest tests/migration/ -k my_new_test -v
```

3. Generate golden file:

```bash
pytest tests/migration/ --update-golden-files -k my_new_test
```

## Exit Criteria

Phase A.1 is complete when:
- [ ] All 40+ Phase A directive test cases pass
- [ ] Zero HTML diff between mistune and Patitas rendering
- [ ] Golden files committed to version control
- [ ] Edge case tests pass without crashes

## Related Documents

- RFC: `plan/drafted/rfc-patitas-bengal-directive-migration.md`
- Patitas Parser: `bengal/rendering/parsers/patitas/`
- Mistune Parser: `bengal/rendering/parsers/mistune/`
