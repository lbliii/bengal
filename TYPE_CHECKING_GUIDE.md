# Type Checking Guide for Bengal

How to test type annotations and catch type-related problems in the Bengal codebase.

## Quick Start

```bash
# Run type checking
make typecheck

# Or directly with uv
uv run mypy bengal/ --show-error-codes
```

## Understanding Type Errors

When you add type annotations, mypy will catch several categories of problems:

### Common Error Types

1. **`assignment`** - Type mismatch in assignments
   ```python
   # Example: bengal/utils/progress.py:156
   # Variable expects int, but got str
   ```

2. **`type-arg`** - Missing type parameters for generics
   ```python
   # Example: dict should be dict[str, Any]
   # Example: list should be list[str]
   ```

3. **`no-any-return`** - Function returns `Any` when it shouldn't
   ```python
   # Example: Function should return specific type, not Any
   ```

4. **`attr-defined`** - Accessing attribute that doesn't exist on type
   ```python
   # Example: PageComputedMixin missing metadata attribute
   ```

5. **`import-untyped`** - Library stubs not installed
   ```python
   # Example: "Library stubs not installed for 'yaml'"
   # Fix: Install types-PyYAML
   ```

6. **`var-annotated`** - Variable needs type annotation
   ```python
   # Example: Need type annotation for "section_buffer"
   # Hint: "section_buffer: list[<type>] = ..."
   ```

## Debugging Type Issues

### 1. Use `reveal_type()` to Inspect Inferred Types

Add `reveal_type()` calls in your code to see what mypy thinks a variable's type is:

```python
from typing import reveal_type

def example_function(data: dict[str, Any]) -> None:
    result = data.get("key")
    reveal_type(result)  # Shows: Revealed type is "Any | None"
    
    # After fixing:
    result: str | None = data.get("key")
    reveal_type(result)  # Shows: Revealed type is "str | None"
```

**Important**: Remove `reveal_type()` calls before committing!

### 2. Check Specific Files

```bash
# Check a single file
uv run mypy bengal/utils/file_io.py --show-error-codes

# Check a directory
uv run mypy bengal/utils/ --show-error-codes
```

### 3. Get More Context

```bash
# Show error context (where the error occurred)
uv run mypy bengal/ --show-error-codes --show-error-context

# Show traceback for errors
uv run mypy bengal/ --show-error-codes --show-traceback
```

### 4. Strict Mode (for debugging)

```bash
# Run with strict mode to catch everything
make typecheck-strict

# Or manually
uv run mypy bengal/ --strict --show-error-codes
```

**Note**: Strict mode enables all checks. Your current config already has many strict settings enabled.

## Installing Missing Type Stubs

When you see `Library stubs not installed for "X"`:

```bash
# Install specific stubs
uv pip install types-PyYAML
uv pip install types-psutil
uv pip install types-python-dateutil

# Or let mypy suggest all missing stubs
uv run mypy bengal/ --install-types
```

Then add to `pyproject.toml` under `[project.optional-dependencies.dev]`:

```toml
dev = [
    # ... existing ...
    "types-PyYAML>=6.0.12",
    "types-psutil>=5.9.0",
    "types-python-dateutil>=2.8.0",
]
```

## Testing Types After Adding Annotations

### Workflow

1. **Add type annotations** to your code
2. **Run type checking**:
   ```bash
   make typecheck
   ```
3. **Review errors** - mypy will show:
   - Type mismatches you didn't expect
   - Missing type parameters
   - Incorrect assumptions about types
4. **Fix issues** - Either:
   - Fix the code to match the types
   - Fix the types to match the code
   - Add type guards/narrowing where needed
5. **Re-run** until clean

### Example: Finding Type Problems

```bash
# Before adding types - no errors (but also no safety)
# After adding types:
$ make typecheck
bengal/utils/progress.py:156: error: Incompatible types in assignment (expression has type "str", variable has type "int")  [assignment]

# This reveals: You thought it was an int, but it's actually a str!
# Fix: Either change the type annotation or fix the code
```

## Common Patterns for Fixing Type Errors

### 1. Type Narrowing

```python
# Problem: Union type, need to narrow
def process(data: dict[str, Any] | None) -> None:
    if data is None:
        return
    # Now mypy knows data is dict[str, Any], not None
    value = data.get("key")
```

### 2. Type Guards

```python
from typing import TypeGuard

def is_dict(value: Any) -> TypeGuard[dict[str, Any]]:
    return isinstance(value, dict)

def process(value: Any) -> None:
    if is_dict(value):
        # Now mypy knows value is dict[str, Any]
        value["key"]
```

### 3. TypedDict for Structured Data

```python
from typing import TypedDict

class ConfigDict(TypedDict):
    name: str
    version: str
    optional_field: str | None

def load_config() -> ConfigDict:
    # Instead of dict[str, Any]
    return {"name": "bengal", "version": "0.1.4"}
```

### 4. Generic Type Parameters

```python
# Bad: Missing type parameters
def process(items: list) -> dict:
    ...

# Good: Explicit type parameters
def process(items: list[str]) -> dict[str, int]:
    ...
```

## CI Integration

To catch type errors in CI, add to `.github/workflows/tests.yml`:

```yaml
- name: Type checking
  run: |
    uv pip install -e ".[dev]"
    uv run mypy bengal/ --show-error-codes
```

Or add as a separate job:

```yaml
typecheck:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Set up Python 3.14
      uses: actions/setup-python@v5
      with:
        python-version: "3.14"
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .[dev]
    - name: Run mypy
      run: mypy bengal/ --show-error-codes
```

## Current Configuration

Your `pyproject.toml` has these strict settings enabled:

```toml
[tool.mypy]
python_version = "3.14"
warn_return_any = true              # Warns about Any returns
warn_unused_configs = true         # Warns about unused config
disallow_untyped_defs = true        # Requires type annotations
strict_optional = true              # Treats None as separate type
disallow_any_generics = true        # Requires type params for generics
disallow_incomplete_defs = true     # Requires complete annotations
```

## Tips

1. **Run type checking frequently** - Catch issues early
2. **Use `reveal_type()` for debugging** - Understand what mypy sees
3. **Fix errors incrementally** - Don't try to fix everything at once
4. **Check specific files** - Focus on files you're modifying
5. **Review error messages carefully** - They often suggest fixes
6. **Install missing stubs** - Improves type checking for dependencies

## Resources

- [mypy Documentation](https://mypy.readthedocs.io/)
- [Python Type Hints (PEP 484)](https://peps.python.org/pep-0484/)
- [Bengal Type Safety RFC](plan/active/rfc-type-safety-improvements.md)
- [Python Style Guide](.cursor/rules/python-style.mdc)

