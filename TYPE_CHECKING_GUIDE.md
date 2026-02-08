# Type Checking Guide for Bengal

How to test type annotations and catch type-related problems in the Bengal codebase.

## Quick Start

```bash
# Run type checking
make typecheck

# Or directly with uv
uv run ty check bengal/
```

## Understanding Type Errors

When you add type annotations, ty will catch several categories of problems:

### Common Error Types

1. **`invalid-assignment`** - Type mismatch in assignments
   ```python
   # Example: bengal/utils/progress.py:156
   # Variable expects int, but got str
   ```

2. **`missing-type-parameter`** - Missing type parameters for generics
   ```python
   # Example: dict should be dict[str, Any]
   # Example: list should be list[str]
   ```

3. **`no-matching-overload`** - Function call doesn't match any overload
   ```python
   # Example: Function should return specific type, not Any
   ```

4. **`unresolved-attribute`** - Accessing attribute that doesn't exist on type
   ```python
   # Example: PageComputedMixin missing metadata attribute
   ```

## Debugging Type Issues

### 1. Use `reveal_type()` to Inspect Inferred Types

Add `reveal_type()` calls in your code to see what the type checker infers:

```python
from typing import reveal_type

def example_function(data: dict[str, Any]) -> None:
    result = data.get("key")
    reveal_type(result)  # Shows inferred type

    # After fixing:
    result: str | None = data.get("key")
    reveal_type(result)  # Shows: str | None
```

**Important**: Remove `reveal_type()` calls before committing!

### 2. Check Specific Files

```bash
# Check a single file
uv run ty check bengal/utils/file_io.py

# Check a directory
uv run ty check bengal/utils/
```

### 3. Check the Full Codebase

```bash
uv run ty check bengal/
```

## Common Patterns for Fixing Type Errors

### 1. Type Narrowing

```python
# Problem: Union type, need to narrow
def process(data: dict[str, Any] | None) -> None:
    if data is None:
        return
    # Now the type checker knows data is dict[str, Any], not None
    value = data.get("key")
```

### 2. Type Guards

```python
from typing import TypeGuard

def is_dict(value: Any) -> TypeGuard[dict[str, Any]]:
    return isinstance(value, dict)

def process(value: Any) -> None:
    if is_dict(value):
        # Now the type checker knows value is dict[str, Any]
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

Type checking runs in CI via `.github/workflows/tests.yml`:

```yaml
typecheck:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Install uv
      uses: astral-sh/setup-uv@v4
      with:
        python-version: "3.14t"
    - name: Install dependencies
      run: uv sync --group dev
    - name: Run ty
      run: uv run ty check bengal/
```

## Tips

1. **Run type checking frequently** - Catch issues early
2. **Use `reveal_type()` for debugging** - Understand what the type checker sees
3. **Fix errors incrementally** - Don't try to fix everything at once
4. **Check specific files** - Focus on files you're modifying
5. **Review error messages carefully** - They often suggest fixes

## Resources

- [ty Documentation](https://docs.astral.sh/ty/)
- [Python Type Hints (PEP 484)](https://peps.python.org/pep-0484/)
- [Bengal Type Safety RFC](plan/active/rfc-type-safety-improvements.md)
- [Python Style Guide](.cursor/rules/python-style.mdc)
