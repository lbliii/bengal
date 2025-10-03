# Template Functions Analysis & Implementation Plan

## Executive Summary

**Current State**: Bengal has minimal template functionality (1 filter, 3 global functions)  
**Goal**: Implement a comprehensive template function library comparable to Hugo/Jekyll  
**Impact**: Enhanced developer experience, feature parity with leading SSGs, increased adoption

---

## 1. Current State Analysis

### What Bengal Currently Has

From `bengal/rendering/template_engine.py`:

**Custom Filters (1):**
- `dateformat` - Format dates with strftime syntax

**Global Functions (3):**
- `url_for(page)` - Generate clean URLs for pages
- `asset_url(path)` - Generate asset URLs
- `get_menu(menu_name)` - Get menu items

**Built-in Jinja2 Features:**
- Standard Jinja2 filters (upper, lower, capitalize, title, length, truncate, join, first, last)
- Template inheritance (extends, block)
- Includes and imports
- Control structures (if, for, etc.)

### Gap Analysis

Bengal is **significantly behind** Hugo and Jekyll in template functionality. Missing categories:
- ❌ String manipulation functions (beyond basic Jinja2)
- ❌ Math/arithmetic functions
- ❌ Collection manipulation (where, sort, group_by, etc.)
- ❌ Content transformation (markdownify, htmlEscape, truncatewords)
- ❌ URL manipulation (beyond basic url_for)
- ❌ File system functions (readFile, fileExists)
- ❌ Image processing functions
- ❌ Taxonomy helpers
- ❌ Data manipulation functions

---

## 2. Competitive Analysis

### Hugo Template Functions

Hugo provides **200+ template functions** organized into categories:

#### String Functions (~30 functions)
- `upper`, `lower`, `title` - Case transformations
- `replace`, `replaceRE` - String replacement (regex support)
- `substr`, `slice` - Substring extraction
- `trim`, `trimPrefix`, `trimSuffix` - Whitespace/string trimming
- `truncate` - Truncate with ellipsis
- `strings.Count`, `strings.Contains` - String inspection
- `strings.Split`, `strings.Join` - String splitting/joining
- `chomp` - Remove trailing newline
- `humanize` - Make strings human-readable
- `pluralize`, `singularize` - Pluralization

#### Math Functions (~20 functions)
- `add`, `sub`, `mul`, `div`, `mod` - Basic arithmetic
- `math.Ceil`, `math.Floor`, `math.Round` - Rounding
- `math.Max`, `math.Min` - Min/max
- `math.Pow`, `math.Sqrt` - Advanced math
- `math.Log` - Logarithms

#### Collections Functions (~40 functions)
- `where` - Filter collections by criteria
- `first`, `last`, `after` - Select items
- `sort`, `reverse` - Sorting
- `group` - Group by field
- `shuffle` - Randomize order
- `uniq`, `complement`, `intersect`, `union` - Set operations
- `index` - Access nested data
- `slice` - Array slicing
- `append`, `merge` - Array manipulation
- `delimit` - Join with delimiter

#### Date/Time Functions (~10 functions)
- `time` - Parse time
- `now` - Current time
- `dateFormat` - Format dates
- `duration` - Calculate duration

#### URL Functions (~10 functions)
- `absURL`, `relURL` - Absolute/relative URLs
- `ref`, `relref` - Content references
- `urlize` - Convert to URL-safe string

#### Content Functions (~15 functions)
- `markdownify` - Render markdown to HTML
- `plainify` - Strip HTML tags
- `htmlEscape`, `htmlUnescape` - HTML entity escaping
- `safeHTML`, `safeCSS`, `safeJS` - Mark as safe
- `emojify` - Convert emoji codes

#### Conditional Functions (~10 functions)
- `default` - Provide default value
- `cond` - Ternary operator
- `echoParam` - Echo parameter with default

#### Data Functions (~15 functions)
- `getJSON`, `getCSV` - Fetch remote data
- `readFile`, `readDir` - Read local files
- `fileExists` - Check file existence
- `resources.Get`, `resources.Match` - Resource handling

#### Image Functions (~20 functions)
- `images.Resize` - Resize images
- `images.Fit`, `images.Fill` - Fit to dimensions
- `images.Filter` - Apply filters (blur, brightness, etc.)
- `images.Overlay` - Overlay images

#### Debugging Functions (~5 functions)
- `printf`, `warnf`, `errorf` - Formatted output
- `debug.Dump` - Dump variables

### Jekyll Liquid Filters

Jekyll provides **60+ filters** organized by type:

#### String Filters
- `upcase`, `downcase`, `capitalize` - Case transformations
- `replace`, `replace_first`, `remove`, `remove_first` - String replacement
- `append`, `prepend` - String concatenation
- `strip`, `lstrip`, `rstrip` - Whitespace trimming
- `strip_html`, `strip_newlines` - Content cleaning
- `truncate`, `truncatewords` - Truncation
- `url_encode`, `url_decode` - URL encoding
- `slugify` - URL-safe slugs
- `markdownify` - Render markdown
- `smartify` - Smart quotes

#### Array/Collection Filters
- `join` - Join array elements
- `sort`, `sort_natural` - Sorting
- `where`, `where_exp` - Filtering
- `group_by`, `group_by_exp` - Grouping
- `first`, `last` - Select items
- `map` - Extract field from objects
- `push`, `pop`, `shift`, `unshift` - Array manipulation
- `uniq` - Remove duplicates
- `compact` - Remove nil values
- `concat` - Concatenate arrays
- `reverse` - Reverse array
- `size` - Get array size

#### Date Filters
- `date` - Format dates
- `date_to_xmlschema` - ISO 8601 format
- `date_to_rfc822` - RFC 822 format
- `date_to_string`, `date_to_long_string` - Human-readable dates

#### Math Filters
- `plus`, `minus`, `times`, `divided_by` - Basic arithmetic
- `modulo` - Modulo operation
- `abs` - Absolute value
- `ceil`, `floor`, `round` - Rounding

#### URL Filters
- `relative_url`, `absolute_url` - URL generation
- `link` - Generate link tag

### Eleventy (11ty)

Eleventy is more flexible, allowing multiple templating engines. For Nunjucks/Liquid:
- Similar filter set to Jekyll
- Extensible with custom filters
- Shortcodes for reusable components

### Pelican (Python-based, Jinja2)

Pelican uses Jinja2 like Bengal, and adds:
- `strftime` - Date formatting
- `pygments_highlight` - Syntax highlighting
- `markdown` - Markdown rendering
- `filesizeformat` - Human-readable file sizes

**Key Insight**: Pelican's approach is most relevant to Bengal since both use Jinja2.

---

## 3. Strategic Recommendations

### Phased Approach

Given Bengal's current state, I recommend a **3-phase implementation**:

#### Phase 1: Essential Functions (High Priority)
Focus on the most commonly used functions that provide immediate value.

#### Phase 2: Advanced Functions (Medium Priority)
Add sophisticated functions for power users.

#### Phase 3: Specialized Functions (Low Priority)
Complete feature parity with edge case functions.

### Design Principles

1. **Jinja2-Native**: Leverage Jinja2's existing capabilities, don't reinvent
2. **Pythonic**: Follow Python conventions and idioms
3. **Performance**: Optimize hot-path functions, cache where appropriate
4. **Documentation**: Each function needs clear docs with examples
5. **Testing**: Every function must have unit tests
6. **Backwards Compatible**: Existing templates must continue working

---

## 4. Implementation Plan

### Phase 1: Essential Functions (Priority: HIGH)

**Timeline**: 1-2 weeks  
**Target**: 30 most-used functions

#### 1.1 String Functions (10 functions)

```python
# bengal/rendering/template_functions/strings.py

def truncatewords(text: str, count: int, suffix: str = "...") -> str:
    """Truncate text to word count."""
    words = text.split()
    if len(words) <= count:
        return text
    return " ".join(words[:count]) + suffix

def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    import re
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text

def markdownify(text: str) -> str:
    """Render markdown to HTML."""
    from markdown import markdown
    return markdown(text, extensions=['extra', 'codehilite'])

def strip_html(text: str) -> str:
    """Remove HTML tags."""
    import re
    return re.sub(r'<[^>]+>', '', text)

def truncate_chars(text: str, length: int, suffix: str = "...") -> str:
    """Truncate to character length."""
    if len(text) <= length:
        return text
    return text[:length].rstrip() + suffix

def replace_regex(text: str, pattern: str, replacement: str) -> str:
    """Replace using regex."""
    import re
    return re.sub(pattern, replacement, text)

def pluralize(count: int, singular: str, plural: str = None) -> str:
    """Return plural form based on count."""
    if plural is None:
        plural = singular + 's'
    return singular if count == 1 else plural

def reading_time(text: str, wpm: int = 200) -> int:
    """Calculate reading time in minutes."""
    words = len(text.split())
    return max(1, round(words / wpm))

def excerpt(text: str, length: int = 200) -> str:
    """Extract excerpt, respecting word boundaries."""
    if len(text) <= length:
        return text
    excerpt_text = text[:length].rsplit(' ', 1)[0]
    return excerpt_text + "..."

def strip_whitespace(text: str) -> str:
    """Remove extra whitespace."""
    import re
    return re.sub(r'\s+', ' ', text).strip()
```

**Registration**:
```python
# In template_engine.py
env.filters['truncatewords'] = strings.truncatewords
env.filters['slugify'] = strings.slugify
env.filters['markdownify'] = strings.markdownify
env.filters['strip_html'] = strings.strip_html
env.filters['truncate_chars'] = strings.truncate_chars
env.filters['replace_regex'] = strings.replace_regex
env.filters['pluralize'] = strings.pluralize
env.filters['reading_time'] = strings.reading_time
env.filters['excerpt'] = strings.excerpt
env.filters['strip_whitespace'] = strings.strip_whitespace
```

#### 1.2 Collection Functions (8 functions)

```python
# bengal/rendering/template_functions/collections.py

from typing import Any, List, Dict, Callable

def where(items: List[Dict], key: str, value: Any) -> List[Dict]:
    """Filter items where key equals value."""
    return [item for item in items if item.get(key) == value]

def where_not(items: List[Dict], key: str, value: Any) -> List[Dict]:
    """Filter items where key does not equal value."""
    return [item for item in items if item.get(key) != value]

def group_by(items: List[Dict], key: str) -> Dict[Any, List[Dict]]:
    """Group items by key."""
    from itertools import groupby
    from operator import itemgetter
    
    sorted_items = sorted(items, key=itemgetter(key))
    return {k: list(g) for k, g in groupby(sorted_items, key=itemgetter(key))}

def sort_by(items: List[Dict], key: str, reverse: bool = False) -> List[Dict]:
    """Sort items by key."""
    return sorted(items, key=lambda x: x.get(key), reverse=reverse)

def limit(items: List, count: int) -> List:
    """Limit items to count."""
    return items[:count]

def offset(items: List, count: int) -> List:
    """Skip first count items."""
    return items[count:]

def uniq(items: List) -> List:
    """Remove duplicates while preserving order."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

def flatten(items: List[List]) -> List:
    """Flatten nested lists."""
    return [item for sublist in items for item in sublist]
```

#### 1.3 Math Functions (6 functions)

```python
# bengal/rendering/template_functions/math_functions.py

import math

def percentage(part: float, total: float, decimals: int = 0) -> str:
    """Calculate percentage."""
    if total == 0:
        return "0%"
    pct = (part / total) * 100
    return f"{pct:.{decimals}f}%"

def times(value: float, multiplier: float) -> float:
    """Multiply value."""
    return value * multiplier

def divided_by(value: float, divisor: float) -> float:
    """Divide value."""
    if divisor == 0:
        return 0
    return value / divisor

def ceil(value: float) -> int:
    """Round up."""
    return math.ceil(value)

def floor(value: float) -> int:
    """Round down."""
    return math.floor(value)

def round_num(value: float, decimals: int = 0) -> float:
    """Round to decimals."""
    return round(value, decimals)
```

#### 1.4 Date Functions (3 functions)

```python
# bengal/rendering/template_functions/dates.py

from datetime import datetime, timedelta
from typing import Optional

def time_ago(date: datetime) -> str:
    """Human-readable time ago."""
    now = datetime.now()
    diff = now - date
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return "just now"

def date_iso(date: datetime) -> str:
    """Format as ISO 8601."""
    return date.isoformat()

def date_rfc822(date: datetime) -> str:
    """Format as RFC 822 (for RSS)."""
    return date.strftime("%a, %d %b %Y %H:%M:%S %z")
```

#### 1.5 URL Functions (3 functions)

```python
# bengal/rendering/template_functions/urls.py

def absolute_url(url: str, base_url: str) -> str:
    """Convert to absolute URL."""
    if url.startswith(('http://', 'https://', '//')):
        return url
    return base_url.rstrip('/') + '/' + url.lstrip('/')

def url_encode(text: str) -> str:
    """URL encode string."""
    from urllib.parse import quote
    return quote(text)

def url_decode(text: str) -> str:
    """URL decode string."""
    from urllib.parse import unquote
    return unquote(text)
```

### Phase 2: Advanced Functions (Priority: MEDIUM)

**Timeline**: 2-3 weeks  
**Target**: 25 advanced functions

#### 2.1 Data Manipulation (8 functions)
- `get_data(path)` - Load JSON/YAML data files
- `jsonify(data)` - Convert to JSON string
- `merge(dict1, dict2)` - Deep merge dictionaries
- `has_key(dict, key)` - Check for key existence
- `get_nested(dict, path)` - Access nested data (e.g., "user.profile.name")
- `keys(dict)` - Get dictionary keys
- `values(dict)` - Get dictionary values
- `items(dict)` - Get key-value pairs

#### 2.2 Content Transformation (6 functions)
- `safe_html(text)` - Mark HTML as safe
- `html_escape(text)` - Escape HTML entities
- `html_unescape(text)` - Unescape HTML entities
- `nl2br(text)` - Convert newlines to `<br>`
- `smartquotes(text)` - Smart quotes/apostrophes
- `emojify(text)` - Convert `:emoji:` codes

#### 2.3 Advanced String Functions (5 functions)
- `camelize(text)` - Convert to camelCase
- `underscore(text)` - Convert to snake_case
- `titleize(text)` - Proper title case
- `wrap(text, width)` - Word wrap text
- `indent(text, spaces)` - Indent text

#### 2.4 File System Functions (3 functions)
- `read_file(path)` - Read file contents
- `file_exists(path)` - Check if file exists
- `file_size(path)` - Get file size (human-readable)

#### 2.5 Advanced Collection Functions (3 functions)
- `sample(items, count)` - Random sample
- `shuffle(items)` - Randomize order
- `chunk(items, size)` - Split into chunks

### Phase 3: Specialized Functions (Priority: LOW)

**Timeline**: 1-2 weeks  
**Target**: 20 specialized functions

#### 3.1 Image Functions (6 functions)
- `image_resize(path, width, height)` - Resize image
- `image_thumb(path, size)` - Generate thumbnail
- `image_dimensions(path)` - Get width/height
- `image_url(path, params)` - Generate image URL with params
- `image_srcset(path, sizes)` - Generate srcset attribute
- `image_optimize(path)` - Optimize image

#### 3.2 SEO Functions (4 functions)
- `meta_description(text, length)` - Generate meta description
- `meta_keywords(tags)` - Generate meta keywords
- `canonical_url(page)` - Generate canonical URL
- `og_image(image)` - Generate Open Graph image URL

#### 3.3 Debug Functions (3 functions)
- `debug(var)` - Pretty-print variable
- `typeof(var)` - Get variable type
- `inspect(object)` - Inspect object attributes

#### 3.4 Taxonomy Functions (4 functions)
- `related_posts(page, limit)` - Get related posts by tags
- `popular_tags(limit)` - Get most popular tags
- `tag_url(tag)` - Generate tag page URL
- `has_tag(page, tag)` - Check if page has tag

#### 3.5 Pagination Functions (3 functions)
- `paginate(items, per_page)` - Paginate items
- `page_url(pagination, page_num)` - Generate page URL
- `page_range(pagination, window)` - Generate page range

---

## 5. Architecture

### File Structure

```
bengal/
  rendering/
    template_engine.py          # Main template engine
    template_functions/          # NEW
      __init__.py               # Function registration
      strings.py                # String functions
      collections.py            # Collection functions
      math_functions.py         # Math functions
      dates.py                  # Date/time functions
      urls.py                   # URL functions
      data.py                   # Data manipulation
      content.py                # Content transformation
      files.py                  # File system functions
      images.py                 # Image processing
      seo.py                    # SEO helpers
      debug.py                  # Debug utilities
      taxonomies.py             # Taxonomy helpers
```

### Registration System

```python
# bengal/rendering/template_functions/__init__.py

from . import (
    strings,
    collections,
    math_functions,
    dates,
    urls,
    data,
    content,
    files,
    images,
    seo,
    debug,
    taxonomies,
)

def register_filters(env, site):
    """Register all custom filters with Jinja2 environment."""
    
    # String functions
    env.filters.update({
        'truncatewords': strings.truncatewords,
        'slugify': strings.slugify,
        'markdownify': strings.markdownify,
        'strip_html': strings.strip_html,
        'truncate_chars': strings.truncate_chars,
        'replace_regex': strings.replace_regex,
        'pluralize': strings.pluralize,
        'reading_time': strings.reading_time,
        'excerpt': strings.excerpt,
        'strip_whitespace': strings.strip_whitespace,
    })
    
    # Collection functions
    env.filters.update({
        'where': collections.where,
        'where_not': collections.where_not,
        'group_by': collections.group_by,
        'sort_by': collections.sort_by,
        'limit': collections.limit,
        'offset': collections.offset,
        'uniq': collections.uniq,
        'flatten': collections.flatten,
    })
    
    # Math functions
    env.filters.update({
        'percentage': math_functions.percentage,
        'times': math_functions.times,
        'divided_by': math_functions.divided_by,
        'ceil': math_functions.ceil,
        'floor': math_functions.floor,
        'round': math_functions.round_num,
    })
    
    # Date functions
    env.filters.update({
        'time_ago': dates.time_ago,
        'date_iso': dates.date_iso,
        'date_rfc822': dates.date_rfc822,
    })
    
    # URL functions
    env.filters.update({
        'absolute_url': lambda url: urls.absolute_url(url, site.baseurl),
        'url_encode': urls.url_encode,
        'url_decode': urls.url_decode,
    })
    
    # ... more phases as they're implemented

def register_globals(env, site):
    """Register global functions with Jinja2 environment."""
    
    # Keep existing globals
    env.globals['url_for'] = lambda page: page.url if hasattr(page, 'url') else f"/{page.slug}/"
    env.globals['asset_url'] = lambda path: f"/assets/{path}"
    env.globals['get_menu'] = lambda name='main': [item.to_dict() for item in site.menu.get(name, [])]
    
    # Add new globals (Phase 2+)
    # env.globals['get_data'] = lambda path: data.get_data(site.root_path / path)
    # env.globals['file_exists'] = lambda path: files.file_exists(site.root_path / path)
```

### Updated Template Engine

```python
# bengal/rendering/template_engine.py

from bengal.rendering.template_functions import register_filters, register_globals

class TemplateEngine:
    def _create_environment(self) -> Environment:
        # ... existing code ...
        
        # Register all custom filters and globals
        register_filters(env, self.site)
        register_globals(env, self.site)
        
        return env
```

---

## 6. Testing Strategy

### Unit Tests

Each function must have comprehensive unit tests:

```python
# tests/unit/template_functions/test_strings.py

import pytest
from bengal.rendering.template_functions.strings import truncatewords, slugify

class TestTruncatewords:
    def test_truncate_long_text(self):
        text = "This is a long piece of text with many words"
        result = truncatewords(text, 5)
        assert result == "This is a long piece..."
    
    def test_no_truncate_short_text(self):
        text = "Short text"
        result = truncatewords(text, 5)
        assert result == "Short text"
    
    def test_custom_suffix(self):
        text = "This is a long piece of text"
        result = truncatewords(text, 3, " [more]")
        assert result == "This is a [more]"

class TestSlugify:
    def test_basic_slug(self):
        assert slugify("Hello World") == "hello-world"
    
    def test_special_chars(self):
        assert slugify("Hello, World!") == "hello-world"
    
    def test_unicode(self):
        assert slugify("Héllo Wörld") == "hllo-wrld"
    
    def test_multiple_spaces(self):
        assert slugify("Hello    World") == "hello-world"
```

### Integration Tests

Test functions in actual templates:

```python
# tests/integration/test_template_functions.py

from bengal.rendering.template_engine import TemplateEngine

def test_truncatewords_in_template(site):
    engine = TemplateEngine(site)
    template = "{{ text | truncatewords(5) }}"
    result = engine.render_string(template, {
        'text': 'This is a long piece of text with many words'
    })
    assert result == "This is a long piece..."

def test_filter_chaining(site):
    engine = TemplateEngine(site)
    template = "{{ text | strip_html | truncatewords(3) }}"
    result = engine.render_string(template, {
        'text': '<p>This is a long piece of text</p>'
    })
    assert result == "This is a..."
```

### Coverage Target

- **Phase 1**: 95% coverage for essential functions
- **Phase 2**: 90% coverage for advanced functions
- **Phase 3**: 85% coverage for specialized functions

---

## 7. Documentation Plan

### Template Function Reference

Create comprehensive documentation:

```markdown
# Template Function Reference

## String Functions

### truncatewords

Truncates text to a specified number of words.

**Syntax:**
```jinja2
{{ text | truncatewords(count, suffix="...") }}
```

**Parameters:**
- `count` (int): Number of words to keep
- `suffix` (str, optional): Text to append. Default: "..."

**Examples:**
```jinja2
{{ post.content | truncatewords(50) }}
# Output: First 50 words...

{{ post.content | truncatewords(30, " [Read more]") }}
# Output: First 30 words [Read more]
```

**Use Cases:**
- Blog post excerpts
- Preview text
- Search results
```

### User Guide

Add section to quickstart:

```markdown
## Using Template Functions

Bengal provides 50+ template functions to help you build powerful templates.

### String Manipulation

```jinja2
{{ page.title | slugify }}              # hello-world
{{ page.content | truncatewords(50) }}  # First 50 words...
{{ page.content | reading_time }}       # 5 (minutes)
{{ markdown_text | markdownify }}       # Rendered HTML
```

### Collections

```jinja2
{% set tutorials = site.pages | where('category', 'tutorial') %}
{% set recent = site.pages | sort_by('date', reverse=true) | limit(5) %}
{% set tags = site.pages | group_by('category') %}
```

### Math

```jinja2
{{ 42.7 | ceil }}                       # 43
{{ 50 | percentage(200) }}              # 25%
{{ price | times(1.1) }}                # Price with 10% tax
```
```

---

## 8. Migration Path

### Backwards Compatibility

All existing templates continue to work. New functions are additive only.

### Deprecation Policy

If we need to change/remove a function:
1. Mark as deprecated in docs
2. Log warning when used
3. Provide migration guide
4. Remove after 2 major versions

---

## 9. Performance Considerations

### Caching

Functions that are expensive should cache results:

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def markdownify(text: str) -> str:
    """Render markdown (cached)."""
    from markdown import markdown
    return markdown(text, extensions=['extra', 'codehilite'])
```

### Lazy Evaluation

Some functions should evaluate lazily:

```python
def where(items: List[Dict], key: str, value: Any) -> Iterator[Dict]:
    """Filter items (lazy iterator)."""
    return (item for item in items if item.get(key) == value)
```

### Benchmarks

Track performance of hot-path functions:
- `where`, `sort_by` - Used frequently in loops
- `markdownify` - Heavy computation
- `truncatewords` - Common in listings

Target: No function should take > 1ms for typical input.

---

## 10. Success Metrics

### Adoption Metrics
- **Documentation views** - Track most-viewed function docs
- **Template usage** - Log which functions are used most
- **GitHub issues** - Track function-related questions/bugs

### Feature Parity
- ✅ Phase 1: 30 essential functions → **85% of common use cases**
- ✅ Phase 2: +25 advanced functions → **95% of use cases**
- ✅ Phase 3: +20 specialized → **99% feature parity with Hugo/Jekyll**

### Quality Metrics
- ✅ 90%+ test coverage
- ✅ < 1ms per function (P95)
- ✅ Zero breaking changes to existing templates

---

## 11. Timeline & Resources

### Phase 1: Essential Functions (Weeks 1-2)
- **Week 1**: Implement & test string/collection functions
- **Week 2**: Implement & test math/date/URL functions
- **Deliverable**: 30 production-ready functions

### Phase 2: Advanced Functions (Weeks 3-5)
- **Week 3**: Data manipulation & content transformation
- **Week 4**: Advanced string & file system functions
- **Week 5**: Advanced collection functions & testing
- **Deliverable**: 55 total functions

### Phase 3: Specialized Functions (Weeks 6-7)
- **Week 6**: Image & SEO functions
- **Week 7**: Debug, taxonomy, pagination functions
- **Deliverable**: 75 total functions

### Documentation (Week 8)
- Write comprehensive function reference
- Update user guide
- Create example templates
- **Deliverable**: Complete documentation

### Total Timeline: **8 weeks**

---

## 12. Risks & Mitigations

### Risk 1: Performance Degradation
**Impact**: High  
**Probability**: Medium  
**Mitigation**: Benchmark all functions, cache expensive operations, use lazy evaluation

### Risk 2: Breaking Changes
**Impact**: High  
**Probability**: Low  
**Mitigation**: Strict backwards compatibility policy, comprehensive testing

### Risk 3: Maintenance Burden
**Impact**: Medium  
**Probability**: Medium  
**Mitigation**: Excellent test coverage, clear documentation, modular architecture

### Risk 4: Feature Bloat
**Impact**: Medium  
**Probability**: Low  
**Mitigation**: Only implement well-justified functions, track usage metrics

---

## 13. Next Steps

1. **Review & Approve**: Get stakeholder sign-off on this plan
2. **Setup Infrastructure**: Create `template_functions/` module structure
3. **Begin Phase 1**: Start with string functions (highest value)
4. **Iterate**: Get feedback from real usage, adjust priorities
5. **Document**: Write docs as we implement, not after

---

## Appendix A: Complete Function List

### Phase 1: Essential (30 functions)

**String Functions (10):**
- `truncatewords(text, count, suffix)` - Truncate to word count
- `slugify(text)` - URL-safe slug
- `markdownify(text)` - Render markdown
- `strip_html(text)` - Remove HTML tags
- `truncate_chars(text, length, suffix)` - Truncate to char count
- `replace_regex(text, pattern, replacement)` - Regex replace
- `pluralize(count, singular, plural)` - Pluralization
- `reading_time(text, wpm)` - Reading time in minutes
- `excerpt(text, length)` - Smart excerpt extraction
- `strip_whitespace(text)` - Remove extra whitespace

**Collection Functions (8):**
- `where(items, key, value)` - Filter by equality
- `where_not(items, key, value)` - Filter by inequality
- `group_by(items, key)` - Group items
- `sort_by(items, key, reverse)` - Sort items
- `limit(items, count)` - Limit count
- `offset(items, count)` - Skip count
- `uniq(items)` - Remove duplicates
- `flatten(items)` - Flatten nested lists

**Math Functions (6):**
- `percentage(part, total, decimals)` - Calculate percentage
- `times(value, multiplier)` - Multiply
- `divided_by(value, divisor)` - Divide
- `ceil(value)` - Round up
- `floor(value)` - Round down
- `round(value, decimals)` - Round

**Date Functions (3):**
- `time_ago(date)` - Human-readable time
- `date_iso(date)` - ISO 8601 format
- `date_rfc822(date)` - RFC 822 format

**URL Functions (3):**
- `absolute_url(url, base)` - Absolute URL
- `url_encode(text)` - URL encode
- `url_decode(text)` - URL decode

### Phase 2: Advanced (25 functions)

**Data Manipulation (8):**
- `get_data(path)`, `jsonify(data)`, `merge(dict1, dict2)`, `has_key(dict, key)`, `get_nested(dict, path)`, `keys(dict)`, `values(dict)`, `items(dict)`

**Content Transformation (6):**
- `safe_html(text)`, `html_escape(text)`, `html_unescape(text)`, `nl2br(text)`, `smartquotes(text)`, `emojify(text)`

**Advanced String (5):**
- `camelize(text)`, `underscore(text)`, `titleize(text)`, `wrap(text, width)`, `indent(text, spaces)`

**File System (3):**
- `read_file(path)`, `file_exists(path)`, `file_size(path)`

**Advanced Collections (3):**
- `sample(items, count)`, `shuffle(items)`, `chunk(items, size)`

### Phase 3: Specialized (20 functions)

**Image (6):**
- `image_resize`, `image_thumb`, `image_dimensions`, `image_url`, `image_srcset`, `image_optimize`

**SEO (4):**
- `meta_description`, `meta_keywords`, `canonical_url`, `og_image`

**Debug (3):**
- `debug`, `typeof`, `inspect`

**Taxonomy (4):**
- `related_posts`, `popular_tags`, `tag_url`, `has_tag`

**Pagination (3):**
- `paginate`, `page_url`, `page_range`

---

## Appendix B: Example Templates

### Before (Current Bengal)

```jinja2
{% extends "base.html" %}

{% block content %}
<h1>{{ page.title }}</h1>
<time>{{ page.date | dateformat('%Y-%m-%d') }}</time>
<div>{{ content }}</div>

<h2>Recent Posts</h2>
{% for post in site.pages %}
  {% if post.metadata.type == 'post' %}
    <article>
      <h3>{{ post.title }}</h3>
    </article>
  {% endif %}
{% endfor %}
{% endblock %}
```

### After (With New Functions)

```jinja2
{% extends "base.html" %}

{% block content %}
<h1>{{ page.title }}</h1>
<time>{{ page.date | time_ago }}</time>
<span>{{ page.content | reading_time }} min read</span>

<div class="excerpt">
  {{ page.content | strip_html | excerpt(200) }}
</div>

<h2>Recent Posts</h2>
{% set recent_posts = site.pages 
   | where('type', 'post') 
   | sort_by('date', reverse=true) 
   | limit(5) %}

{% for post in recent_posts %}
  <article>
    <h3><a href="{{ url_for(post) }}">{{ post.title }}</a></h3>
    <time>{{ post.date | time_ago }}</time>
    <p>{{ post.content | truncatewords(30) }}</p>
  </article>
{% endfor %}

<h2>Popular Tags</h2>
{% set tag_counts = site.pages | group_by('tags') %}
{% for tag, posts in tag_counts.items() | sort_by('1', reverse=true) | limit(10) %}
  <a href="/tags/{{ tag | slugify }}/">
    {{ tag }} ({{ posts | length }})
  </a>
{% endfor %}
{% endblock %}
```

**Benefits:**
- ✅ Cleaner, more expressive templates
- ✅ Less Python code in templates
- ✅ More powerful filtering and transformation
- ✅ Better readability and maintainability

---

**Document Status**: Draft for Review  
**Author**: AI Analysis  
**Date**: October 3, 2025  
**Next Review**: After Phase 1 Implementation

