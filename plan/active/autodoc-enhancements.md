# Autodoc & Large Site Enhancements

## Discovered from NeMo Microservices SDK Project

Testing Bengal on a real-world SDK project (1300+ pages, 915 autodoc modules) revealed several enhancement opportunities.

---

## 1. Better Default Titles for `_index.md` Files ⭐

### Problem
When auto-generated `_index.md` files lack titles in frontmatter, Bengal uses the filename stem (`_index`) which gets titled to **"Index"**. This shows up everywhere:

```html
<!-- Current behavior -->
<title>Index - Site Name</title>  <!-- Not helpful! -->
<h1>Index</h1>
<nav><a href="/api/">Index</a></nav>  <!-- Says "Index" for API section -->
```

### Solution
For `_index.md` files specifically, use the **parent directory name** humanized:

```python
# In bengal/core/page/metadata.py
@property
def title(self) -> str:
    """Get page title from metadata or generate from filename."""
    if "title" in self.metadata:
        return self.metadata["title"]

    # Special handling for _index.md files
    if self.source_path.stem == "_index":
        # Use humanized directory name: "api" → "Api", "data-designer" → "Data Designer"
        dir_name = self.source_path.parent.name
        return dir_name.replace("-", " ").replace("_", " ").title()

    # Regular pages use filename
    return self.source_path.stem.replace("-", " ").title()
```

### Impact
- ✅ `/api/` shows "Api" instead of "Index"
- ✅ `/api/data-designer/` shows "Data Designer" instead of "Index"
- ✅ Better SEO, navigation, and breadcrumbs
- ✅ Works for all auto-generated section indexes (autodoc, manual sections, etc.)

### Implementation Priority
**HIGH** - This is user-facing and affects every section without explicit titles

---

## 2. Autodoc Index Page Generation

### Problem
Autodoc generates 915 individual module pages but **no `_index.md` files** for directories. Section finalization creates empty archive pages, but they don't provide:
- Overview of what's in the section
- API organization/grouping
- Search/filter interface

### Solution
Add optional index page generation to autodoc:

```toml
[autodoc.python]
generate_index_pages = true  # Default: false
index_template = "api-index"  # Template for generated indexes
```

Generated `_index.md` could include:
```markdown
---
title: "Apps API"
type: api-section
---

# Apps API

Manage app tasks and operations.

## Modules

- [apps.apps](apps.md) - Core apps resource
- [task.py](task.md) - Task management
- [tasks.py](tasks.md) - Task collections

## Classes

- `AppsResource` - Main apps API client
- `Task` - Represents a single task
- `TasksPage` - Paginated task results
```

### Implementation Priority
**MEDIUM** - Improves UX but workaround exists (manual `_index.md` files)

---

## 3. Smarter Content Type Detection for API Docs

### Current Behavior
Auto-generated API sections get detected as generic content, which may not use the best template.

### Enhancement
Add explicit API content type detection:

```python
# In bengal/content_types/detection.py
def detect_content_type(section: Section) -> str:
    # Check metadata hint
    if any(p.metadata.get("type") == "python-module" for p in section.pages[:5]):
        return "api-reference"

    # Check directory patterns
    if section.path.name in ("api", "reference", "sdk"):
        return "api-reference"

    # ... existing detection logic
```

Then use specialized templates:
```toml
[content_types.api-reference]
template = "api/list.html"
sort_by = "alphabetical"  # Not chronological like blog
paginate = false  # Usually want full list
```

### Implementation Priority
**LOW** - Nice-to-have, not critical

---

## 4. Handle Pages with Invalid Output Paths ✅ FIXED

### Problem Found
Some pages ended up with `output_path = Path('.')` causing crashes:
```
PosixPath('.') has an empty name
'.' is not in the subpath of '.../public'
```

### Solution
Added defensive validation in `output_formats.py` (committed: `ee495be`)

---

## 5. Large Site Performance Optimizations

### Observations from 1300+ Page Build

**Current Performance:**
- Build time: ~13-20s (full rebuild)
- Throughput: 66-99 pages/second
- Discovery: 145ms ✅
- Rendering: 3.5-8.7s ⚠️
- Assets: 1.3s
- Postprocess: 272ms-1.66s

### Bottlenecks
1. **Rendering** - Most expensive phase
2. **Output formats** - Generating 1300+ JSON/txt files

### Potential Optimizations

#### A. Lazy Template Loading
```python
# Don't load all templates upfront for large sites
class TemplateEngine:
    def __init__(self, lazy=True):
        if lazy:
            self._template_cache = {}  # Load on demand
        else:
            self._preload_templates()  # Current behavior
```

#### B. Batched Output Format Generation
```python
# Write output formats in batches instead of one-by-one
def _generate_page_json_batch(self, pages: list[Page]) -> int:
    # Process 100 pages at a time with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(self._write_json, page) for page in pages]
        return sum(f.result() for f in futures)
```

#### C. Skip Unchanged Pages in Incremental Builds
Already implemented via PageProxy! ✅

### Implementation Priority
**DEFER** - Current performance is acceptable for 1300 pages

---

## 6. Better Autodoc Module Organization

### Problem
Flat structure for 915 modules is hard to navigate:
```
/api/
  apps.md
  audit.md
  beta.md
  ... 912 more files
```

### Solution Option 1: Preserve Package Structure
```
/api/
  nemo_microservices/
    resources/
      intake/
        apps/
          apps.md
          tasks.md
```

### Solution Option 2: Group by Type
```
/api/
  clients/
    apps.md
    audit.md
  types/
    task.md
    config.md
  utils/
    ...
```

### Implementation
Add to autodoc config:
```toml
[autodoc.python]
preserve_structure = true  # Keep original package structure
# OR
flatten_structure = false  # Same thing
```

### Implementation Priority
**LOW** - Trade-off between flat (easy to browse) vs hierarchical (matches code)

---

## 7. Template Error Resilience

### Observation
The project hit several template edge cases:
- PageProxy missing properties ✅ FIXED
- Invalid output paths ✅ FIXED
- Missing frontmatter (handled well by defaults ✅)

### Already Good
Bengal's defensive template handling is solid:
- Graceful fallbacks for missing metadata
- Clear error messages in strict mode
- Non-strict mode allows warnings without failures

---

## 8. Documentation Improvements

### What Worked Well from User's Perspective
1. ✅ Clear error messages
2. ✅ Autodoc "just worked" once config was fixed
3. ✅ Incremental builds are fast
4. ✅ Dev server with hot reload

### What Could Be Better
1. **Better examples** for large projects (sphinx migration, SDKs)
2. **Troubleshooting guide** for common issues:
   - TOML syntax errors
   - Autodoc source_dirs configuration
   - Section index generation
3. **Performance tuning guide** for 1000+ page sites

### Implementation Priority
**MEDIUM** - Good docs prevent support burden

---

## 9. Strict Mode Configuration Gotcha

### Issue
Users might add `strict_mode = false` in wrong format:
```toml
# WRONG (Python syntax in TOML)
site.config["strict_mode"] = False

# RIGHT
[site]
strict_mode = false
```

### Solution
Add config validation that gives helpful errors:
```python
# In config/validators.py
def validate_config_syntax(raw_toml: str) -> list[str]:
    errors = []
    if 'site.config[' in raw_toml:
        errors.append(
            "Found Python syntax 'site.config[...]' in TOML file. "
            "Use TOML syntax instead: [site] section with key = value"
        )
    return errors
```

### Implementation Priority
**LOW** - TOML parser already catches this, but better error would help

---

## Priority Summary

### Implement Soon (High Priority)
1. ⭐ **Better `_index.md` title defaults** - User-facing, affects all sections
2. ✅ **PageProxy navigation** - Already fixed
3. ✅ **Invalid output path handling** - Already fixed

### Consider (Medium Priority)
4. **Autodoc index page generation** - Improves API docs UX
5. **Documentation improvements** - Reduce support burden

### Future (Low Priority)
6. **Performance optimizations** - Current speed is acceptable
7. **Smarter API content type detection** - Nice-to-have
8. **Better module organization** - Trade-offs, not clearly better
9. **Config validation improvements** - TOML parser already handles it

---

## Next Steps

1. Implement `_index.md` title enhancement (30 min)
2. Add test case with autodoc-generated sections
3. Update documentation with large site examples
4. Consider autodoc index generation for v0.2

---

## Files to Modify

### For Title Enhancement
- `bengal/core/page/metadata.py` - Update `title` property
- `tests/unit/core/test_page_metadata.py` - Add tests
- `CHANGELOG.md` - Document improvement

### For Autodoc Index Generation (Future)
- `bengal/autodoc/generator.py` - Add index generation
- `bengal/autodoc/templates/python/section-index.md.jinja2` - New template
- `bengal/autodoc/config.py` - Add config options
