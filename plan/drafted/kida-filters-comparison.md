# Kida Filters: Strategic Roadmap for Best-in-Class Templating

**Status**: Ready for Implementation  
**Date**: 2025-01-27  
**Goal**: Position Kida as the most performant and ergonomic templating engine in 2025

## Executive Summary

Kida already has **80+ filters** — more comprehensive than Jinja2, Liquid, Twig, or Hugo individually. This RFC identifies **strategic gaps** and proposes additions that would make Kida definitively best-in-class.

**Current Standing**:
| Engine | Filter Count | Unique Strength | Kida Advantage |
|--------|-------------|-----------------|----------------|
| Jinja2 | ~50 | Python ecosystem | Kida has all + 30 more |
| Liquid | ~40 | URL/commerce | Kida matches + better collections |
| Twig | ~55 | PHP integration | Kida has all + pipeline operator |
| Hugo | ~100+ | Go performance | Kida matches features, better ergonomics |

**Strategic Additions** (13 filters to achieve parity+):
1. **URL Manipulation** (4): `url_parse`, `url_query`, `url_param`, `urlize`
2. **Regex Power** (2): `regex_search`, `regex_findall`  
3. **Date Arithmetic** (2): `date_add`, `date_diff`
4. **String Operations** (3): `trim_prefix`, `trim_suffix`, `contains`
5. **Collections** (2): `reduce`, `to_sentence`

---

## Current Kida Filter Inventory (Verified)

### String Filters (18 filters) ✅

**Core**:
- `upper`, `lower`, `capitalize`, `title`
- `trim`, `strip` (alias)
- `truncate`, `truncatewords`, `truncatewords_html`
- `replace`, `replace_regex`
- `slugify`, `striptags`
- `wordwrap`, `indent`, `center`
- `urlencode`, `format`

**Bengal Extensions**:
- `split` — Split string to list
- `camelize` — `hello_world` → `helloWorld`
- `underscore` — `helloWorld` → `hello_world`
- `titleize` — Smart title case with article handling
- `softwrap_ident` — Zero-width breaks for long identifiers
- `last_segment` — `a.b.c` → `c`
- `first_sentence` — Extract first sentence

### Collection Filters (26 filters) ✅

**Core**:
- `first`, `last`, `length`, `count` (alias)
- `sort`, `reverse`, `unique`
- `join`, `batch`, `slice`
- `map`, `select`, `reject`, `selectattr`, `rejectattr`
- `groupby`, `compact`

**Bengal Extensions** (Kida-exclusive):
- `sort_by` — Sort by attribute with intuitive syntax
- `where`, `where_not` — Hugo-style filtering with operators (`gt`, `lt`, `in`, `not_in`)
- `group_by`, `group_by_year`, `group_by_month` — Powerful grouping
- `take`, `skip` — Pipeline-friendly pagination (vs `limit`/`offset`)
- `union`, `intersect`, `complement` — Set operations
- `flatten` — Flatten nested lists
- `sample`, `shuffle` — Random selection with seed support
- `chunk` — Split into fixed-size chunks
- `archive_years` — Blog archive helper
- `resolve_pages` — O(1) page lookups from indexes

### Type Conversion (5 filters + 2 globals) ✅

**Filters**: `string`, `int`, `float`, `list`, `tojson`  
**Globals**: `bool`, `dict` — Available as functions, not filters

### HTML/Content Processing (12 filters) ✅

**Security**:
- `safe`, `escape`, `e` (alias)
- `striptags`, `xmlattr`

**Content Transformation**:
- `markdownify` — Markdown → HTML with docstring support
- `strip_html` — Remove HTML tags (alias: `plainify` recommended)
- `excerpt` — Smart excerpt with word boundaries
- `reading_time`, `word_count`, `wordcount`
- `nl2br` — Newlines → `<br>` tags ✅ (already exists)
- `emojify` — `:smile:` → 😊 ✅ (already exists)
- `html_escape`, `html_unescape` — Entity handling
- `smartquotes` — Curly quotes and em-dashes
- `extract_content` — Extract main content from full HTML
- `demote_headings` — Shift heading levels for embedding
- `prefix_heading_ids` — Unique IDs for embedded content

### URL Handling (5 filters) ✅

- `absolute_url`, `url` (alias)
- `href` — Apply baseurl
- `url_encode` — URL encoding
- `url_decode` — URL decoding ✅ (already exists)
- `ensure_trailing_slash`

### Date Filters (8 filters) ✅

- `dateformat`, `date` (alias) — Flexible date formatting
- `date_iso`, `date_rfc822` — Standard formats
- `time_ago` — "2 days ago" format
- `days_ago`, `months_ago` — Numeric age
- `month_name` — Month number → name
- `humanize_days` — Days → "yesterday", "2 weeks ago"

### Math Filters (8 filters) ✅

- `abs`, `round` (with `method='ceil'`/`'floor'`)
- `min`, `max`, `sum`
- `format_number`, `commas` — Thousands separators
- `filesizeformat` — Human-readable file sizes

### Debug/Utility (5 filters) ✅

- `pprint`, `debug` — Development inspection
- `get`, `attr` — Safe attribute access
- `dictsort` — Sort dict by key/value
- `require` — Fail-fast validation

---

## Competitive Analysis: What Makes Kida Unique

### Kida-Only Features (No Competitor Has)

| Feature | Description | Competitor Status |
|---------|-------------|-------------------|
| **Pipeline Operator `\|>`** | Type-safe chaining | None have it |
| **`where` with operators** | `where('date', cutoff, 'gt')` | Hugo partial, others none |
| **Set operations** | `union`, `intersect`, `complement` | Hugo only |
| **Seed-based randomization** | `sample(3, seed=42)` | None |
| **None-resilient defaults** | Graceful `None` handling | Hugo partial |
| **Strict mode** | `\| int(strict=true)` | None |
| **`softwrap_ident`** | API doc helper | None |
| **`archive_years`** | Blog archive helper | None |

### Performance Advantages

1. **Zero-copy pipeline** — `|>` operator avoids intermediate allocations
2. **O(1) page lookups** — `resolve_pages` uses cached path maps
3. **Lazy evaluation** — Generators where possible
4. **Compiled templates** — AST-based execution

---

## Strategic Additions: Path to Best-in-Class

### Tier 1: High Impact (Implement First)

#### 1. URL Parsing Suite

**Gap**: Liquid/Hugo have comprehensive URL manipulation; Kida has encode/decode but not parsing.

```kida
{# Parse URL into components #}
{% let parts = url | url_parse %}
{{ parts.scheme }}    {# "https" #}
{{ parts.host }}      {# "example.com" #}
{{ parts.path }}      {# "/docs/api" #}
{{ parts.query }}     {# "version=2" #}

{# Extract specific query parameter #}
{{ url | url_param('version') }}  {# "2" #}

{# Build query string from dict #}
{{ {'q': 'test', 'page': 1} | url_query }}  {# "q=test&page=1" #}
```

**Implementation**:
```python
# bengal/rendering/template_functions/urls.py
from urllib.parse import urlparse, parse_qs, urlencode

def url_parse(url: str) -> dict:
    """Parse URL into components."""
    parsed = urlparse(url)
    return {
        'scheme': parsed.scheme,
        'host': parsed.netloc,
        'path': parsed.path,
        'query': parsed.query,
        'fragment': parsed.fragment,
        'params': dict(parse_qs(parsed.query)),
    }

def url_param(url: str, param: str, default: str = '') -> str:
    """Extract query parameter from URL."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    values = params.get(param, [default])
    return values[0] if values else default

def url_query(data: dict) -> str:
    """Build query string from dict."""
    return urlencode(data, doseq=True)
```

**Effort**: 2 hours | **Impact**: High — closes biggest gap vs Hugo/Liquid

#### 2. Regex Extraction

**Gap**: Kida has `replace_regex` but not extraction. Jinja2 has both.

```kida
{# Extract first match #}
{{ "Price: $99.99" | regex_search(r'\$[\d.]+') }}  {# "$99.99" #}

{# Extract with groups #}
{{ "Price: $99.99" | regex_search(r'\$(\d+)\.(\d+)', group=1) }}  {# "99" #}

{# Find all matches #}
{{ "a1 b2 c3" | regex_findall(r'\d+') }}  {# ["1", "2", "3"] #}
```

**Implementation**:
```python
# bengal/rendering/template_functions/advanced_strings.py
import re

def regex_search(text: str, pattern: str, group: int = 0) -> str | None:
    """Extract first regex match."""
    match = re.search(pattern, text)
    if not match:
        return None
    try:
        return match.group(group)
    except IndexError:
        return match.group(0)

def regex_findall(text: str, pattern: str) -> list[str]:
    """Find all regex matches."""
    return re.findall(pattern, text)
```

**Effort**: 1 hour | **Impact**: High — enables text extraction use cases

#### 3. Auto-Linking (`urlize`)

**Gap**: Convert plain URLs to clickable links. Jinja2 and Hugo have this.

```kida
{{ "Check out https://example.com for more info" | urlize }}
{# Output: Check out <a href="https://example.com">https://example.com</a> for more info #}

{# With custom attributes #}
{{ text | urlize(target='_blank', rel='noopener') }}
```

**Effort**: 2 hours | **Impact**: High — common content processing need

### Tier 2: Medium Impact (Implement Second)

#### 4. Date Arithmetic

**Gap**: Twig has `date_modify`; Hugo has `time.Add`. Useful for expiration dates, schedules.

```kida
{# Add/subtract time #}
{{ page.date | date_add(days=7) }}
{{ page.date | date_add(weeks=2, hours=12) }}

{# Calculate difference #}
{{ end_date | date_diff(start_date) }}  {# Returns timedelta-like dict #}
{{ end_date | date_diff(start_date, unit='days') }}  {# Returns int #}
```

**Effort**: 2 hours | **Impact**: Medium — less common but powerful

#### 5. String Prefix/Suffix Operations

**Gap**: Hugo has `TrimPrefix`/`TrimSuffix`/`HasPrefix`/`HasSuffix`. Very ergonomic.

```kida
{{ "hello_world" | trim_prefix("hello_") }}  {# "world" #}
{{ "file.txt" | trim_suffix(".txt") }}  {# "file" #}

{% if url | has_prefix("https://") %}
  <span class="secure">🔒</span>
{% endif %}

{{ text | contains("error") }}  {# true/false #}
```

**Effort**: 1 hour | **Impact**: Medium — common string manipulation

#### 6. `to_sentence` (Array to Natural Language)

**Gap**: Liquid has `array_to_sentence_string`. Nice for human-readable lists.

```kida
{{ ['Alice', 'Bob', 'Charlie'] | to_sentence }}
{# "Alice, Bob, and Charlie" #}

{{ ['Alice', 'Bob'] | to_sentence }}
{# "Alice and Bob" #}

{{ ['Alice'] | to_sentence }}
{# "Alice" #}

{# Custom connectors #}
{{ items | to_sentence(connector='or', oxford=false) }}
{# "Alice, Bob or Charlie" #}
```

**Effort**: 1 hour | **Impact**: Medium — nice ergonomic touch

### Tier 3: Nice to Have (Lower Priority)

#### 7. `reduce` Filter

**Gap**: Twig has `reduce`. Powerful but rarely needed in templates.

```kida
{{ [1, 2, 3, 4] | reduce((acc, x) => acc + x, 0) }}  {# 10 #}
```

**Note**: This requires lambda support in Kida syntax. Consider if worth complexity.

#### 8. Base64 Encoding

**Gap**: Hugo has `base64Encode`/`base64Decode`. Useful for data URLs.

```kida
{{ "hello" | base64_encode }}  {# "aGVsbG8=" #}
{{ "aGVsbG8=" | base64_decode }}  {# "hello" #}
```

**Effort**: 30 minutes | **Impact**: Low — specialized use case

#### 9. `plainify` Alias

**Already have**: `strip_html` does this. Add alias for Hugo compatibility.

```kida
{{ html_content | plainify }}  {# Alias for strip_html #}
```

**Effort**: 5 minutes | **Impact**: Low — just an alias

---

## Implementation Plan

### Phase 1: URL + Regex (Week 1)
- [ ] `url_parse`, `url_param`, `url_query` in `urls.py`
- [ ] `urlize` in `content.py`
- [ ] `regex_search`, `regex_findall` in `advanced_strings.py`
- [ ] Tests for all new filters
- [ ] Documentation updates

### Phase 2: Strings + Dates (Week 2)
- [ ] `trim_prefix`, `trim_suffix`, `has_prefix`, `has_suffix`, `contains` in `advanced_strings.py`
- [ ] `to_sentence` in `advanced_strings.py`
- [ ] `date_add`, `date_diff` in `dates.py`
- [ ] Tests and docs

### Phase 3: Polish (Week 3)
- [ ] `plainify` alias for `strip_html`
- [ ] `base64_encode`, `base64_decode`
- [ ] Performance benchmarks vs Hugo/Jinja2
- [ ] Marketing: "80+ filters" documentation page

---

## Quality Requirements

All new filters must:

1. **Handle `None` gracefully** — Return sensible defaults, not errors
2. **Support strict mode** — Optional `strict=True` for fail-fast
3. **Work with pipeline `|>`** — Type annotations for IDE support
4. **Have clear errors** — Use `TemplateRuntimeError` with suggestions
5. **Be tested** — Unit tests + integration tests in templates
6. **Be documented** — Docstrings + site documentation

**Example pattern**:
```python
def url_param(url: str | None, param: str, default: str = '') -> str:
    """Extract query parameter from URL.
    
    Args:
        url: URL string to parse
        param: Parameter name to extract
        default: Default value if parameter not found
        
    Returns:
        Parameter value or default
        
    Example:
        {{ "https://x.com?page=2" | url_param('page') }}  # "2"
    """
    if url is None:
        return default
    # ... implementation
```

---

## Success Metrics

After implementation, Kida will have:

| Metric | Current | Target | Competitor Best |
|--------|---------|--------|-----------------|
| Total filters | 80+ | 93+ | Hugo ~100 |
| URL filters | 5 | 9 | Liquid 8 |
| Regex filters | 1 | 3 | Jinja2 3 |
| String filters | 18 | 23 | Hugo 20 |
| Unique features | 8 | 8 | - |

**Positioning**: "The only templating engine with 90+ filters, pipeline operators, and strict mode."

---

## Rejected Additions

| Filter | Reason |
|--------|--------|
| `math.Sqrt`, `math.Log`, `math.Sin` | Too specialized; use Python in code |
| `locale` formatting | Complex i18n; defer to site-level config |
| `link_to`, `link_to_tag` | Use macros instead; more flexible |
| `asset_url` with transforms | Bengal has `resources.get` pattern |

---

## Conclusion

Kida is **already the most feature-rich** open-source templating engine for static sites. The proposed 13 additions would:

1. **Close all significant gaps** vs Hugo/Liquid/Twig/Jinja2
2. **Add ergonomic touches** that improve developer experience
3. **Maintain Kida's performance edge** with efficient implementations

**Estimated effort**: ~2 weeks for full implementation with tests and docs.

**Recommendation**: Proceed with Tier 1 (URL + Regex + urlize) immediately — highest value-to-effort ratio.
