# Plan: Error Handling Improvements

**Status**: Evaluated  
**Priority**: P1 (High)  
**Confidence**: 88% 🟢

---

## Executive Summary

Improve error handling consistency, context propagation, and user experience across Bengal. Establish centralized error hierarchy, standardize error context patterns, enhance error recovery, and improve error reporting.

**Key Goals**:
1. Centralized exception hierarchy with consistent context
2. Standardized error context propagation
3. Improved error recovery patterns
4. Better error aggregation and reporting
5. Consistent error handling across all subsystems

---

## Current State Analysis

### Strengths ✅

1. **Rich Error Objects**: `TemplateRenderError`, `DirectiveError`, `ContentValidationError` provide detailed context
2. **CLI Error Handling**: `handle_cli_errors` decorator and `cli_error_context` context manager
3. **Error Collection**: `BuildStats` collects template errors and warnings
4. **Context-Aware Help**: `get_context_aware_help` provides suggestions for common Python errors
5. **Graceful Degradation**: Strict mode vs production mode patterns

### Gaps ❌

1. **No Centralized Hierarchy**: Exceptions scattered, no common base class
2. **Inconsistent Context**: Some errors lack file paths, line numbers, suggestions
3. **Generic Exception Catching**: Some areas catch `Exception` without proper context
4. **Lost Exception Chains**: Some error handling loses original exception context
5. **Inconsistent Recovery**: Different subsystems handle errors differently
6. **Missing Error Categories**: No structured error categorization system
7. **Limited Error Reporting**: Errors not consistently aggregated or reported

---

## Exception Inventory

**Complete list of custom exceptions in Bengal**:

### Rendering Subsystem
- `TemplateRenderError` (`bengal/rendering/errors.py:49`) - **⚠️ DATACLASS, NOT EXCEPTION**
- `TemplateRenderError` (`bengal/rendering/engines/errors.py:52`) - Exception subclass
- `TemplateNotFoundError` (`bengal/rendering/engines/errors.py:38`) - Exception subclass
- `TemplateError` (`bengal/rendering/engines/errors.py:19`) - Dataclass (not exception)

### Directives Subsystem
- `DirectiveError` (`bengal/directives/errors.py:12`) - Exception subclass ✅

### Collections Subsystem
- `ContentValidationError` (`bengal/collections/errors.py:40`) - Exception subclass ✅
- `CollectionNotFoundError` (`bengal/collections/errors.py:116`) - Exception subclass
- `SchemaError` (`bengal/collections/errors.py:136`) - Exception subclass
- `ValidationError` (`bengal/collections/errors.py:16`) - Dataclass (not exception)

### Config Subsystem
- `ConfigLoadError` (`bengal/config/directory_loader.py:30`) - Exception subclass
- `ConfigValidationError` (`bengal/config/validators.py:18`) - Extends `ValueError`

### Core Subsystem
- `URLCollisionError` (`bengal/core/url_ownership.py:66`) - Exception subclass ✅

### Utils Subsystem
- `LockAcquisitionError` (`bengal/utils/file_lock.py:35`) - Exception subclass

**Note**: There are TWO `TemplateRenderError` classes:
1. Rich dataclass in `rendering/errors.py` (used for display/collection)
2. Exception in `rendering/engines/errors.py` (used for raising)

---

## Proposed Improvements

### Phase 0: TemplateRenderError Architecture Fix ⚠️ CRITICAL

**Goal**: Resolve the dual `TemplateRenderError` architecture before migration.

**Problem**:
- `bengal/rendering/errors.py:49` defines `TemplateRenderError` as a `@dataclass` (not Exception)
- `bengal/rendering/engines/errors.py:52` defines `TemplateRenderError` as an `Exception` subclass
- The dataclass version is used for rich error display and collection
- Currently wrapped in `RuntimeError` when raised (`bengal/rendering/renderer.py:304`)

**Solution Options**:

**Option A: Convert Dataclass to Exception (Recommended)**
- Convert `rendering/errors.py:TemplateRenderError` to extend `BengalRenderingError`
- Keep all rich context fields
- Update `BuildStats.add_template_error()` to accept Exception
- Update all display/collection code

**Option B: Keep Dataclass, Create Wrapper Exception**
- Keep dataclass for display/collection
- Create `TemplateRenderException` that wraps dataclass
- Use wrapper when raising, dataclass when collecting

**Option C: Dual-Class Strategy**
- Rename dataclass to `TemplateRenderErrorData`
- Keep Exception as `TemplateRenderError`
- Exception contains dataclass instance

**Recommended**: Option A - Convert to Exception subclass. Cleaner architecture, aligns with plan.

**Tasks**:

1. **Convert TemplateRenderError to Exception**:
   ```python
   # bengal/rendering/errors.py
   class TemplateRenderError(BengalRenderingError):
       """Rich template error with all debugging information."""

       def __init__(
           self,
           error_type: str,
           message: str,
           template_context: TemplateErrorContext,
           inclusion_chain: InclusionChain | None = None,
           page_source: Path | None = None,
           suggestion: str | None = None,
           available_alternatives: list[str] | None = None,
           search_paths: list[Path] | None = None,
           *,
           file_path: Path | None = None,
           line_number: int | None = None,
           original_error: Exception | None = None,
       ):
           # Set base class fields
           super().__init__(
               message=message,
               file_path=file_path or template_context.template_path,
               line_number=line_number or template_context.line_number,
               suggestion=suggestion,
               original_error=original_error,
           )

           # Set rich context fields
           self.error_type = error_type
           self.template_context = template_context
           self.inclusion_chain = inclusion_chain
           self.page_source = page_source
           self.available_alternatives = available_alternatives or []
           self.search_paths = search_paths
   ```

2. **Update Renderer** (`bengal/rendering/renderer.py:304`):
   ```python
   # Before
   raise RuntimeError(f"Template error: {rich_error.message[:200]}") from e

   # After
   raise rich_error  # Can now raise directly
   ```

3. **Update BuildStats** (`bengal/orchestration/stats/models.py:107`):
   - Ensure `add_template_error()` accepts Exception
   - Update type hints

4. **Remove Duplicate Exception** (`bengal/rendering/engines/errors.py:52`):
   - Remove `TemplateRenderError` Exception (keep only rich version)
   - Update imports across codebase

**Files to Modify**:
- `bengal/rendering/errors.py` - Convert dataclass to Exception
- `bengal/rendering/renderer.py` - Remove RuntimeError wrapper
- `bengal/rendering/engines/errors.py` - Remove duplicate Exception
- `bengal/orchestration/stats/models.py` - Update type hints
- All files importing `TemplateRenderError`

**Estimated Time**: 3-4 hours

**Backward Compatibility**:
- Keep `display_template_error()` function signature unchanged
- Keep `BuildStats.add_template_error()` signature unchanged
- Internal implementation changes only

---

### Phase 1: Centralized Error Hierarchy

**Goal**: Create a base exception hierarchy with consistent context support.

**Tasks**:

1. **Create Base Exception Classes** (`bengal/utils/exceptions.py`):
   ```python
   class BengalError(Exception):
       """Base exception for all Bengal errors."""

       def __init__(
           self,
           message: str,
           *,
           file_path: Path | None = None,
           line_number: int | None = None,
           suggestion: str | None = None,
           original_error: Exception | None = None,
       ):
           self.message = message
           self.file_path = file_path
           self.line_number = line_number
           self.suggestion = suggestion
           self.original_error = original_error
           super().__init__(self._format_message())

       def _format_message(self) -> str:
           """Format error message with context."""
           parts = [self.message]
           if self.file_path:
               parts.append(f"File: {self.file_path}")
           if self.line_number:
               parts.append(f"Line: {self.line_number}")
           if self.suggestion:
               parts.append(f"Tip: {self.suggestion}")
           return "\n".join(parts)

       def to_dict(self) -> dict[str, Any]:
           """Convert to dictionary for JSON serialization."""
           return {
               "type": self.__class__.__name__,
               "message": self.message,
               "file_path": str(self.file_path) if self.file_path else None,
               "line_number": self.line_number,
               "suggestion": self.suggestion,
           }

   class BengalConfigError(BengalError):
       """Configuration-related errors."""
       pass

   class BengalContentError(BengalError):
       """Content-related errors."""
       pass

   class BengalRenderingError(BengalError):
       """Rendering-related errors."""
       pass

   class BengalDiscoveryError(BengalError):
       """Content discovery errors."""
       pass

   class BengalCacheError(BengalError):
       """Cache-related errors."""
       pass
   ```

2. **Migrate Existing Exceptions** (after Phase 0):
   - `TemplateRenderError` → Already extends `BengalRenderingError` (from Phase 0)
   - `DirectiveError` → Extend `BengalRenderingError`
   - `ContentValidationError` → Extend `BengalContentError`
   - `URLCollisionError` → Extend `BengalContentError`
   - `ConfigLoadError` → Extend `BengalConfigError`
   - `TemplateNotFoundError` → Extend `BengalRenderingError`
   - `CollectionNotFoundError` → Extend `BengalContentError`
   - `SchemaError` → Extend `BengalContentError`
   - `ConfigValidationError` → Extend `BengalConfigError` (currently extends ValueError)
   - `LockAcquisitionError` → Extend `BengalCacheError` (or new `BengalSystemError`)

3. **Update Error Handling Rule**:
   - Document new hierarchy
   - Update examples to use base classes
   - Add migration guide

**Files to Modify**:
- `bengal/utils/exceptions.py` (new)
- `bengal/rendering/errors.py`
- `bengal/directives/errors.py`
- `bengal/collections/errors.py`
- `bengal/core/url_ownership.py`
- `bengal/config/loader.py`
- `.cursor/rules/error-handling.mdc`

**Estimated Time**: 4-6 hours

---

### Phase 2: Standardized Error Context Propagation

**Goal**: Ensure all errors include file path, line number, and suggestions when available.

**Tasks**:

1. **Create Error Context Helper** (`bengal/utils/error_context.py`):
   ```python
   @dataclass
   class ErrorContext:
       """Standardized error context."""
       file_path: Path | None = None
       line_number: int | None = None
       column: int | None = None
       operation: str | None = None  # e.g., "parsing frontmatter", "rendering template"
       suggestion: str | None = None
       original_error: Exception | None = None

   def enrich_error(
       error: Exception,
       context: ErrorContext,
       error_class: type[BengalError] = BengalError,
   ) -> BengalError:
       """Enrich exception with context."""
       if isinstance(error, BengalError):
           # Already enriched, just add missing context
           if context.file_path and not error.file_path:
               error.file_path = context.file_path
           if context.line_number and not error.line_number:
               error.line_number = context.line_number
           if context.suggestion and not error.suggestion:
               error.suggestion = context.suggestion
           return error

       # Create new error with context
       return error_class(
           message=str(error) or type(error).__name__,
           file_path=context.file_path,
           line_number=context.line_number,
           suggestion=context.suggestion,
           original_error=error,
       )
   ```

2. **Add Context to File Processing**:
   - Wrap file operations with context managers
   - Capture file path and line number automatically
   - Propagate context through exception chains

3. **Update Error Handlers**:
   - Use `enrich_error` in all catch blocks
   - Ensure context flows through exception chains

**Files to Modify**:
- `bengal/utils/error_context.py` (new)
- `bengal/discovery/content_discovery.py`
- `bengal/rendering/renderer.py`
- `bengal/orchestration/build/content.py`
- `bengal/config/loader.py`

**Estimated Time**: 3-4 hours

---

### Phase 3: Improved Error Recovery Patterns

**Goal**: Standardize error recovery across subsystems.

**Tasks**:

1. **Create Error Recovery Utilities** (`bengal/utils/error_recovery.py`):
   ```python
   def with_error_recovery(
       operation: Callable[[], T],
       *,
       on_error: Callable[[Exception], T] | None = None,
       error_types: tuple[type[Exception], ...] = (Exception,),
       strict_mode: bool = False,
       logger: Any | None = None,
   ) -> T:
       """
       Execute operation with error recovery.

       Args:
           operation: Function to execute
           on_error: Recovery function (returns fallback value)
           error_types: Exception types to catch
           strict_mode: If True, re-raise instead of recovering
           logger: Logger instance for warnings

       Returns:
           Result of operation or recovery function
       """
       try:
           return operation()
       except error_types as e:
           if strict_mode:
               raise

           if logger:
               logger.warning(f"Error in {operation.__name__}: {e}")

           if on_error:
               return on_error(e)

           raise

   @contextmanager
   def error_recovery_context(
       operation_name: str,
       *,
       strict_mode: bool = False,
       logger: Any | None = None,
   ):
       """Context manager for error recovery."""
       try:
           yield
       except Exception as e:
           if strict_mode:
               raise

           if logger:
               logger.warning(f"Error in {operation_name}: {e}")

           # Continue execution (don't re-raise)
   ```

2. **Apply to File Processing**:
   - Use `with_error_recovery` in file loops
   - Continue processing other files on error
   - Collect errors for batch reporting

3. **Apply to Template Rendering**:
   - Use recovery patterns in renderer
   - Collect errors instead of failing immediately
   - Report at end of build

**Files to Modify**:
- `bengal/utils/error_recovery.py` (new)
- `bengal/discovery/content_discovery.py`
- `bengal/rendering/renderer.py`
- `bengal/orchestration/build/content.py`

**Estimated Time**: 3-4 hours

---

### Phase 4: Enhanced Error Aggregation and Reporting

**Goal**: Improve error collection, categorization, and reporting.

**Tasks**:

1. **Enhance BuildStats Error Collection**:
   ```python
   @dataclass
   class ErrorCategory:
       """Error category for grouping."""
       name: str
       errors: list[BengalError] = field(default_factory=list)
       warnings: list[str] = field(default_factory=list)

   @dataclass
   class BuildStats:
       # Existing fields...

       # Enhanced error collection
       errors_by_category: dict[str, ErrorCategory] = field(default_factory=dict)

       def add_error(self, error: BengalError, category: str = "general") -> None:
           """Add error to category."""
           if category not in self.errors_by_category:
               self.errors_by_category[category] = ErrorCategory(name=category)
           self.errors_by_category[category].errors.append(error)

       def get_error_summary(self) -> dict[str, Any]:
           """Get summary of all errors."""
           return {
               "total_errors": sum(len(cat.errors) for cat in self.errors_by_category.values()),
               "total_warnings": sum(len(cat.warnings) for cat in self.errors_by_category.values()),
               "by_category": {
                   name: {
                       "errors": len(cat.errors),
                       "warnings": len(cat.warnings),
                   }
                   for name, cat in self.errors_by_category.items()
               },
           }
   ```

2. **Create Error Reporter** (`bengal/utils/error_reporter.py`):
   ```python
   def format_error_report(stats: BuildStats, verbose: bool = False) -> str:
       """Format comprehensive error report."""
       lines = []

       summary = stats.get_error_summary()
       if summary["total_errors"] == 0 and summary["total_warnings"] == 0:
           return "✅ No errors or warnings"

       lines.append(f"Errors: {summary['total_errors']}, Warnings: {summary['total_warnings']}")

       for category_name, category in stats.errors_by_category.items():
           if not category.errors and not category.warnings:
               continue

           lines.append(f"\n{category_name.upper()}:")

           for error in category.errors:
               lines.append(f"  ❌ {error.message}")
               if verbose and error.file_path:
                   lines.append(f"     File: {error.file_path}")
               if verbose and error.suggestion:
                   lines.append(f"     Tip: {error.suggestion}")

       return "\n".join(lines)
   ```

3. **Integrate into Build Output**:
   - Display error summary at end of build
   - Show categorized errors
   - Provide suggestions for fixing

**Files to Modify**:
- `bengal/orchestration/stats/models.py`
- `bengal/utils/error_reporter.py` (new)
- `bengal/orchestration/build/finalization.py`
- `bengal/cli/commands/build.py`

**Estimated Time**: 3-4 hours

---

### Phase 5: Subsystem-Specific Improvements

**Goal**: Address gaps in specific subsystems.

**Tasks**:

1. **Discovery Subsystem**:
   - Add file path context to all discovery errors
   - Improve symlink error handling
   - Better permission error messages

2. **Rendering Subsystem**:
   - Ensure all template errors include context
   - Improve filter/variable error suggestions
   - Better inclusion chain reporting

3. **Config Subsystem**:
   - Better validation error messages
   - Include config file path and line number
   - Suggest fixes for common config errors

4. **Cache Subsystem**:
   - Better cache corruption detection
   - Clearer cache error messages
   - Recovery suggestions

5. **Orchestration Subsystem**:
   - Better phase error reporting
   - Context propagation through phases
   - Clearer build failure messages

**Files to Modify**:
- `bengal/discovery/content_discovery.py`
- `bengal/rendering/renderer.py`
- `bengal/config/loader.py`
- `bengal/cache/` (various files)
- `bengal/orchestration/build/` (various files)

**Estimated Time**: 4-6 hours

---

## Implementation Plan

### Week 1: Foundation
- [ ] Phase 0: TemplateRenderError Architecture Fix ⚠️ CRITICAL
- [ ] Phase 1: Centralized Error Hierarchy
- [ ] Phase 2: Standardized Error Context Propagation

### Week 2: Enhancement
- [ ] Phase 3: Improved Error Recovery Patterns
- [ ] Phase 4: Enhanced Error Aggregation and Reporting

### Week 3: Integration
- [ ] Phase 5: Subsystem-Specific Improvements
- [ ] Update tests
- [ ] Update documentation

---

## Testing Strategy

1. **Unit Tests**:
   - Test base exception classes
   - Test error context helpers
   - Test error recovery utilities
   - Test error aggregation

2. **Integration Tests**:
   - Test error handling in builds
   - Test error collection across phases
   - Test error reporting output

3. **Edge Cases**:
   - Nested exception chains
   - Missing context scenarios
   - Strict mode vs production mode
   - Concurrent error handling

---

## Migration Strategy & Backward Compatibility

### Backward Compatibility Approach

**Principle**: Gradual migration with zero breaking changes during transition.

**Strategy**:
1. **Additive Changes First**: New base classes don't break existing code
2. **Dual Support Period**: Old and new exception classes coexist
3. **Gradual Migration**: Migrate one subsystem at a time
4. **Deprecation Timeline**: 2-3 releases for full migration

### Migration Phases

**Phase 0-1 (Current Release)**:
- Add base exception classes
- Convert `TemplateRenderError` to Exception
- No breaking changes - old code still works

**Phase 2-3 (Next Release)**:
- Migrate exceptions to extend base classes
- Add deprecation warnings for old patterns
- Old exceptions still work, but emit warnings

**Phase 4-5 (Future Release)**:
- Remove deprecated exception classes
- Update all code to use new hierarchy
- Breaking changes only after deprecation period

### Deprecation Timeline

| Release | Action | Breaking? |
|---------|--------|-----------|
| v0.1.6 | Add base classes, Phase 0 fix | No |
| v0.1.7 | Migrate exceptions, add warnings | No (warnings only) |
| v0.2.0 | Remove deprecated classes | Yes (after deprecation) |

### Code Migration Examples

**Example 1: Raising Exceptions**
```python
# Before (still works during migration)
raise ValueError(f"Invalid config: {key}")

# After (preferred)
from bengal.utils.exceptions import BengalConfigError
raise BengalConfigError(
    f"Invalid config: {key}",
    file_path=config_path,
    suggestion=f"Check available keys: {', '.join(available_keys)}"
)
```

**Example 2: Catching Exceptions**
```python
# Before (still works)
try:
    render_template(name)
except TemplateRenderError as e:
    handle_error(e)

# After (same - no change needed)
try:
    render_template(name)
except TemplateRenderError as e:  # Now extends BengalRenderingError
    handle_error(e)
```

**Example 3: Error Collection**
```python
# Before (still works)
if self.build_stats:
    self.build_stats.add_template_error(rich_error)

# After (same - no change needed)
# TemplateRenderError is now Exception, works with existing code
if self.build_stats:
    self.build_stats.add_template_error(rich_error)
```

---

## Migration Guide

### For Developers

1. **Use Base Exception Classes**:
   ```python
   # Before
   raise ValueError(f"Invalid config: {key}")

   # After
   from bengal.utils.exceptions import BengalConfigError
   raise BengalConfigError(
       f"Invalid config: {key}",
       file_path=config_path,
       suggestion=f"Check available keys: {', '.join(available_keys)}"
   )
   ```

2. **Use Error Context Helpers**:
   ```python
   # Before
   try:
       parse_file(path)
   except Exception as e:
       logger.error(f"Error: {e}")

   # After
   from bengal.utils.error_context import ErrorContext, enrich_error

   try:
       parse_file(path)
   except Exception as e:
       context = ErrorContext(file_path=path, operation="parsing file")
       enriched = enrich_error(e, context)
       logger.error(str(enriched))
   ```

3. **Use Error Recovery**:
   ```python
   # Before
   for file in files:
       try:
           process(file)
       except Exception:
           continue

   # After
   from bengal.utils.error_recovery import with_error_recovery

   for file in files:
       with_error_recovery(
           lambda: process(file),
           on_error=lambda e: logger.warning(f"Skipped {file}: {e}"),
           strict_mode=strict_mode,
       )
   ```

---

## Success Criteria

✅ **Centralized Hierarchy**: All exceptions extend base classes  
✅ **Consistent Context**: All errors include file path, line number, suggestions  
✅ **Error Recovery**: Standardized recovery patterns across subsystems  
✅ **Error Reporting**: Comprehensive error reports at end of build  
✅ **User Experience**: Clear, actionable error messages  
✅ **Developer Experience**: Easy to add context to errors  
✅ **Backward Compatible**: Existing code continues to work  

---

## Risks and Mitigations

**Risk**: Breaking changes to exception hierarchy  
**Mitigation**:
- Phase 0 addresses TemplateRenderError architecture first
- Gradual migration with 2-3 release deprecation period
- Keep existing exceptions, add base classes gradually
- Dual support during transition period

**Risk**: Performance impact of error context collection  
**Mitigation**: Use lazy evaluation, only collect when needed

**Risk**: Inconsistent migration across subsystems  
**Mitigation**: Phase-by-phase approach, update rule documentation

---

## Related Documentation

- `.cursor/rules/error-handling.mdc` - Current error handling rules
- `plan/ready/rfc-template-error-collection.md` - Template error collection RFC
- `architecture/design-principles.md` - Design principles

---

## Next Steps

### Before Implementation

1. ✅ **Review and approve plan** - Address critical Phase 0 issue
2. ✅ **Complete exception inventory** - Documented above
3. ✅ **Clarify migration strategy** - Added backward compatibility section

### Implementation Order

1. **Phase 0** (CRITICAL): Fix TemplateRenderError architecture
   - Convert dataclass to Exception subclass
   - Remove RuntimeError wrapper
   - Test thoroughly - this affects rendering subsystem

2. **Phase 1**: Create base exception classes
   - Add `BengalError` and subclasses
   - No breaking changes - additive only

3. **Phase 2-5**: Gradual migration
   - Migrate one subsystem at a time
   - Test each migration thoroughly
   - Update documentation as you go

### Proof of Concept

**Recommended**: Start with `DirectiveError` migration
- Small, isolated subsystem
- Already has rich context
- Low risk, high value demonstration

**Steps**:
1. Make `DirectiveError` extend `BengalRenderingError`
2. Update error creation code
3. Test directive error handling
4. Verify backward compatibility
5. Document migration pattern for other subsystems
