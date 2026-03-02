---
name: ""
overview: ""
todos: []
isProject: false
---

# Fourth-Round: Unexplored Region Boundary Fixes

## Summary

Address remaining `type: ignore` and boundary patterns in regions not yet covered by rounds 1–3. Focus on attribute declarations, control-flow narrowing, and config/serialization boundaries. Deferred items (BuildTrigger, shortcodes, BuildContext) are planned separately.

---

## 1. Add `_cascade_invalidated` to Page

**File:** [bengal/core/page/**init**.py](bengal/core/page/__init__.py)

**Problem:** [bengal/build/provenance/filter.py:275](bengal/build/provenance/filter.py) assigns `page._cascade_invalidated = True` but Page does not declare this attribute. [bengal/rendering/pipeline/cache_checker.py:337](bengal/rendering/pipeline/cache_checker.py) reads it via `getattr(page, "_cascade_invalidated", False)`.

**Solution:** Add optional cache-invalidation flag to Page:

```python
_cascade_invalidated: bool = field(default=False, repr=False, init=False)
```

Then remove `type: ignore[attr-defined]` from provenance/filter.py. The cache_checker can keep `getattr` for backward compatibility with PageProxy/mocks, or switch to direct access.

**Effort:** ~15 min

---

## 2. Fix Index Generator `accumulated_data` Union Narrowing

**File:** [bengal/postprocess/output_formats/index_generator.py](bengal/postprocess/output_formats/index_generator.py)

**Problem:** Lines 267 and 429: `for data in accumulated_data` — when `use_accumulated_only` is True, `accumulated_data` is guaranteed non-None (we checked `accumulated_count == len(pages) and accumulated_count > 0`), but the type checker does not narrow.

**Solution:** Add explicit assert before the loop in both `_generate_single_index` and `_generate_version_index`:

```python
if use_accumulated_only:
    assert accumulated_data is not None  # Guaranteed by use_accumulated_only
    for data in accumulated_data:
        ...
```

Remove both `type: ignore[union-attr]`.

**Effort:** ~20 min

---

## 3. Fix Site Config `.raw` Union-Attr

**File:** [bengal/core/site/**init**.py](bengal/core/site/__init__.py)

**Problem:** Line 289: `config_dict = self.config.raw` — Site has `config: Config | dict[str, Any]`. After `hasattr(self.config, "raw")`, the type checker does not narrow to Config.

**Solution:** Use the existing `unwrap_config` helper from [bengal/config/utils.py](bengal/config/utils.py):

```python
from bengal.config.utils import unwrap_config

config_dict = unwrap_config(self.config)
```

Replace the entire `if hasattr ... elif isinstance ... else` block. Remove `type: ignore[union-attr]`.

**Effort:** ~15 min

---

## 4. Fix `_get_version_target_url` Arg-Type

**File:** [bengal/core/site/**init**.py](bengal/core/site/__init__.py)

**Problem:** Line 550: `return _get_version_target_url(page, target_version, self)` — `_get_version_target_url` expects `(page: PageLike | None, target_version, site: SiteLike)`. Site passes `self`; the checker may not recognize Site as SiteLike.

**Solution:** Use `cast(SiteLike, self)` when calling:

```python
return _get_version_target_url(page, target_version, cast(SiteLike, self))
```

`cast` is already imported in site/**init**.py. Remove `type: ignore[arg-type]`.

**Effort:** ~10 min

---

## 5. Fix Collections Validator `model_validate` Attr-Defined

**File:** [bengal/collections/validator.py](bengal/collections/validator.py)

**Problem:** Line 284: `instance = self.schema.model_validate(data)` — `schema` is typed as a generic; when `_is_pydantic` is True we know it has `model_validate`, but the type checker does not.

**Solution:** Add a Protocol for Pydantic-like schemas, or use `getattr` with a type assertion:

```python
# Option A: Protocol
class HasModelValidate(Protocol):
    def model_validate(self, data: Any) -> Any: ...

# In _validate_pydantic: cast schema to HasModelValidate
instance = cast(HasModelValidate, self.schema).model_validate(data)
```

Or Option B: Keep the type: ignore with a clearer comment — Pydantic is an optional dependency and the schema type is intentionally generic. **Recommendation:** Use `cast(HasModelValidate, self.schema).model_validate(data)` with a small Protocol in the same file or in `bengal/protocols/`.

**Effort:** ~20 min

---

## 6. Fix Dates.py Type Ignores (Optional / Lower Priority)

**File:** [bengal/utils/primitives/dates.py](bengal/utils/primitives/dates.py)

**Problem:**

- Line 102: `return value` when `on_error="return_original"` — `parse_date` declares `-> datetime | None` but can return the original value (str, etc.).
- Line 308: `return dt_start1 <= dt_end2 and ...` — comparison of `datetime | date | None`; checker may not narrow after `all()`.

**Solution:**

- Line 102: Broaden return type to `datetime | date_type | None | DateLike` when `on_error="return_original"`, or use overloads. Simpler: `return cast(datetime | date_type | None, value)` with a comment that return_original returns as-is.
- Line 308: Add explicit narrowing: `assert dt_start1 is not None and dt_end1 is not None and dt_start2 is not None and dt_end2 is not None` before the return, or wrap in `bool()`.

**Recommendation:** Defer dates.py to a later pass — these are in a low-level utility and the ignores are narrow. If included: ~25 min.

**Effort:** ~25 min (if done)

---

## Implementation Order


| #   | Task                                           | Est.   |
| --- | ---------------------------------------------- | ------ |
| 1   | Add `_cascade_invalidated` to Page             | 15 min |
| 2   | Fix index generator accumulated_data narrowing | 20 min |
| 3   | Fix Site config.raw via unwrap_config          | 15 min |
| 4   | Fix _get_version_target_url arg-type           | 10 min |
| 5   | Fix collections validator model_validate       | 20 min |
| 6   | Fix dates.py (optional)                        | 25 min |


**Total (excluding dates):** ~1.5 hours  
**Total (including dates):** ~2 hours

---

## Verification

- Run `ruff check bengal/` and `mypy bengal/`
- Confirm zero `type: ignore` in modified files for the addressed issues
- Run relevant tests (provenance, index generator, site init)

---

## Out of Scope (Deferred Items)

- BuildTrigger getattr replacement
- Shortcodes getattr replacement
- BuildContext Any fields
- Optional imports (typer, smartcrop, rosettes)
- Kida protocol self-check
