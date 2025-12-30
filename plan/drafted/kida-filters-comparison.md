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

### Phase 1: URL Parsing Suite (Days 1-2)

**Goal**: Close the biggest gap vs Hugo/Liquid with URL manipulation.

#### 1.1 Add URL Parsing Filters (`bengal/rendering/template_functions/urls.py`)

| Filter | Signature | Description |
|--------|-----------|-------------|
| `url_parse` | `url_parse(url: str) -> dict` | Parse URL into components (scheme, host, path, query, fragment, params) |
| `url_param` | `url_param(url: str, param: str, default: str = '') -> str` | Extract single query parameter |
| `url_query` | `url_query(data: dict) -> str` | Build query string from dict |

**Tasks**:
- [ ] **1.1.1** Add `url_parse()` function using `urllib.parse.urlparse`
- [ ] **1.1.2** Add `url_param()` function using `urllib.parse.parse_qs`
- [ ] **1.1.3** Add `url_query()` function using `urllib.parse.urlencode`
- [ ] **1.1.4** Register filters in `register()` function
- [ ] **1.1.5** Add docstrings with Kida syntax examples

**File**: `bengal/rendering/template_functions/urls.py` (lines 34-49)

```python
# Add to register():
env.filters.update({
    "url_parse": url_parse,
    "url_param": url_param,
    "url_query": url_query,
    # ... existing filters
})
```

#### 1.2 Add Auto-Linking Filter (`bengal/rendering/template_functions/content.py`)

| Filter | Signature | Description |
|--------|-----------|-------------|
| `urlize` | `urlize(text: str, target: str = '', rel: str = '', shorten: bool = False) -> str` | Convert plain URLs to clickable links |

**Tasks**:
- [ ] **1.2.1** Add `urlize()` function with regex URL detection
- [ ] **1.2.2** Support `target` attribute (e.g., `_blank`)
- [ ] **1.2.3** Support `rel` attribute (e.g., `noopener noreferrer`)
- [ ] **1.2.4** Optional URL shortening for display
- [ ] **1.2.5** Register filter in `register()` function

**File**: `bengal/rendering/template_functions/content.py` (lines 19-33)

#### 1.3 Write Tests (`tests/unit/template_functions/test_urls.py`)

**Tasks**:
- [ ] **1.3.1** Test `url_parse` with various URL formats (absolute, relative, with/without query)
- [ ] **1.3.2** Test `url_param` with single params, missing params, defaults
- [ ] **1.3.3** Test `url_query` with dicts, special characters, empty values
- [ ] **1.3.4** Test `urlize` with plain text, mixed content, edge cases

**Test file**: `tests/unit/template_functions/test_urls.py`

```python
class TestUrlParse:
    def test_full_url(self):
        result = url_parse("https://example.com/path?q=test#section")
        assert result["scheme"] == "https"
        assert result["host"] == "example.com"
        assert result["path"] == "/path"
        assert result["query"] == "q=test"
        assert result["fragment"] == "section"
        assert result["params"]["q"] == ["test"]

    def test_relative_url(self): ...
    def test_none_handling(self): ...
```

---

### Phase 2: Regex Extraction (Days 3-4)

**Goal**: Enable text extraction use cases currently impossible in Kida.

#### 2.1 Add Regex Filters (`bengal/rendering/template_functions/advanced_strings.py`)

| Filter | Signature | Description |
|--------|-----------|-------------|
| `regex_search` | `regex_search(text: str, pattern: str, group: int = 0) -> str \| None` | Extract first regex match |
| `regex_findall` | `regex_findall(text: str, pattern: str) -> list[str]` | Find all regex matches |

**Tasks**:
- [ ] **2.1.1** Add `regex_search()` with group support
- [ ] **2.1.2** Add `regex_findall()` returning list of matches
- [ ] **2.1.3** Add proper error handling for invalid regex patterns (log + return input)
- [ ] **2.1.4** Register filters in `register()` function
- [ ] **2.1.5** Add docstrings with Kida syntax examples

**File**: `bengal/rendering/template_functions/advanced_strings.py` (lines 18-34)

```python
# Add to register():
env.filters.update({
    "regex_search": regex_search,
    "regex_findall": regex_findall,
    # ... existing filters
})
```

**Implementation pattern** (follow existing `replace_regex` in `strings.py`):
```python
def regex_search(text: str | None, pattern: str, group: int = 0) -> str | None:
    """Extract first regex match from text.

    Args:
        text: Text to search in
        pattern: Regular expression pattern
        group: Capture group to return (0 for full match)

    Returns:
        Matched text or None if no match

    Example:
        {{ "Price: $99.99" | regex_search(r'\\$[\\d.]+') }}  # "$99.99"
        {{ "v2.3.1" | regex_search(r'v(\\d+)', group=1) }}  # "2"
    """
    if text is None:
        return None
    try:
        match = re.search(pattern, text)
        if not match:
            return None
        return match.group(group)
    except (re.error, IndexError) as e:
        logger.warning("regex_search_failed", pattern=pattern, error=str(e))
        return None
```

#### 2.2 Write Tests (`tests/unit/template_functions/test_advanced_strings.py`)

**Tasks**:
- [ ] **2.2.1** Test `regex_search` with simple patterns, groups, no match cases
- [ ] **2.2.2** Test `regex_findall` with multiple matches, no matches
- [ ] **2.2.3** Test error handling for invalid regex patterns
- [ ] **2.2.4** Test `None` input handling

---

### Phase 3: String Prefix/Suffix Operations (Days 5-6)

**Goal**: Match Hugo's ergonomic string manipulation.

#### 3.1 Add String Filters (`bengal/rendering/template_functions/advanced_strings.py`)

| Filter | Signature | Description |
|--------|-----------|-------------|
| `trim_prefix` | `trim_prefix(text: str, prefix: str) -> str` | Remove prefix if present |
| `trim_suffix` | `trim_suffix(text: str, suffix: str) -> str` | Remove suffix if present |
| `has_prefix` | `has_prefix(text: str, prefix: str) -> bool` | Check if starts with prefix |
| `has_suffix` | `has_suffix(text: str, suffix: str) -> bool` | Check if ends with suffix |
| `contains` | `contains(text: str, substring: str) -> bool` | Check if contains substring |

**Tasks**:
- [ ] **3.1.1** Add `trim_prefix()` function
- [ ] **3.1.2** Add `trim_suffix()` function
- [ ] **3.1.3** Add `has_prefix()` function (for use in conditionals)
- [ ] **3.1.4** Add `has_suffix()` function
- [ ] **3.1.5** Add `contains()` function
- [ ] **3.1.6** Register all filters

**File**: `bengal/rendering/template_functions/advanced_strings.py`

```python
def trim_prefix(text: str | None, prefix: str) -> str:
    """Remove prefix from string if present.

    Args:
        text: Text to trim
        prefix: Prefix to remove

    Returns:
        Text with prefix removed (or unchanged if no prefix)

    Example:
        {{ "hello_world" | trim_prefix("hello_") }}  # "world"
        {{ "test" | trim_prefix("hello_") }}  # "test" (unchanged)
    """
    if not text:
        return ""
    if text.startswith(prefix):
        return text[len(prefix):]
    return text
```

#### 3.2 Add `to_sentence` Filter (`bengal/rendering/template_functions/advanced_strings.py`)

| Filter | Signature | Description |
|--------|-----------|-------------|
| `to_sentence` | `to_sentence(items: list, connector: str = 'and', oxford: bool = True) -> str` | Convert array to natural language sentence |

**Tasks**:
- [ ] **3.2.1** Add `to_sentence()` function
- [ ] **3.2.2** Support custom connector ('and', 'or')
- [ ] **3.2.3** Support Oxford comma toggle
- [ ] **3.2.4** Handle edge cases (0, 1, 2 items)

```python
def to_sentence(items: list | None, connector: str = "and", oxford: bool = True) -> str:
    """Convert list to natural language sentence.

    Args:
        items: List of items to join
        connector: Word to use before last item (default: "and")
        oxford: Whether to use Oxford comma (default: True)

    Returns:
        Natural language string

    Example:
        {{ ['Alice', 'Bob', 'Charlie'] | to_sentence }}  # "Alice, Bob, and Charlie"
        {{ ['Alice', 'Bob'] | to_sentence }}  # "Alice and Bob"
        {{ tags | to_sentence(connector='or', oxford=false) }}  # "A, B or C"
    """
    if not items:
        return ""
    items = [str(item) for item in items]
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {connector} {items[1]}"
    if oxford:
        return f"{', '.join(items[:-1])}, {connector} {items[-1]}"
    return f"{', '.join(items[:-1])} {connector} {items[-1]}"
```

#### 3.3 Write Tests

**Tasks**:
- [ ] **3.3.1** Test all prefix/suffix operations with various inputs
- [ ] **3.3.2** Test `to_sentence` with 0, 1, 2, 3+ items
- [ ] **3.3.3** Test custom connectors and Oxford comma toggle

---

### Phase 4: Date Arithmetic (Days 7-8)

**Goal**: Enable date calculations for expiration dates, schedules.

#### 4.1 Add Date Filters (`bengal/rendering/template_functions/dates.py`)

| Filter | Signature | Description |
|--------|-----------|-------------|
| `date_add` | `date_add(date, days=0, weeks=0, hours=0, minutes=0) -> datetime` | Add/subtract time from date |
| `date_diff` | `date_diff(date1, date2, unit='days') -> int \| dict` | Calculate difference between dates |

**Tasks**:
- [ ] **4.1.1** Add `date_add()` using `timedelta`
- [ ] **4.1.2** Support negative values for subtraction
- [ ] **4.1.3** Add `date_diff()` returning difference
- [ ] **4.1.4** Support unit parameter ('days', 'hours', 'minutes', 'seconds')
- [ ] **4.1.5** Integrate with existing `bengal.utils.dates.parse_date`

**File**: `bengal/rendering/template_functions/dates.py` (lines 19-31)

```python
from datetime import timedelta

def date_add(
    date: datetime | str | None,
    days: int = 0,
    weeks: int = 0,
    hours: int = 0,
    minutes: int = 0,
) -> datetime | None:
    """Add time to a date.

    Args:
        date: Base date (datetime or ISO string)
        days: Days to add (negative to subtract)
        weeks: Weeks to add
        hours: Hours to add
        minutes: Minutes to add

    Returns:
        New datetime, or None if date is invalid

    Example:
        {{ page.date | date_add(days=7) }}  # One week later
        {{ now | date_add(days=-30) }}  # 30 days ago
        {{ event.start | date_add(hours=2) }}  # 2 hours later
    """
    from bengal.utils.dates import parse_date

    dt = parse_date(date)
    if not dt:
        return None

    delta = timedelta(days=days, weeks=weeks, hours=hours, minutes=minutes)
    return dt + delta
```

#### 4.2 Write Tests (`tests/unit/template_functions/test_dates.py`)

**Tasks**:
- [ ] **4.2.1** Test `date_add` with positive/negative values
- [ ] **4.2.2** Test `date_add` with ISO strings and datetime objects
- [ ] **4.2.3** Test `date_diff` with various units
- [ ] **4.2.4** Test timezone handling

---

### Phase 5: Aliases & Base64 (Days 9-10)

**Goal**: Compatibility aliases and specialized utilities.

#### 5.1 Add Aliases

| Alias | Target | Location |
|-------|--------|----------|
| `plainify` | `strip_html` | `strings.py` |

**Tasks**:
- [ ] **5.1.1** Add `plainify` alias in `strings.py` register function

```python
# In register():
env.filters["plainify"] = strip_html  # Hugo compatibility
```

#### 5.2 Add Base64 Filters (`bengal/rendering/template_functions/strings.py`)

| Filter | Signature | Description |
|--------|-----------|-------------|
| `base64_encode` | `base64_encode(text: str) -> str` | Encode to Base64 |
| `base64_decode` | `base64_decode(text: str) -> str` | Decode from Base64 |

**Tasks**:
- [ ] **5.2.1** Add `base64_encode()` function
- [ ] **5.2.2** Add `base64_decode()` function with error handling
- [ ] **5.2.3** Register filters

```python
import base64

def base64_encode(text: str | None) -> str:
    """Encode text as Base64.

    Args:
        text: Text to encode

    Returns:
        Base64 encoded string

    Example:
        {{ "hello" | base64_encode }}  # "aGVsbG8="
        {{ small_image | base64_encode }}  # For data URLs
    """
    if not text:
        return ""
    return base64.b64encode(text.encode()).decode()

def base64_decode(text: str | None) -> str:
    """Decode Base64 text.

    Args:
        text: Base64 encoded string

    Returns:
        Decoded text, or empty string on error

    Example:
        {{ "aGVsbG8=" | base64_decode }}  # "hello"
    """
    if not text:
        return ""
    try:
        return base64.b64decode(text).decode()
    except Exception:
        return ""
```

---

### Phase 6: Documentation & Integration (Days 11-12)

**Goal**: Complete documentation and integration testing.

#### 6.1 Update Site Documentation

**File**: `site/content/docs/reference/kida-syntax.md`

**Tasks**:
- [ ] **6.1.1** Add URL filters section with examples
- [ ] **6.1.2** Add Regex filters section with examples
- [ ] **6.1.3** Add String manipulation section (prefix/suffix)
- [ ] **6.1.4** Add Date arithmetic section
- [ ] **6.1.5** Update filter count (80+ → 93+)
- [ ] **6.1.6** Add migration note for Hugo users

#### 6.2 Integration Tests

**File**: `tests/integration/test_kida_filters.py`

**Tasks**:
- [ ] **6.2.1** Create template integration tests for each new filter
- [ ] **6.2.2** Test filter chaining (pipeline operator compatibility)
- [ ] **6.2.3** Test error recovery in templates

```python
def test_url_filters_in_template(site):
    """Test URL filters work correctly in actual templates."""
    template = """
    {% let url = "https://example.com/path?page=2&sort=date" %}
    {{ url | url_parse | get('host') }}
    {{ url | url_param('page') }}
    """
    result = site.render_string(template)
    assert "example.com" in result
    assert "2" in result
```

#### 6.3 Performance Benchmarks

**File**: `benchmarks/filters/`

**Tasks**:
- [ ] **6.3.1** Benchmark `url_parse` vs manual parsing
- [ ] **6.3.2** Benchmark `regex_search` vs `replace_regex`
- [ ] **6.3.3** Compare with equivalent Jinja2/Hugo operations

---

### Implementation Checklist Summary

| Phase | Filters | Effort | Files Modified |
|-------|---------|--------|----------------|
| **Phase 1** | `url_parse`, `url_param`, `url_query`, `urlize` | 2 days | `urls.py`, `content.py`, `test_urls.py` |
| **Phase 2** | `regex_search`, `regex_findall` | 2 days | `advanced_strings.py`, `test_advanced_strings.py` |
| **Phase 3** | `trim_prefix`, `trim_suffix`, `has_prefix`, `has_suffix`, `contains`, `to_sentence` | 2 days | `advanced_strings.py`, `test_advanced_strings.py` |
| **Phase 4** | `date_add`, `date_diff` | 2 days | `dates.py`, `test_dates.py` |
| **Phase 5** | `plainify` (alias), `base64_encode`, `base64_decode` | 2 days | `strings.py`, `test_strings.py` |
| **Phase 6** | Documentation & integration | 2 days | `kida-syntax.md`, `test_kida_filters.py` |

**Total**: ~12 working days (2.5 weeks)

---

### Dependencies & Blockers

| Dependency | Status | Notes |
|------------|--------|-------|
| `urllib.parse` | ✅ stdlib | No external deps for URL parsing |
| `re` | ✅ stdlib | Already used in `strings.py` |
| `base64` | ✅ stdlib | No external deps |
| `timedelta` | ✅ stdlib | Already imported in `dates.py` |

**No new dependencies required** — all implementations use Python stdlib.

---

### Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Regex performance in templates | Use compiled patterns; add timeout for complex patterns |
| URL parsing edge cases | Extensive test coverage; follow `urllib.parse` behavior |
| Breaking existing templates | All filters are additive; no changes to existing API |
| Type annotation issues | Follow existing patterns in codebase; use `str \| None` consistently |

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
