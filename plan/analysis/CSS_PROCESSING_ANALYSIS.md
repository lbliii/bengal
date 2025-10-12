# CSS Processing Analysis & Recommendations

**Date**: October 8, 2025  
**Issue**: CSS not bundled, causing 30+ HTTP requests  
**Priority**: 🔥 HIGH - Performance impact

---

## Current State: ❌ NOT GOOD

### What We Do Now
```python
# In Asset.minify()
def _minify_css(self):
    import csscompressor
    css_content = f.read()
    minified = csscompressor.compress(css_content)
    # Just removes whitespace and comments
```

### What We DON'T Do
- ❌ Bundle `@import` statements (inline them)
- ❌ Autoprefixing (vendor prefixes for older browsers)
- ❌ Modern CSS transforms (nesting, etc.)
- ❌ PostCSS plugins
- ❌ Dead code elimination (PurgeCSS)

### Current Output
```bash
# style.css references 30+ files
public/assets/css/
  style.css                    # Has 30+ @import statements
  tokens/foundation.css        # HTTP request #1
  tokens/semantic.css          # HTTP request #2
  base/reset.css               # HTTP request #3
  base/typography.css          # HTTP request #4
  # ... 26+ more files ...
```

**Result**: 30+ sequential HTTP requests for CSS! 🐌

---

## Performance Impact

### Current (Without Bundling)
```
DNS Lookup: 20ms
TCP Connect: 50ms
TLS Handshake: 100ms
Request #1 (style.css): 170ms
  ↓ Parse, see @import
Request #2 (foundation.css): 50ms
Request #3 (semantic.css): 50ms
Request #4 (reset.css): 50ms
... 26 more requests ...

Total: ~1,500-2,000ms to load CSS 😱
```

### With Bundling
```
Request #1 (style.css with everything inlined): 200ms

Total: ~200ms to load CSS ✅
```

**Improvement**: 7-10x faster CSS loading!

---

## Solutions (Ranked by Complexity)

### Option 1: PostCSS (Standard Industry Solution) ⭐ RECOMMENDED

**What It Is**: CSS processor with plugins for everything

**Install**:
```bash
npm install -D postcss postcss-cli postcss-import autoprefixer cssnano
```

**Config** (`postcss.config.js`):
```javascript
module.exports = {
  plugins: {
    'postcss-import': {},           // Inline @import
    'autoprefixer': {},              // Add vendor prefixes
    'cssnano': {                     // Minify
      preset: 'default'
    }
  }
};
```

**Integrate with Bengal**:
```python
# In Asset._process_css()
def _process_css(self) -> None:
    """Process CSS with PostCSS (if available)."""
    try:
        import subprocess
        result = subprocess.run(
            ['npx', 'postcss', str(self.source_path), '--no-map'],
            capture_output=True,
            text=True,
            check=True
        )
        self._processed_content = result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback to basic minification
        self.minify()
```

**Pros**:
- ✅ Industry standard (used by Tailwind, Bootstrap, etc.)
- ✅ Rich plugin ecosystem
- ✅ Autoprefixer for browser compatibility
- ✅ Can add more plugins later (nesting, custom properties, etc.)
- ✅ Fast (written in JS, but fast enough)

**Cons**:
- ⚠️ Requires Node.js/npm
- ⚠️ External dependency

**Effort**: 1-2 days
- Python integration: 4 hours
- Testing: 2 hours
- Documentation: 2 hours
- Config examples: 1 hour

---

### Option 2: Lightning CSS (Fastest) ⚡

**What It Is**: Rust-based CSS bundler/minifier (super fast)

**Install**:
```bash
npm install -D lightningcss-cli
# or
pip install lightningcss  # Python bindings!
```

**Python Integration**:
```python
from lightningcss import CSSMinifier

def _process_css(self) -> None:
    """Process CSS with Lightning CSS."""
    minifier = CSSMinifier()
    with open(self.source_path, 'r') as f:
        result = minifier.minify(
            f.read(),
            bundle=True,              # Inline @import
            minify=True,
            autoprefixer=True,
            targets={
                'chrome': 90,
                'firefox': 88,
                'safari': 14
            }
        )
    self._processed_content = result
```

**Pros**:
- ✅ SUPER FAST (written in Rust)
- ✅ Python bindings available!
- ✅ All-in-one (bundle, minify, autoprefix)
- ✅ No Node.js required (if using Python bindings)
- ✅ Modern CSS support (nesting, custom media, etc.)

**Cons**:
- ⚠️ Newer tool (less mature than PostCSS)
- ⚠️ Python bindings might lag behind CLI

**Effort**: 1 day
- Python integration: 2 hours
- Testing: 2 hours
- Documentation: 2 hours

---

### Option 3: Pure Python CSS Bundler (Simple)

**What It Is**: Custom Python script to inline @import statements

**Implementation**:
```python
import re
from pathlib import Path

def bundle_css(entry_file: Path, base_dir: Path) -> str:
    """Bundle CSS by inlining all @import statements."""

    def resolve_import(match):
        import_path = match.group(1)
        imported_file = base_dir / import_path

        if not imported_file.exists():
            return f"/* Could not find: {import_path} */"

        # Recursively process imports in imported file
        content = imported_file.read_text(encoding='utf-8')
        return process_imports(content, imported_file.parent)

    def process_imports(content: str, current_dir: Path) -> str:
        # Match: @import url('...')  or  @import '...'
        pattern = r'@import\s+(?:url\()?[\'"]([^\'"]+)[\'"](?:\))?;?'

        def resolver(m):
            path = m.group(1)
            full_path = current_dir / path
            if full_path.exists():
                imported = full_path.read_text(encoding='utf-8')
                # Recursively process nested imports
                return process_imports(imported, full_path.parent)
            return f"/* Missing: {path} */"

        return re.sub(pattern, resolver, content)

    entry_content = entry_file.read_text(encoding='utf-8')
    bundled = process_imports(entry_content, entry_file.parent)

    return bundled

# In Asset class:
def bundle(self) -> 'Asset':
    """Bundle CSS (inline all @import statements)."""
    if self.asset_type == 'css':
        bundled = bundle_css(self.source_path, self.source_path.parent)
        self._processed_content = bundled
        self.bundled = True
    return self
```

**Pros**:
- ✅ No external dependencies
- ✅ Pure Python (easy to debug)
- ✅ Fast (for reasonable file counts)
- ✅ Simple to understand

**Cons**:
- ❌ No autoprefixing
- ❌ No advanced transforms
- ❌ Need to write our own logic
- ❌ Edge cases (relative paths, URL imports, etc.)

**Effort**: 2-3 days
- Bundler implementation: 1 day
- Edge case handling: 0.5 day
- Testing: 0.5 day
- Integration: 0.5 day

---

### Option 4: Parcel / esbuild (Overkill)

**What It Is**: Full JavaScript bundlers

**Why NOT Recommended**:
- 🔴 Way too heavy for our needs
- 🔴 Requires Node.js build step
- 🔴 Complex configuration
- 🔴 Slower than Lightning CSS

---

## Comparison Matrix

| Solution | Speed | Setup | Features | Dependencies | Effort |
|----------|-------|-------|----------|--------------|--------|
| **PostCSS** | Good | Medium | Excellent | Node.js | 1-2 days |
| **Lightning CSS** | Excellent | Easy | Great | Python/npm | 1 day |
| **Pure Python** | Good | None | Basic | None | 2-3 days |
| **Parcel/esbuild** | Good | Hard | Overkill | Node.js | 3+ days |

---

## Recommendation: Lightning CSS ⚡

**Why**:
1. **Python bindings** - No Node.js subprocess required
2. **Super fast** - Rust-based performance
3. **All-in-one** - Bundling + minification + autoprefixer
4. **Modern CSS** - Supports latest features
5. **Easy integration** - Drop-in replacement for csscompressor

**Implementation Plan**:

### Phase 1: Add Lightning CSS support (1 day)
```python
# bengal/core/asset.py

def _process_css(self) -> None:
    """Process CSS with bundling and minification."""
    try:
        # Try Lightning CSS first (if installed)
        import lightningcss

        minifier = lightningcss.CSSMinifier()
        with open(self.source_path, 'r', encoding='utf-8') as f:
            result = minifier.minify(
                f.read(),
                bundle=True,           # Inline @import
                minify=True,
                autoprefixer={
                    'chrome': 90,
                    'firefox': 88,
                    'safari': 14,
                    'edge': 90
                }
            )

        self._minified_content = result
        self.bundled = True

    except ImportError:
        # Fallback: Basic minification (no bundling)
        print("⚠️  lightningcss not installed, CSS not bundled")
        print("   Install: pip install lightningcss")
        self._minify_css_basic()
```

### Phase 2: Update requirements
```txt
# requirements.txt
lightningcss>=1.0.0  # Optional but recommended
```

### Phase 3: Configuration
```toml
# bengal.toml
[assets]
bundle_css = true           # Bundle @import (requires lightningcss)
minify = true
autoprefixer = true
fingerprint = true

[assets.browser_targets]
chrome = 90
firefox = 88
safari = 14
edge = 90
```

### Phase 4: Documentation
```markdown
## CSS Processing

Bengal can bundle and optimize CSS using Lightning CSS:

1. Install: `pip install lightningcss`
2. Enable in config: `bundle_css = true`
3. Build: `bengal build`

Your CSS will be:
- ✅ Bundled (all @import inlined)
- ✅ Minified
- ✅ Autoprefixed for browser compatibility
- ✅ Fingerprinted for cache busting

Without lightningcss, only minification is applied.
```

---

## Alternative: PostCSS (If Lightning CSS has issues)

**Fallback Implementation**:
```python
def _process_css_with_postcss(self) -> None:
    """Process CSS with PostCSS via subprocess."""
    import subprocess
    import shutil

    # Check if postcss is available
    if not shutil.which('postcss'):
        self._minify_css_basic()
        return

    try:
        # Run postcss with our config
        result = subprocess.run(
            [
                'npx', 'postcss',
                str(self.source_path),
                '--no-map',
                '--config', 'postcss.config.js'
            ],
            capture_output=True,
            text=True,
            check=True,
            cwd=self.source_path.parent
        )

        self._minified_content = result.stdout
        self.bundled = True

    except subprocess.CalledProcessError:
        print("⚠️  PostCSS failed, falling back to basic minification")
        self._minify_css_basic()
```

**PostCSS Config**:
```javascript
// postcss.config.js (in theme directory)
module.exports = {
  plugins: {
    'postcss-import': {
      path: ['.']
    },
    'autoprefixer': {
      overrideBrowserslist: [
        'last 2 chrome versions',
        'last 2 firefox versions',
        'last 2 safari versions',
        'last 2 edge versions'
      ]
    },
    'cssnano': {
      preset: ['default', {
        discardComments: { removeAll: true }
      }]
    }
  }
};
```

---

## Implementation Timeline

### Week 1: Lightning CSS (Primary)
- **Day 1-2**: Python integration
  - Add lightningcss dependency
  - Implement bundling in Asset class
  - Add configuration options
- **Day 3**: Testing
  - Test with default theme
  - Test bundling correctness
  - Test autoprefixer output
- **Day 4**: Documentation
  - Update ARCHITECTURE.md
  - Add CSS processing guide
  - Update asset management comparison

### Week 2: PostCSS (Fallback)
- **Day 1-2**: Subprocess integration
  - Implement PostCSS processor
  - Add config file generation
  - Handle errors gracefully
- **Day 3**: Testing
  - Test both paths (Lightning CSS + PostCSS)
  - Test fallback behavior
  - Performance benchmarks

---

## Success Metrics

### Before (Current)
```
CSS Load Time: ~1,500-2,000ms
HTTP Requests: 30+ (style.css + 30 imports)
Total CSS Size: ~50KB (uncompressed)
Browser Compatibility: Manual prefixes only
```

### After (With Bundling)
```
CSS Load Time: ~200ms
HTTP Requests: 1 (bundled style.css)
Total CSS Size: ~35KB (compressed + bundled)
Browser Compatibility: Autoprefixed for target browsers
```

**Improvement**: **7-10x faster CSS loading** 🚀

---

## Browser Compatibility

### Current Issues (Without Autoprefixer)
```css
/* We write: */
.button {
  display: flex;
  transition: all 0.2s;
}

/* What older browsers need: */
.button {
  display: -webkit-box;      /* Missing! */
  display: -ms-flexbox;      /* Missing! */
  display: flex;
  -webkit-transition: all 0.2s;  /* Missing! */
  transition: all 0.2s;
}
```

### With Autoprefixer
All vendor prefixes added automatically based on browser targets!

---

## Migration Plan (Zero Breaking Changes)

### Phase 1: Add opt-in bundling
```toml
[assets]
bundle_css = false  # Default: off (no breaking change)
```

### Phase 2: Enable for new sites
```toml
# In project templates
[assets]
bundle_css = true  # Recommended for new sites
```

### Phase 3: Make it default (v0.5.0)
```toml
[assets]
bundle_css = true  # Default: on
```

---

## Questions & Answers

### Q: Do we need Node.js?
**A**:
- Lightning CSS (Python): NO
- Lightning CSS (CLI): Yes
- PostCSS: Yes

**Recommendation**: Use Lightning CSS Python bindings (no Node.js)

### Q: What about existing sites?
**A**: Opt-in via config. No breaking changes.

### Q: Performance impact on build?
**A**:
- Lightning CSS: ~50-100ms (fast!)
- PostCSS: ~200-500ms (still fast)
- Current (no bundling): ~50ms

**Worth it?** YES! 7-10x faster page loads.

### Q: What about SCSS/SASS?
**A**: Different feature. This is for bundling plain CSS. SCSS is separate (see asset management comparison).

---

## Conclusion

**MUST DO**: Add CSS bundling to Bengal

**Top Priority**: CSS bundling is causing 30+ HTTP requests per page

**Recommended Solution**: Lightning CSS with Python bindings

**Timeline**: 1-2 weeks for complete implementation

**Impact**: 7-10x faster CSS loading for all Bengal sites

---

## Next Steps

1. ✅ Get approval for Lightning CSS approach
2. Install and test `lightningcss` Python package
3. Implement in Asset class with fallback
4. Add configuration options
5. Test with default theme
6. Update documentation
7. Benchmark performance improvements
8. Ship in v0.3.0
