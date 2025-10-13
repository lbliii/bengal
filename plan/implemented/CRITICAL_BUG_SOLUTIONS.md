# Critical Bug Solutions

**Date**: October 13, 2025  
**Priority**: Critical (blocking v0.1.2 release)  
**Estimated Fix Time**: 2-3 hours total

---

## Bug #1: Cache Stored in Output Directory (Data Loss Risk)

### Problem Analysis

**Location**: `bengal/orchestration/incremental.py:57`

```python
cache_path = self.site.output_dir / ".bengal-cache.json"
```

**Issue**: Cache is stored in `public/.bengal-cache.json` instead of project root. When users run `bengal clean`, the cache is deleted, causing:
1. **Data loss** - All incremental build metadata lost
2. **Performance regression** - Next "incremental" build is actually a full rebuild
3. **User confusion** - "Why is --incremental slow after cleaning?"

**Impact**:
- Every user who runs `bengal clean` loses cache
- Incremental builds become useless in CI/CD (always clean first)
- Violates principle of least surprise

### Solution

**Change**: Store cache in project root `.bengal/` directory

#### Implementation Plan

**File**: `bengal/orchestration/incremental.py`

```python
# BEFORE (Line 57)
cache_path = self.site.output_dir / ".bengal-cache.json"

# AFTER
cache_path = self.site.root_path / ".bengal" / "cache.json"
```

**Additional changes needed**:

1. **Create cache directory** (line 56-57):
```python
def initialize(self, enabled: bool = False) -> tuple["BuildCache", "DependencyTracker"]:
    """Initialize cache and tracker."""
    from bengal.cache import BuildCache, DependencyTracker

    # Store cache in project root .bengal directory (not output)
    cache_dir = self.site.root_path / ".bengal"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "cache.json"

    if enabled:
        self.cache = BuildCache.load(cache_path)
        # ... rest of code
```

2. **Update save_cache method** (line ~350):
```python
def save_cache(self, pages_to_build: list[Page], assets_to_process: list[Asset]) -> None:
    """Save cache after successful build."""
    if not self.cache:
        return

    # Use same path as initialize()
    cache_dir = self.site.root_path / ".bengal"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "cache.json"

    self.cache.save(cache_path)
    # ... rest of code
```

3. **Add .gitignore entry** - Update CLI templates to include:
```gitignore
# Bengal cache directory
.bengal/
```

#### Benefits

✅ **Survives clean** - Cache persists through `bengal clean`  
✅ **Conventional** - Matches `.git/`, `.pytest_cache/`, etc.  
✅ **Clear separation** - Output vs. metadata clearly separated  
✅ **CI-friendly** - Can cache `.bengal/` directory between builds  
✅ **Multiple caches** - Future: profiles, different configs, etc.

#### Migration Path

**For existing users**: First build after update will:
1. Look for cache in old location (`public/.bengal-cache.json`)
2. If found, copy to new location (`.bengal/cache.json`)
3. Show migration message
4. Continue using new location

```python
def initialize(self, enabled: bool = False) -> tuple["BuildCache", "DependencyTracker"]:
    """Initialize cache with automatic migration."""
    from bengal.cache import BuildCache, DependencyTracker
    import shutil

    # New cache location
    cache_dir = self.site.root_path / ".bengal"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "cache.json"

    # Legacy cache location
    old_cache_path = self.site.output_dir / ".bengal-cache.json"

    # Migrate old cache if exists and new doesn't
    if old_cache_path.exists() and not cache_path.exists():
        try:
            shutil.copy2(old_cache_path, cache_path)
            logger.info(
                "cache_migrated",
                from_location=str(old_cache_path),
                to_location=str(cache_path),
                action="automatic_migration"
            )
            # Optionally delete old cache
            # old_cache_path.unlink()
        except Exception as e:
            logger.warning(
                "cache_migration_failed",
                error=str(e),
                action="using_fresh_cache"
            )

    if enabled:
        self.cache = BuildCache.load(cache_path)
        # ... rest of code
```

#### Testing Required

1. **Unit test**: Cache path uses root_path not output_dir
2. **Integration test**:
   - Full build → check `.bengal/cache.json` exists
   - `bengal clean` → verify cache still exists
   - Incremental build → verify cache used
3. **Migration test**: Old cache → new cache conversion
4. **Edge cases**:
   - Read-only filesystem (cache in temp?)
   - Network drive (permission issues?)
   - Concurrent builds (file locking?)

#### Risks & Mitigation

**Risk 1**: Breaking change for existing users  
**Mitigation**: Automatic migration on first build after update

**Risk 2**: `.bengal/` directory surprises users  
**Mitigation**: Document in CHANGELOG, add to .gitignore templates

**Risk 3**: Concurrent builds conflict  
**Mitigation**: Atomic writes already implemented (AtomicFile), add PID to cache filename if needed

---

## Bug #2: Meta Description Contains Raw Markdown (SEO Disaster)

### Problem Analysis

**Location**: `bengal/core/page/computed.py:20-72` (meta_description property)

```python
@cached_property
def meta_description(self) -> str:
    """Generate SEO-friendly meta description."""
    # Check metadata first
    if self.metadata.get("description"):
        return self.metadata["description"]

    # Generate from content
    text = self.content  # ← BUG: self.content is RENDERED HTML
    if not text:
        return ""

    # Strip HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # ... truncate and return
```

**Issues**:
1. `self.content` contains **rendered HTML** with directive syntax still visible in source
2. Directives like `:::{button}` appear in meta tags
3. HTML tag stripping happens AFTER content is already polluted
4. No markdown-to-plaintext conversion

**Example**:
```markdown
---
title: Get Started
---
:::{button} /docs/
Click here
:::
```

**Current meta tag**:
```html
<meta name="description" content=":::{button} /docs/ Click here :::">
```

**What users see in Google**:
```
Get Started
:::{button} /docs/ Click here ::: ...
```

### Root Cause

The problem is **when** meta_description is computed:

1. **Discovery phase**: `page.content` = raw markdown
2. **Parsing phase**: `page.content` = rendered HTML (but directives already converted)
3. **Template phase**: Meta description accessed

At template time, `page.content` is already HTML, but the regex only strips tags, not directive syntax.

### Solution Option A: Use Raw Content (Recommended)

**Strategy**: Generate meta description from raw markdown before rendering.

```python
@cached_property
def meta_description(self) -> str:
    """
    Generate SEO-friendly meta description (computed once, cached).

    Creates description by:
    - Using explicit 'description' from metadata if available
    - Otherwise generating from RAW markdown by stripping syntax and truncating
    - Attempting to end at sentence boundary for better readability

    Returns:
        Meta description text (max 160 chars)
    """
    # Check metadata first (explicit description)
    if self.metadata.get("description"):
        return self.metadata["description"]

    # Generate from RAW CONTENT (before rendering)
    # Use raw_content if available (set during discovery), fallback to content
    text = getattr(self, 'raw_content', self.content)
    if not text:
        return ""

    # Convert markdown to plain text
    text = self._markdown_to_plaintext(text)

    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    length = 160
    if len(text) <= length:
        return text

    # Truncate to length
    truncated = text[:length]

    # Try to end at sentence boundary
    sentence_end = max(truncated.rfind(". "), truncated.rfind("! "), truncated.rfind("? "))

    if sentence_end > length * 0.6:
        return truncated[: sentence_end + 1].strip()

    # Try to end at word boundary
    last_space = truncated.rfind(" ")
    if last_space > 0:
        return truncated[:last_space].strip() + "…"

    return truncated + "…"

def _markdown_to_plaintext(self, markdown: str) -> str:
    """
    Convert markdown to plain text, removing all syntax.

    Handles:
    - Directive syntax (:::{directive} ... :::)
    - Markdown formatting (**bold**, *italic*, [links](url))
    - Code blocks (```...```)
    - Inline code (`code`)
    - Headers (#, ##, etc.)
    - Lists (-, *, 1.)
    - HTML tags (<tag>)

    Args:
        markdown: Raw markdown content

    Returns:
        Plain text with all syntax removed
    """
    text = markdown

    # Remove directive blocks (:::{directive} ... :::)
    # Match both backtick and colon fences
    text = re.sub(r':::?\{[^}]+\}[^\n]*\n', '', text)  # Opening
    text = re.sub(r':::?\n', '', text)  # Closing
    text = re.sub(r'```\{[^}]+\}[^\n]*\n', '', text)  # Backtick opening

    # Remove code blocks (``` ... ```)
    text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)

    # Remove inline code (`code`)
    text = re.sub(r'`([^`]+)`', r'\1', text)

    # Remove links but keep text ([text](url) → text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

    # Remove images (![alt](url) → alt)
    text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)

    # Remove bold (**text** or __text__ → text)
    text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)

    # Remove italic (*text* or _text_ → text)
    text = re.sub(r'\*([^\*]+)\*', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)

    # Remove headers (# Header → Header)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Remove list markers (-, *, 1., etc.)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)

    # Remove HTML tags (in case any exist)
    text = re.sub(r'<[^>]+>', '', text)

    # Remove horizontal rules (---, ***, etc.)
    text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)

    # Remove blockquotes (> text → text)
    text = re.sub(r'^\s*>\s+', '', text, flags=re.MULTILINE)

    return text
```

#### Implementation Details

**File**: `bengal/core/page/computed.py`

**Changes needed**:
1. Add `_markdown_to_plaintext()` helper method
2. Update `meta_description` to use raw content
3. Store raw markdown during discovery phase

**File**: `bengal/discovery/content_discovery.py` (or wherever Page is created)

```python
# When creating Page object, preserve raw content
page = Page(
    source_path=source_path,
    content=content,  # This gets rendered later
    raw_content=content,  # NEW: Preserve for meta description
    metadata=metadata,
    # ...
)
```

**File**: `bengal/core/page/__init__.py`

```python
@dataclass
class Page(...):
    """Page object."""
    source_path: Path
    content: str = ""
    raw_content: str = ""  # NEW: Original markdown before rendering
    metadata: dict[str, Any] = field(default_factory=dict)
    # ...
```

### Solution Option B: Strip Directives from HTML (Fallback)

If Option A is too invasive, we can improve the current approach:

```python
@cached_property
def meta_description(self) -> str:
    """Generate SEO-friendly meta description."""
    # Check metadata first
    if self.metadata.get("description"):
        return self.metadata["description"]

    # Generate from content (HTML at this point)
    text = self.content
    if not text:
        return ""

    # NEW: Remove directive syntax before HTML stripping
    # This handles cases where directives weren't fully rendered
    text = re.sub(r':::?\{[^}]+\}[^\n]*', '', text)
    text = re.sub(r':::?', '', text)
    text = re.sub(r'```\{[^}]+\}[^\n]*', '', text)

    # Strip HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # ... rest of truncation logic
```

**Pros**: Minimal changes, quick fix  
**Cons**: Hacky, doesn't handle all edge cases

### Recommendation: Option A (Raw Content)

**Reasoning**:
1. **Correct by design** - Uses source markdown, not rendered HTML
2. **Comprehensive** - Handles all markdown syntax, not just directives
3. **Future-proof** - Works for any new directives or markdown features
4. **Better SEO** - Plain text descriptions read naturally
5. **Performance** - Cached property, no performance penalty

#### Testing Required

1. **Unit tests**:
   ```python
   def test_meta_description_strips_directives():
       page = Page(
           source_path=Path("test.md"),
           raw_content=":::{button} /docs/\nClick\n:::\n\nThis is content.",
           metadata={}
       )
       assert page.meta_description == "Click This is content."

   def test_meta_description_strips_markdown_formatting():
       page = Page(
           source_path=Path("test.md"),
           raw_content="**Bold** and *italic* and `code` text.",
           metadata={}
       )
       assert page.meta_description == "Bold and italic and code text."

   def test_meta_description_respects_explicit():
       page = Page(
           source_path=Path("test.md"),
           raw_content=":::{note}\nIgnored\n:::",
           metadata={"description": "Custom description"}
       )
       assert page.meta_description == "Custom description"
   ```

2. **Integration test**:
   ```python
   def test_meta_tags_no_directive_syntax():
       """Ensure built pages have clean meta descriptions."""
       site = Site.from_config(test_site_path)
       site.build()

       html = (site.output_dir / "test-page/index.html").read_text()

       # Should NOT contain directive syntax
       assert ":::{" not in html
       assert ":::" not in html or '<div class="admonition">' in html  # OK in content

       # Check meta tag specifically
       meta_desc = re.search(r'<meta name="description" content="([^"]+)"', html)
       assert meta_desc
       assert ":::{" not in meta_desc.group(1)
   ```

3. **Manual verification**:
   - Build example site with directives
   - View source of generated HTML
   - Check all `<meta>` tags for clean text
   - Test in Google's Rich Results validator

#### Edge Cases to Handle

1. **No raw content available** (legacy compatibility):
   ```python
   text = getattr(self, 'raw_content', None) or self.content
   ```

2. **Nested directives**:
   ```markdown
   ::::{tabs}
   :::{tab} Python
   Code here
   :::
   ::::
   ```
   Should extract: "Python Code here"

3. **Directives with no text content**:
   ```markdown
   :::{button} /docs/
   :::
   ```
   Should skip (empty after extraction)

4. **Mixed content**:
   ```markdown
   Regular text **bold** :::{note}
   Note text
   :::
   More text.
   ```
   Should extract: "Regular text bold Note text More text."

---

## Bug #3 (Bonus): Page Name Slugification

**Quick win** - Can be fixed alongside #2 since we're touching page creation code.

**File**: `bengal/cli/commands/new.py`

```python
def slugify(text: str) -> str:
    """
    Convert text to URL-safe slug.

    Examples:
        "My Awesome Page" → "my-awesome-page"
        "Hello, World!" → "hello-world"
        "Test   Multiple   Spaces" → "test-multiple-spaces"
    """
    import re

    # Lowercase
    text = text.lower()

    # Remove special characters (keep alphanumeric, spaces, hyphens)
    text = re.sub(r'[^\w\s-]', '', text)

    # Replace spaces and multiple hyphens with single hyphen
    text = re.sub(r'[-\s]+', '-', text)

    # Strip leading/trailing hyphens
    return text.strip('-')

# In new page command:
@new.command()
@click.argument("name")
def page(name: str) -> None:
    """Create a new page."""
    # Slugify the name for filename
    slug = slugify(name)

    content_dir = Path("content")
    if not content_dir.exists():
        raise click.ClickException("content/ directory not found")

    # Use slugified name for file
    page_path = content_dir / f"{slug}.md"

    if page_path.exists():
        raise click.ClickException(f"Page already exists: {page_path}")

    # Use original name for title (capitalize properly)
    title = name.title()

    # Create page with proper YAML frontmatter
    page_path.write_text(f"""---
title: {title}
---

# {title}

Start writing your content here.
""")

    click.echo(click.style(f"\n✨ Created new page: {page_path}\n", fg="green"))
```

---

## Summary

### Fix Order (Recommended)

1. **Bug #1 (Cache location)** - 1 hour
   - Clear user impact, low risk
   - Includes migration code for smooth upgrade

2. **Bug #3 (Slugification)** - 15 minutes  
   - Quick win, obvious improvement
   - No breaking changes

3. **Bug #2 (Meta descriptions)** - 1.5 hours
   - Most complex, needs careful testing
   - Requires dataclass field addition

### Release Plan

**v0.1.2** (Hotfix):
- Bug #1: Cache location fix with migration
- Bug #3: Page name slugification
- Updated .gitignore templates

**v0.1.3** (Week 2):
- Bug #2: Meta description fix (needs more testing)
- Additional test coverage
- Documentation updates

### Documentation Updates Needed

1. **CHANGELOG.md**:
   ```markdown
   ## [0.1.2] - 2025-10-XX

   ### Fixed
   - **BREAKING**: Cache now stored in `.bengal/` directory (migrated automatically)
   - Page names are now slugified (spaces → hyphens)
   - Meta descriptions no longer contain raw markdown syntax

   ### Migration
   - Existing caches in `public/.bengal-cache.json` will be automatically
     migrated to `.bengal/cache.json` on first build
   - Add `.bengal/` to your .gitignore
   ```

2. **GETTING_STARTED.md**:
   - Document `.bengal/` directory purpose
   - Explain cache behavior
   - Add to .gitignore section

3. **ARCHITECTURE.md**:
   - Update cache section
   - Document meta description generation
   - Add slugification to page creation flow

---

## Testing Checklist

### Bug #1 (Cache Location)
- [ ] Unit test: Cache path uses root_path
- [ ] Integration test: Full build creates `.bengal/cache.json`
- [ ] Integration test: `bengal clean` preserves cache
- [ ] Integration test: Incremental build uses cache
- [ ] Migration test: Old cache migrated automatically
- [ ] Edge case: Read-only filesystem
- [ ] Edge case: Network drive permissions

### Bug #2 (Meta Descriptions)
- [ ] Unit test: Directive syntax stripped
- [ ] Unit test: Markdown formatting stripped
- [ ] Unit test: Explicit description respected
- [ ] Integration test: Built HTML has clean meta tags
- [ ] Integration test: Nested directives handled
- [ ] Manual test: Google Rich Results validator
- [ ] Edge case: No raw content available
- [ ] Edge case: Empty content

### Bug #3 (Slugification)
- [ ] Unit test: Spaces converted to hyphens
- [ ] Unit test: Special characters removed
- [ ] Unit test: Multiple spaces collapsed
- [ ] Integration test: `bengal new page "Test Page"` creates `test-page.md`
- [ ] Edge case: Unicode characters
- [ ] Edge case: Emoji in names

---

**Document Status**: ✅ Complete  
**Ready for**: Implementation  
**Priority**: Critical - blocking v0.1.2 release
