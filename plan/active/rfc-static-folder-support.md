# RFC: Static Folder Support

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2024-12-03  
**Subsystems**: `orchestration`, `discovery`, `config`

---

## Summary

Add support for a `static/` folder that copies files verbatim to the output directory without processing. This enables raw HTML pages, downloadable files, and other assets that need to bypass the content pipeline while still having access to theme assets.

---

## Motivation

### Problem

Currently, Bengal has no clean way to include raw HTML pages or files that should be copied without processing:

1. **Raw HTML demos** - Interactive demos (like the holographic card effects) need full HTML control but want to use Bengal's theme CSS
2. **Downloadable files** - PDFs, ZIPs, binaries that shouldn't be processed
3. **Third-party widgets** - Embed codes, iframes, or HTML snippets
4. **Style guides** - Live component examples with raw HTML
5. **Landing pages** - Custom HTML that doesn't fit the template system

### Current Workaround

Files placed in `site/assets/` get copied, but:
- Mixes static content with processed assets (CSS, JS)
- URLs are under `/assets/` which isn't ideal
- Conceptually confusing - assets vs static files

### Industry Standard

Every major SSG has this pattern:

| SSG | Static Folder | Behavior |
|-----|---------------|----------|
| Hugo | `static/` | Copied to output root |
| Astro | `public/` | Copied to output root |
| Next.js | `public/` | Copied to output root |
| Eleventy | Configurable | `addPassthroughCopy()` |
| Jekyll | Any file without front matter | Copied as-is |

---

## Proposal

### Directory Structure

```
site/
├── static/              # NEW: Copied verbatim to public/
│   ├── demos/
│   │   └── holo.html    # → public/demos/holo.html
│   ├── downloads/
│   │   └── guide.pdf    # → public/downloads/guide.pdf
│   └── robots.txt       # → public/robots.txt
├── assets/              # Processed (bundling, fingerprinting)
├── content/             # Markdown → HTML via templates
└── bengal.toml
```

### Behavior

1. **Copy timing** - Static files copied FIRST, before any other build phase
2. **No processing** - Files copied byte-for-byte, no transformation
3. **Overwrite behavior** - Static files can be overwritten by generated files (content takes precedence)
4. **Theme access** - Static HTML can link to `/assets/css/style.css` to use Bengal's theme

### Configuration

```toml
# bengal.toml (defaults shown)

[static]
enabled = true           # Enable static folder support
dir = "static"           # Source directory (relative to site root)
# Output is always site root (no prefix)
```

Minimal config - works out of the box with sensible defaults.

### URL Mapping

```
static/foo.html          → public/foo.html           → /foo.html
static/demos/widget.html → public/demos/widget.html  → /demos/widget.html
static/downloads/app.zip → public/downloads/app.zip  → /downloads/app.zip
```

---

## Implementation

### Phase 1: Core Copy Logic

**File**: `bengal/orchestration/static.py` (new)

```python
"""Static file orchestrator - copies static/ to output verbatim."""

import shutil
from pathlib import Path
from bengal.utils.logging import get_logger

logger = get_logger(__name__)


class StaticOrchestrator:
    """Copies static files to output directory without processing."""

    def __init__(self, site):
        self.site = site
        self.static_dir = site.root_path / site.config.get("static", {}).get("dir", "static")
        self.output_dir = site.output_dir

    def is_enabled(self) -> bool:
        """Check if static folder exists and is enabled."""
        enabled = self.site.config.get("static", {}).get("enabled", True)
        return enabled and self.static_dir.exists()

    def copy(self) -> int:
        """
        Copy static files to output directory.

        Returns:
            Number of files copied
        """
        if not self.is_enabled():
            return 0

        count = 0
        for source_path in self.static_dir.rglob("*"):
            if source_path.is_file():
                # Compute relative path and destination
                rel_path = source_path.relative_to(self.static_dir)
                dest_path = self.output_dir / rel_path

                # Create parent directories
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                # Copy file (preserving metadata)
                shutil.copy2(source_path, dest_path)
                count += 1

                logger.debug("static_file_copied", source=str(rel_path))

        if count > 0:
            logger.info("static_files_copied", count=count)

        return count
```

### Phase 2: Integration with Build Pipeline

**File**: `bengal/core/site.py` (modify `_build_with_pipeline`)

```python
def _build_with_pipeline(self, parallel: bool = True, verbose: bool = False) -> BuildStats:
    # ... existing code ...

    # Phase 0: Static files (copy FIRST, before everything)
    static_start = time.time()
    from bengal.orchestration.static import StaticOrchestrator
    static = StaticOrchestrator(self)
    static_count = static.copy()
    static_time_ms = (time.time() - static_start) * 1000

    # Phase 1: Font Processing (existing)
    # ...
```

### Phase 3: Dev Server Integration

**File**: `bengal/server/build_handler.py` (modify)

Update `BuildHandler` to:
1. Watch `static/` directory (ensure `_should_ignore_file` allows it)
2. Detect changes in `static/` in `_handle_file_event`
3. Trigger optimized handling for static files:
   - Run `StaticOrchestrator.copy()` (incremental if possible)
   - Trigger browser reload (skip full site build if only static files changed)

### Phase 4: Configuration

**File**: `bengal/config/defaults.py` (modify)

Add defaults to `DEFAULTS` dict:
```python
DEFAULTS = {
    # ...
    "static": {
        "enabled": True,
        "dir": "static",
    },
    # ...
}
```

**File**: `bengal/config/validators.py` (modify)

Update `ConfigValidator` to validate static config:
- Validate `static` key is a dict
- Validate `static.enabled` is boolean
- Validate `static.dir` is string

---

## Use Cases

### 1. Interactive Demo Page

```html
<!-- static/demos/holo-cards.html -->
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="/assets/css/style.css">
</head>
<body>
  <!-- Full HTML control with Bengal's theme -->
  <div class="holo-card">...</div>
  <script>/* custom JS */</script>
</body>
</html>
```

### 2. Downloadable Resources

```
static/
├── downloads/
│   ├── bengal-cheatsheet.pdf
│   └── starter-kit.zip
└── samples/
    └── example-site.tar.gz
```

### 3. Third-Party Integrations

```
static/
├── .well-known/          # ACME, security.txt
│   └── security.txt
├── ads.txt               # Ad verification
└── google1234567.html    # Domain verification
```

### 4. Custom Landing Pages

```html
<!-- static/welcome.html -->
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="/assets/css/style.css">
  <style>/* page-specific overrides */</style>
</head>
<body class="landing-page">
  <!-- Custom layout not using doc template -->
</body>
</html>
```

---

## Alternatives Considered

### 1. Passthrough Config (Eleventy-style)

```toml
[passthrough]
patterns = ["*.pdf", "*.zip", "demos/**/*.html"]
```

**Rejected**: More complex, requires glob patterns, less intuitive than a dedicated folder.

### 2. Front Matter Detection (Jekyll-style)

Files without `---` front matter are copied as-is.

**Rejected**:
- Surprising behavior
- Requires scanning all files
- Can't easily tell what will be processed vs copied

### 3. Use Assets Folder

Keep static files in `assets/`.

**Rejected**:
- URLs prefixed with `/assets/`
- Mixes processed and unprocessed files
- Conceptually confusing

### 4. HTML Content Type

Add a content type that passes HTML through without wrapping in templates.

**Rejected**:
- Doesn't solve non-HTML files (PDFs, ZIPs)
- More complex implementation
- Still goes through content pipeline

---

## Migration

### For Existing Sites

No breaking changes. The feature is additive:
- Sites without `static/` folder: No change
- Sites with `static/` folder: Automatically enabled

### Documentation Update

Add to Getting Started guide:
```markdown
## Static Files

Files in `static/` are copied to your site root without processing:

- `static/robots.txt` → `/robots.txt`
- `static/demos/widget.html` → `/demos/widget.html`
- `static/downloads/guide.pdf` → `/downloads/guide.pdf`

Static HTML files can use Bengal's theme:
```html
<link rel="stylesheet" href="/assets/css/style.css">
```
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_static_orchestrator.py

def test_static_copy_basic(tmp_site):
    """Static files are copied to output root."""
    (tmp_site / "static/foo.txt").write_text("hello")
    site = Site(tmp_site)
    site.build()
    assert (tmp_site / "public/foo.txt").read_text() == "hello"

def test_static_nested_directories(tmp_site):
    """Nested directories are preserved."""
    (tmp_site / "static/a/b/c.txt").mkdir(parents=True)
    ...

def test_static_disabled(tmp_site):
    """Static copy can be disabled via config."""
    ...

def test_static_missing_folder(tmp_site):
    """Missing static folder is handled gracefully."""
    ...

def test_content_overwrites_static(tmp_site):
    """Content-generated files take precedence over static."""
    ...
```

### Integration Tests

```python
# tests/integration/test_static_build.py

def test_static_html_with_theme(tmp_site):
    """Static HTML can reference theme assets."""
    html = '''
    <link rel="stylesheet" href="/assets/css/style.css">
    <div class="admonition">Works!</div>
    '''
    (tmp_site / "static/demo.html").write_text(html)
    site = Site(tmp_site)
    site.build()
    # Verify CSS exists at referenced path
    assert (tmp_site / "public/assets/css/style.css").exists()
```

---

## Rollout Plan

### Phase 1: Core Feature (This PR)
- [ ] `StaticOrchestrator` class
- [ ] Integration in build pipeline
- [ ] Config schema update
- [ ] Unit tests
- [ ] Documentation

### Phase 2: Dev Server (Follow-up)
- [ ] Watch `static/` for changes
- [ ] Incremental copy on change
- [ ] Browser reload trigger

### Phase 3: CLI Enhancement (Optional)
- [ ] `bengal static list` - Show what would be copied
- [ ] `bengal static copy` - Manual copy without full build

---

## Success Criteria

- [ ] `static/` folder contents appear at site root
- [ ] No processing/transformation of static files
- [ ] Static HTML can link to `/assets/css/style.css` and get Bengal theme
- [ ] Works with all palette variants
- [ ] Dev server watches and reloads on static file changes
- [ ] Clear documentation with examples

---

## Open Questions

1. **Conflict resolution** - If both `static/foo.html` and `content/foo.md` exist, which wins?
   - **Proposed**: Content wins (generated files overwrite static)
   - **Rationale**: Explicit content should take precedence over static fallbacks

2. **Ignored files** - Should we respect `.gitignore` in static folder?
   - **Proposed**: No, copy everything (simple and predictable)
   - **Rationale**: Users can exclude files by not putting them there

3. **Large files** - Any size limits or warnings?
   - **Proposed**: Warn if total static size > 50MB
   - **Rationale**: Helps catch accidental inclusion of large files

---

## References

- [Hugo Static Files](https://gohugo.io/content-management/static-files/)
- [Astro Public Directory](https://docs.astro.build/en/basics/project-structure/#public)
- [Eleventy Passthrough Copy](https://www.11ty.dev/docs/copy/)
- [Jekyll Static Files](https://jekyllrb.com/docs/static-files/)
