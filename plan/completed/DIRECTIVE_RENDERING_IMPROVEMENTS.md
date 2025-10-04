# Directive & Rendering Improvements: Health, Ergonomics, Performance

**Date:** October 4, 2025  
**Focus:** Zero in on directives and rendering problems  
**Goals:** Health checks, ergonomics, performance

---

## 🎯 Executive Summary

### Current State

**Directives Working:**
- ✅ Tabs, Admonitions, Dropdowns, Code-tabs all functional
- ✅ Recursive markdown parsing within directives
- ✅ Parser reuse via thread-local storage
- ✅ Variable substitution plugin

**Issues Identified:**

1. **❌ No Directive-Specific Health Checks**
   - RenderingValidator only checks generic HTML output
   - No validation of directive syntax, structure, or completeness
   - No detection of malformed directives that fail silently

2. **❌ Poor Error Ergonomics**
   - Generic parsing errors don't indicate which directive failed
   - No line numbers for directive errors
   - Silent failures in directive rendering

3. **⚠️ Performance Bottlenecks**
   - 100+ directive blocks = 7-9 seconds for 57 pages
   - Recursive parsing O(n × m) complexity
   - No caching of parsed directive content
   - No profiling/timing information

---

## 📊 Problem Analysis

### 1. Health Check Gaps

**Current RenderingValidator checks:**
- ✅ HTML structure (DOCTYPE, html, head, body tags)
- ✅ Unrendered Jinja2 variables
- ✅ Template functions registered
- ✅ SEO metadata

**Missing directive-specific checks:**
- ❌ Malformed directive syntax
- ❌ Unclosed directive blocks
- ❌ Missing required directive options
- ❌ Invalid tab markers in tabs directives
- ❌ Directive nesting depth warnings
- ❌ Performance warnings for directive-heavy pages

**Example: Silent Failure**
```markdown
```{tabs}
### Tab: Python
Content here
# MISSING CLOSING BACKTICKS - FAILS SILENTLY!
```

This will either:
- Render as a code block (directive ignored)
- Cause parsing error with unclear message
- Generate malformed HTML

**No health check catches this!**

### 2. Ergonomics Issues

#### A. Generic Error Messages

**Current error (from parser.py:174-179):**
```python
except Exception as e:
    print(f"Warning: Mistune parsing error: {e}", file=sys.stderr)
    return f'<div class="markdown-error">...'
```

**Problems:**
- Doesn't say WHICH directive failed
- No file path or line number
- No context about directive type
- No suggestion for fix

**Better error would be:**
```
❌ Directive Error: file.md:127
   In directive: {tabs}
   Error: Missing closing tab marker
   
   Found:
   127 | ### Tab: Python
   128 | Content here...
   129 | ### Ta: JavaScript  ← Typo! Should be "### Tab:"
   
   Suggestion: Check tab marker syntax (### Tab: Title)
```

#### B. No Validation Before Parsing

Directives are parsed directly without validation:

```python
# tabs.py:44-45
parts = re.split(r'^### Tab: (.+)$', content, flags=re.MULTILINE)
```

**Issues:**
- No check if tabs block is empty
- No validation of tab marker format
- No warning if only one tab (use admonition instead?)
- No limit on nesting depth

#### C. No Feedback During Build

Users don't know:
- How many directives were processed
- Which pages are slow due to directives
- If directives rendered correctly
- Directive usage statistics

### 3. Performance Analysis

From `plan/SHOWCASE_PERFORMANCE_ANALYSIS.md`:

**Current numbers:**
- 57 pages in 7.08 seconds = 124ms per page average
- Large pages: 500-800ms (1100 lines, 21 tabs blocks)
- Small pages: 10-20ms (simple content)

**Root cause: Recursive parsing**

Each directive calls `self.parse_tokens()` for its content:

```python
# tabs.py:75
'children': self.parse_tokens(block, tab_content, state)
```

**Example:**
- `strings.md` has 21 tabs blocks
- Average 11 individual tabs per block
- **That's 231 recursive markdown parses for one page!**

**No caching means:**
- Same content parsed multiple times if repeated
- No reuse across incremental builds
- Every build does full parse from scratch

---

## ✅ Proposed Solutions

### Phase 1: Health Checks (High Priority)

#### 1.1 DirectiveHealthCheck Validator

New validator: `bengal/health/validators/directives.py`

**Checks:**

```python
class DirectiveValidator(BaseValidator):
    """
    Validates directive syntax and usage.
    
    Checks:
    - Directive syntax is well-formed
    - Required options present
    - Tab markers properly formatted
    - Nesting depth reasonable
    - Performance warnings for heavy directive usage
    """
    
    def validate(self, site: 'Site') -> List[CheckResult]:
        results = []
        results.extend(self._check_directive_syntax(site))
        results.extend(self._check_directive_completeness(site))
        results.extend(self._check_directive_performance(site))
        return results
```

**Specific checks:**

1. **Syntax validation**
   - Find all directive blocks: ` ```{name} `
   - Check closing backticks present
   - Validate directive name is registered
   - Check option syntax (`:key: value`)

2. **Completeness validation**
   - Tabs blocks have at least 2 tabs
   - Tab markers properly formatted: `### Tab: Title`
   - Required options present (e.g., `:id:` for tabs)
   - Content not empty

3. **Performance warnings**
   - Warn if page has >10 directive blocks
   - Warn if directive nesting depth >3
   - Warn if tabs block has >10 tabs
   - Identify slowest pages for optimization

**Example output:**
```
⚠️ Directives
  ✓ All 147 directive blocks syntactically valid
  ⚠ Warning: 3 pages have heavy directive usage (>10 blocks)
    - docs/function-reference/strings.md (21 blocks)
    - docs/markdown/kitchen-sink.md (15 blocks)
    - docs/templates/index.md (12 blocks)
    Recommendation: Consider splitting large pages or reducing directive nesting
  ✓ No missing tab markers
  ✓ All directive options valid
  
  📊 Directive statistics:
    - Total directives: 147
    - Most used: tabs (53), admonitions (42), dropdown (28)
    - Average per page: 2.6
    - Max per page: 21 (strings.md)
```

#### 1.2 Enhance RenderingValidator

Add directive-specific checks to existing validator:

```python
def _check_directive_rendering(self, site: 'Site') -> List[CheckResult]:
    """Check that directives rendered to proper HTML."""
    results = []
    issues = []
    
    for page in site.pages:
        content = page.output_path.read_text()
        
        # Check for unrendered directive markers
        if '```{' in content:
            issues.append(f"{page.output_path.name}: Unrendered directive block")
        
        # Check for directive error markers
        if 'class="markdown-error"' in content:
            issues.append(f"{page.output_path.name}: Directive parsing error")
    
    # ... return results
```

### Phase 2: Ergonomics (High Priority)

#### 2.1 Rich Directive Error Reporting

Enhance `bengal/rendering/parser.py` with directive-aware error handling:

```python
class DirectiveError(Exception):
    """Rich directive parsing error."""
    def __init__(
        self, 
        directive_type: str,
        error_message: str,
        file_path: Optional[Path] = None,
        line_number: Optional[int] = None,
        content_snippet: Optional[str] = None,
        suggestion: Optional[str] = None
    ):
        self.directive_type = directive_type
        self.error_message = error_message
        self.file_path = file_path
        self.line_number = line_number
        self.content_snippet = content_snippet
        self.suggestion = suggestion
    
    def display(self) -> str:
        """Display rich error message."""
        lines = []
        lines.append(f"❌ Directive Error: {self.directive_type}")
        
        if self.file_path and self.line_number:
            lines.append(f"   File: {self.file_path}:{self.line_number}")
        
        lines.append(f"   Error: {self.error_message}")
        
        if self.content_snippet:
            lines.append("\n   Context:")
            lines.append(f"   {self.content_snippet}")
        
        if self.suggestion:
            lines.append(f"\n   💡 Suggestion: {self.suggestion}")
        
        return "\n".join(lines)
```

**Wrap directive parsing:**

```python
# In each directive parse() method, add validation and error handling
def parse(self, block, m, state):
    try:
        content = self.parse_content(m)
        
        # Validate content
        if not content.strip():
            raise DirectiveError(
                directive_type='tabs',
                error_message='Tabs directive has no content',
                suggestion='Add at least one tab: ### Tab: Title'
            )
        
        # ... rest of parsing
        
    except DirectiveError:
        raise  # Re-raise directive errors
    except Exception as e:
        # Wrap generic errors in DirectiveError
        raise DirectiveError(
            directive_type='tabs',
            error_message=f'Failed to parse tabs directive: {e}',
            suggestion='Check directive syntax and closing backticks'
        ) from e
```

#### 2.2 Pre-Parse Validation

Add validation BEFORE parsing in `bengal/rendering/plugins/directives/validator.py`:

```python
class DirectiveSyntaxValidator:
    """
    Validates directive syntax before parsing.
    
    Catches common errors early with helpful messages.
    """
    
    @staticmethod
    def validate_tabs_directive(content: str) -> List[str]:
        """Validate tabs directive content."""
        errors = []
        
        # Check for tab markers
        tab_markers = re.findall(r'^### Tab: (.+)$', content, re.MULTILINE)
        if len(tab_markers) < 2:
            errors.append(
                "Tabs directive should have at least 2 tabs. "
                "Use an admonition for single content blocks."
            )
        
        # Check for malformed markers
        bad_markers = re.findall(r'^###\s*Ta[^b]', content, re.MULTILINE)
        if bad_markers:
            errors.append(
                f"Found malformed tab markers: {bad_markers}. "
                "Use format: ### Tab: Title"
            )
        
        return errors
```

#### 2.3 Build-Time Feedback

Add directive statistics to build output:

```python
# In site.py build() method
if not quiet:
    print(f"\n📊 Directive Statistics:")
    print(f"   Total directives: {directive_count}")
    print(f"   Types: {', '.join(directive_types)}")
    if slow_pages:
        print(f"   ⚠️  {len(slow_pages)} pages with >10 directives")
```

### Phase 3: Performance (Medium Priority)

#### 3.1 Directive Content Caching

Cache parsed directive content by content hash:

```python
# bengal/rendering/plugins/directives/cache.py

class DirectiveCache:
    """
    Cache for parsed directive content.
    
    Uses content hash to detect changes and reuse parsed AST.
    """
    
    def __init__(self):
        self._cache = {}
        self._hits = 0
        self._misses = 0
    
    def get(self, directive_type: str, content: str) -> Optional[List]:
        """Get cached parsed content."""
        cache_key = f"{directive_type}:{hash(content)}"
        
        if cache_key in self._cache:
            self._hits += 1
            return self._cache[cache_key]
        
        self._misses += 1
        return None
    
    def put(self, directive_type: str, content: str, parsed: List) -> None:
        """Cache parsed content."""
        cache_key = f"{directive_type}:{hash(content)}"
        self._cache[cache_key] = parsed
    
    def stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': self._hits / (self._hits + self._misses) if self._hits + self._misses > 0 else 0,
            'size': len(self._cache)
        }

# Global cache instance (shared across all threads)
_directive_cache = DirectiveCache()
```

**Use in directives:**

```python
# tabs.py
def parse(self, block, m, state):
    content = self.parse_content(m)
    
    # Check cache first
    cached = _directive_cache.get('tabs', content)
    if cached:
        return cached
    
    # Parse...
    result = { 'type': 'tabs', 'children': tab_items }
    
    # Cache result
    _directive_cache.put('tabs', content, result)
    
    return result
```

**Expected impact:** 30-50% speedup on pages with repeated directive patterns

#### 3.2 Per-Page Timing

Add detailed timing in `RenderingPipeline.process_page()`:

```python
import time

def process_page(self, page: Page) -> None:
    start = time.perf_counter()
    
    # ... existing code ...
    
    elapsed_ms = (time.perf_counter() - start) * 1000
    
    # Track slow pages
    if elapsed_ms > 200:  # More than 200ms
        if self.build_stats:
            self.build_stats.add_slow_page(page.source_path, elapsed_ms)
    
    # Verbose mode: show timing for all pages
    if not self.quiet and self.site.config.get('verbose', False):
        print(f"  ✓ {page.source_path.name}: {elapsed_ms:.1f}ms")
```

#### 3.3 Directive Profiling

Add profiling mode for directives:

```bash
# New CLI option
bengal build --profile-directives
```

**Output:**
```
🔬 Directive Performance Profile:

Slowest Pages:
  1. strings.md: 623ms (21 tabs, 4 admonitions)
  2. collections.md: 487ms (15 tabs, 6 admonitions)
  3. kitchen-sink.md: 412ms (8 tabs, 9 admonitions, 3 dropdowns)

Directive Timing:
  - tabs: avg 45ms (53 instances)
  - admonitions: avg 8ms (42 instances)
  - dropdown: avg 12ms (28 instances)
  - code-tabs: avg 18ms (14 instances)

Cache Statistics:
  - Hit rate: 23.4%
  - Saved time: ~890ms
  - Cache size: 47 entries
```

#### 3.4 Nesting Depth Limit

Prevent exponential complexity from deep nesting:

```python
MAX_DIRECTIVE_NESTING = 5

def parse(self, block, m, state):
    # Track nesting depth
    if not hasattr(state, 'directive_depth'):
        state.directive_depth = 0
    
    state.directive_depth += 1
    
    if state.directive_depth > MAX_DIRECTIVE_NESTING:
        raise DirectiveError(
            directive_type='tabs',
            error_message=f'Directive nesting too deep (>{MAX_DIRECTIVE_NESTING} levels)',
            suggestion='Flatten your content structure or split into multiple pages'
        )
    
    try:
        # ... parse ...
    finally:
        state.directive_depth -= 1
```

---

## 📋 Implementation Checklist

### Phase 1: Health Checks

- [ ] Create `bengal/health/validators/directives.py`
  - [ ] `DirectiveValidator` class
  - [ ] `_check_directive_syntax()` method
  - [ ] `_check_directive_completeness()` method
  - [ ] `_check_directive_performance()` method
- [ ] Add directive checks to `RenderingValidator`
  - [ ] `_check_directive_rendering()` method
- [ ] Register `DirectiveValidator` in `bengal/health/validators/__init__.py`
- [ ] Add directive validator config to `bengal.toml` schema
- [ ] Write tests for `DirectiveValidator`

### Phase 2: Ergonomics

- [ ] Create `bengal/rendering/plugins/directives/errors.py`
  - [ ] `DirectiveError` exception class
  - [ ] `display_directive_error()` function
- [ ] Enhance each directive with error handling:
  - [ ] `tabs.py` - validate tab markers
  - [ ] `admonitions.py` - validate type
  - [ ] `dropdown.py` - validate title
  - [ ] `code_tabs.py` - validate code blocks
- [ ] Create `bengal/rendering/plugins/directives/validator.py`
  - [ ] `DirectiveSyntaxValidator` class
  - [ ] Pre-parse validation methods
- [ ] Add directive statistics to build output
- [ ] Update documentation with directive error examples

### Phase 3: Performance

- [ ] Create `bengal/rendering/plugins/directives/cache.py`
  - [ ] `DirectiveCache` class
  - [ ] Cache statistics tracking
- [ ] Add caching to each directive
- [ ] Add per-page timing to `RenderingPipeline`
- [ ] Create `--profile-directives` CLI option
- [ ] Add nesting depth limits
- [ ] Document performance best practices

### Testing

- [ ] Unit tests for `DirectiveValidator`
- [ ] Integration tests for directive error reporting
- [ ] Performance benchmarks with/without caching
- [ ] Test edge cases:
  - [ ] Empty directive blocks
  - [ ] Malformed tab markers
  - [ ] Deep nesting (>5 levels)
  - [ ] Very large directive blocks (>1000 lines)
  - [ ] Mixed directive types

---

## 📊 Expected Impact

### Health Checks

**Before:**
- Silent directive failures
- No validation of directive structure
- No performance warnings

**After:**
- ✅ Catch 95% of directive errors before deployment
- ✅ Clear warnings for performance-heavy pages
- ✅ Statistics on directive usage

### Ergonomics

**Before:**
```
Warning: Mistune parsing error: list index out of range
```

**After:**
```
❌ Directive Error: tabs
   File: docs/api/functions.md:127
   Error: Malformed tab marker on line 129
   
   Context:
   127 | ### Tab: Python
   128 | Content here...
   129 | ### Ta: JavaScript  ← Should be "### Tab:"
   
   💡 Suggestion: Check tab marker syntax (### Tab: Title)
```

### Performance

**Current:** 7.21 seconds for 57 pages (showcase site)

**With caching:** ~5.0 seconds (30% improvement)
- Cache hit rate: ~25-30% on complex docs
- Saves ~2 seconds on showcase site
- Bigger impact on incremental builds

**With all optimizations:** ~4.5 seconds (38% improvement)

---

## 🎯 Success Metrics

1. **Health Checks**
   - Catch 95%+ of directive errors before build
   - Zero false positives on valid directives
   - Performance warnings on pages >10 directives

2. **Ergonomics**
   - Error messages show file + line number
   - Clear suggestions for fixing errors
   - Build output shows directive statistics

3. **Performance**
   - 30%+ speedup on directive-heavy pages with caching
   - Incremental builds only re-parse changed directives
   - Profiling mode identifies bottlenecks

---

## 🚀 Next Steps

1. **Start with Phase 1** (Health Checks)
   - Highest ROI for catching bugs
   - Relatively easy to implement
   - Immediate value to users

2. **Then Phase 2** (Ergonomics)
   - Makes debugging much easier
   - Improves developer experience
   - Sets foundation for better docs

3. **Finally Phase 3** (Performance)
   - Requires careful benchmarking
   - Most complex to implement
   - But biggest impact on large sites

**Estimated timeline:**
- Phase 1: 4-6 hours
- Phase 2: 6-8 hours
- Phase 3: 8-10 hours
- **Total: 18-24 hours** for complete implementation

---

## 📝 Related Documents

- `plan/SHOWCASE_PERFORMANCE_ANALYSIS.md` - Performance baseline
- `plan/completed/MARKDOWN_PARSER_CONFIGURATION_FIX.md` - Parser config
- `ARCHITECTURE.md` - System architecture
- `bengal/health/validators/rendering.py` - Existing rendering validator
- `bengal/rendering/plugins/directives/` - Directive implementations

---

**Status:** ✅ Plan Complete - Ready for Implementation

