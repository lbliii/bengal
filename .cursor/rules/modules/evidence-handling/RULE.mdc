---
description: Standard patterns for citing code evidence with file:line references across all Bengal rules
alwaysApply: false
---

# Evidence Handling

Standard patterns for citing source code, tests, and configuration as evidence. Used by all research, validation, and implementation rules.

**Works with**: `modules/types-as-contracts`, `modules/output-format`

---

## Core Principle

> **NEVER invent facts. Only make claims backed by code references (`file:line`).**

Every technical claim must be traceable to source code. This enables:
- Verification of claims
- Detection of drift when code changes
- Clear communication of findings

---

## File Reference Format

**Always use**: `path/to/file.py:45-52` format

### Rules

- Include full path relative to workspace root
- Include line numbers (single: `:45`, range: `:45-52`)
- Use backticks for code formatting
- Make paths copy-paste friendly

### Examples

```markdown
✅ CORRECT:
- `bengal/core/page/__init__.py:145`
- `tests/unit/test_page.py:23-45`
- `bengal.toml` (for config files, line optional)

❌ WRONG:
- `page.py` (missing path)
- `line 45` (not file:line format)
- `bengal/core/page/__init__.py` (missing line for specific claims)
```

---

## Evidence Trail Format

### Single Source

```markdown
**Evidence**: `bengal/core/site.py:145-150`
```

### Multiple Sources

```markdown
**Evidence**:
- Primary: `bengal/core/site.py:145` - Method signature
- Test: `tests/unit/test_site.py:89` - Behavior verified
- Config: `bengal.toml` schema - Default value
```

### In Structured Output (YAML)

```yaml
evidence:
  primary: "bengal/core/site.py:145 - description"
  supporting: ["tests/unit/test_site.py:89", "bengal.toml:12"]
  test_verification: "tests/integration/test_build.py:200"
```

---

## Evidence Types

| Type | Description | Weight |
|------|-------------|--------|
| `source_code` | Direct implementation | Highest |
| `test_verification` | Unit/integration tests | High |
| `configuration` | Config files, defaults | Medium |
| `documentation` | Docstrings, comments | Lower |
| `inferred` | Derived from context | Lowest |

---

## Code Citation Format

When citing source code, include context:

```markdown
**Evidence**: `bengal/core/site.py:145-150`

```python
def build(self, incremental: bool = False) -> None:
    """Build the site with optional incremental mode."""
    return BuildOrchestrator.build(self, incremental=incremental)
```

- Method signature confirms `incremental` parameter
- Delegates to `BuildOrchestrator` as expected
```

---

## 3-Path Validation

For **HIGH criticality** claims, validate via 3 independent paths:

### Path A: Source Code
Find the implementation:
```yaml
path_a:
  source: "Source code"
  location: "bengal/core/site.py:145-150"
  finding: "Method accepts incremental parameter"
  conclusion: ✅ Verified
```

### Path B: Tests
Find tests that verify the behavior:
```yaml
path_b:
  source: "Tests"
  location: "tests/unit/test_site.py:89-105"
  finding: "test_incremental_build verifies behavior"
  conclusion: ✅ Verified
```

### Path C: Config/Schema
Check if behavior is configurable:
```yaml
path_c:
  source: "Configuration"
  location: "bengal.toml schema"
  finding: "No config needed (API parameter)"
  conclusion: N/A
```

### Agreement Scoring

| Agreement | Confidence | Action |
|-----------|------------|--------|
| 3/3 agree | HIGH 🟢 | Ship it |
| 2/3 agree | MODERATE 🟡 | Flag disagreeing source |
| 1/3 or conflict | LOW 🔴 | Manual review required |

---

## Search Strategy

### Step 1: Semantic Search (Broad)

```yaml
tool: codebase_search
query: "How does incremental build work?"
target: ["bengal/"]
purpose: Find relevant modules
```

### Step 2: Symbol Search (Narrow)

```yaml
tool: grep
pattern: "def build\\("
path: "bengal/core/"
purpose: Find exact function definition
```

### Step 3: Read and Extract

```yaml
tool: read_file
target: "bengal/core/site.py"
lines: 140-160
purpose: Extract code with context
```

### Step 4: Cross-Reference Tests

```yaml
tool: grep
pattern: "test.*incremental.*build"
path: "tests/"
purpose: Find related tests
```

---

## Evidence Quality Indicators

### Match Quality

| Quality | Points | Criteria |
|---------|--------|----------|
| Exact Match | 40 | Direct code with file:line and excerpt |
| Strong Match | 30 | Code reference without full excerpt |
| Partial Match | 20 | Docstring or comment only |
| Inferred | 10 | Derived from context |
| No Match | 0 | No evidence found |

---

## Bengal-Specific Evidence Sources

### Core Models
- `bengal/core/site.py` - Site container
- `bengal/core/page/__init__.py` - Page model
- `bengal/core/page/page_core.py` - PageCore contract
- `bengal/core/section.py` - Section model

### Orchestration
- `bengal/orchestration/build_orchestrator.py` - Build coordination
- `bengal/orchestration/render_orchestrator.py` - Rendering
- `bengal/orchestration/incremental_builder.py` - Incremental builds

### Rendering
- `bengal/rendering/template_engine/` - Jinja environment
- `bengal/rendering/markdown/` - Markdown processing
- `bengal/directives/` - MyST directives

### Tests
- `tests/unit/` - Unit tests (fast, isolated)
- `tests/integration/` - Integration tests (full workflows)
- `tests/roots/` - Test site fixtures

### Configuration
- `pyproject.toml` - Project config (ruff, mypy)
- `bengal/config/` - Config system

---

## Anti-Patterns

### ❌ Unverified Claims

```markdown
# BAD - No evidence
"The Site class handles caching automatically"
```

### ✅ Evidence-Backed Claims

```markdown
# GOOD - Evidence provided
"The Site class delegates caching to CacheOrchestrator"
**Evidence**: `bengal/core/site.py:89` - `return CacheOrchestrator.save(self)`
```

### ❌ Vague References

```markdown
# BAD - Not actionable
"See the page module for details"
```

### ✅ Precise References

```markdown
# GOOD - Specific and actionable
"See `bengal/core/page/__init__.py:145-160` for the `build_url` implementation"
```

---

## Quick Reference

| Task | Format |
|------|--------|
| Single line | `file.py:45` |
| Line range | `file.py:45-52` |
| Evidence trail | `**Evidence**: file.py:45` |
| 3-path validation | Source + Test + Config |
| Search strategy | Semantic → Grep → Read → Cross-ref |

---

## Related

- `modules/types-as-contracts` - Type evidence patterns
- `modules/output-format` - Formatting evidence in output
- `commands/research` - Full research procedure
- `commands/validate` - Validation with confidence scoring
