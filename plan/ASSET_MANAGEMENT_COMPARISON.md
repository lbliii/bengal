# Asset Management Feature Comparison: Bengal vs Hugo vs Sphinx

**Date**: October 8, 2025  
**Status**: Feature Audit  
**Purpose**: Compare Bengal's asset management capabilities with Hugo and Sphinx

---

## Executive Summary

**Bengal's Current State**: ✅ **Good foundation, missing some advanced features**

Bengal has solid **basic asset management** (copying, minification, optimization, fingerprinting) but lacks some **advanced features** found in Hugo like asset pipelines, bundling, PostCSS/SCSS processing, and image processing.

Compared to Sphinx (which has minimal asset management), Bengal is **significantly better**. Compared to Hugo (which has comprehensive Hugo Pipes), Bengal covers **core needs but lacks advanced workflow tooling**.

---

## Feature Matrix

| Feature | Bengal | Hugo | Sphinx | Notes |
|---------|--------|------|--------|-------|
| **Basic Features** | | | | |
| Copy assets to output | ✅ Yes | ✅ Yes | ✅ Yes | All support basic copying |
| Preserve directory structure | ✅ Yes | ✅ Yes | ✅ Yes | All preserve paths |
| CSS/JS minification | ✅ Yes | ✅ Yes | ❌ No | Bengal: csscompressor, jsmin |
| Image optimization | ⚠️ Basic | ✅ Advanced | ❌ No | Bengal: basic Pillow, Hugo: full pipeline |
| Fingerprinting/cache busting | ✅ Yes | ✅ Yes | ⚠️ Basic | Bengal: SHA256, Hugo: SHA256/MD5 |
| Theme assets | ✅ Yes | ✅ Yes | ✅ Yes | All support theme assets |
| Asset override (site > theme) | ✅ Yes | ✅ Yes | ✅ Yes | All support overriding |
| Parallel processing | ✅ Yes | ✅ Yes | ❌ No | Bengal: 3-4x speedup |
| **Advanced Features** | | | | |
| Asset bundling/concatenation | ❌ No | ✅ Yes | ❌ No | Hugo: `resources.Concat` |
| SCSS/SASS compilation | ❌ No | ✅ Yes | ❌ No | Hugo: `resources.ToCSS` |
| PostCSS processing | ❌ No | ✅ Yes | ❌ No | Hugo: `resources.PostCSS` |
| Asset pipelines (chaining) | ❌ No | ✅ Yes | ❌ No | Hugo: `.Minify.Fingerprint` |
| Image resizing/cropping | ❌ No | ✅ Yes | ❌ No | Hugo: `.Resize`, `.Fit`, `.Fill` |
| Image format conversion | ❌ No | ✅ Yes | ❌ No | Hugo: WebP, AVIF conversion |
| Responsive images (srcset) | ⚠️ Template fn | ✅ Built-in | ❌ No | Bengal: `image_srcset()` helper |
| Remote asset fetching | ❌ No | ✅ Yes | ❌ No | Hugo: `resources.GetRemote` |
| Asset templates/processing | ❌ No | ✅ Yes | ❌ No | Hugo: Execute templates on assets |
| Subresource Integrity (SRI) | ❌ No | ✅ Yes | ❌ No | Hugo: `.Data.Integrity` |
| Inline assets in HTML | ❌ No | ✅ Yes | ❌ No | Hugo: `.Content` to inline |
| Custom asset processors | ❌ No | ✅ Yes | ❌ No | Hugo: Babel, custom commands |
| **Organization** | | | | |
| Multiple asset directories | ⚠️ One | ✅ Multiple | ⚠️ One | Hugo: Multiple asset dirs |
| Asset includes from content | ❌ No | ✅ Yes | ⚠️ Limited | Hugo: Page bundles |
| Per-page assets (bundles) | ❌ No | ✅ Yes | ❌ No | Hugo: Page bundles |
| **Configuration** | | | | |
| Toggle minify/optimize | ✅ Yes | ✅ Yes | N/A | Bengal: `bengal.toml` |
| Toggle fingerprinting | ✅ Yes | ✅ Yes | N/A | |
| Configure output paths | ⚠️ Fixed | ✅ Flexible | ⚠️ Fixed | Hugo: Custom publish dir |

---

## Detailed Comparison

### 1. Basic Asset Handling

#### Bengal ✅ Strong
```toml
# bengal.toml
[assets]
minify = true          # Minify CSS/JS
optimize = true        # Optimize images
fingerprint = true     # Add content hash to filenames
```

**Assets Structure:**
```
assets/
  css/
    style.css → public/assets/css/style.a1b2c3d4.css
  js/
    main.js → public/assets/js/main.e5f6g7h8.js
  images/
    logo.png → public/assets/images/logo.12345678.png
```

**Features:**
- ✅ Automatic discovery from `assets/` directory
- ✅ SHA256 fingerprinting (8-character hash)
- ✅ CSS minification (csscompressor)
- ✅ JS minification (jsmin)
- ✅ Image optimization (Pillow with quality=85)
- ✅ Parallel processing (3-4x speedup for 50+ assets)
- ✅ Theme assets + site assets (site overrides theme)
- ✅ Preserves directory structure
- ✅ Atomic writes (crash-safe)

**Limitations:**
- ❌ No bundling/concatenation
- ❌ No SCSS/SASS compilation
- ❌ No PostCSS processing
- ❌ No image resizing/cropping
- ❌ Single asset directory (no multiple sources)

---

#### Hugo ✅ Excellent (Hugo Pipes)
```go
{{ $css := resources.Get "scss/main.scss" }}
{{ $css = $css | resources.ToCSS | resources.Minify | resources.Fingerprint }}
<link rel="stylesheet" href="{{ $css.RelPermalink }}" integrity="{{ $css.Data.Integrity }}">

{{ $js := resources.Get "js/main.js" | resources.Minify | resources.Fingerprint }}
<script src="{{ $js.RelPermalink }}" integrity="{{ $js.Data.Integrity }}"></script>

{{ $img := resources.Get "images/hero.jpg" }}
{{ $img = $img.Resize "800x" }}
<img src="{{ $img.RelPermalink }}" alt="Hero">
```

**Hugo Pipes Features:**
- ✅ Asset bundling/concatenation (`resources.Concat`)
- ✅ SCSS/SASS compilation (`resources.ToCSS`)
- ✅ PostCSS processing (`resources.PostCSS`)
- ✅ Minification (CSS, JS, HTML, SVG)
- ✅ Fingerprinting (SHA256, SHA384, SHA512, MD5)
- ✅ Image processing (resize, crop, fit, fill, filter)
- ✅ Image format conversion (WebP, AVIF)
- ✅ Remote resource fetching (`resources.GetRemote`)
- ✅ Asset templates (execute Go templates on assets)
- ✅ Subresource Integrity (SRI) hashes
- ✅ Inline assets (`.Content` to embed)
- ✅ Custom processors (Babel, Tailwind, etc.)
- ✅ Multiple asset directories
- ✅ Page bundles (per-page assets)

---

#### Sphinx ⚠️ Minimal
```python
# conf.py
html_static_path = ['_static']
html_css_files = ['custom.css']
html_js_files = ['custom.js']
```

**Features:**
- ✅ Copy static files to output
- ✅ Theme assets
- ⚠️ Basic fingerprinting (version query string)
- ❌ No minification
- ❌ No optimization
- ❌ No image processing
- ❌ No bundling
- ❌ No SCSS/SASS

**Verdict**: Sphinx asset handling is **very basic** - just copies files. No processing at all.

---

### 2. Image Processing

#### Bengal ⚠️ Basic Optimization Only
```python
# In Asset class
def _optimize_image(self) -> None:
    """Optimize image assets."""
    from PIL import Image
    img = Image.open(self.source_path)
    # Basic optimization - convert to RGB, save with quality=85
    self._optimized_image = img
```

**Template Helper:**
```jinja2
{# Bengal has helper function for srcset #}
{{ image_srcset('hero.jpg', [320, 640, 1024, 1920]) }}
```

**Features:**
- ✅ Basic optimization (Pillow)
- ✅ Format detection (jpg, png, gif, svg, webp)
- ✅ Template helper for responsive images
- ❌ No resizing/cropping
- ❌ No format conversion
- ❌ No filters/effects
- ❌ No automatic responsive image generation

---

#### Hugo ✅ Comprehensive Image Processing
```go
{{ $img := resources.Get "images/hero.jpg" }}

{# Resize #}
{{ $thumb := $img.Resize "300x" }}
{{ $sized := $img.Resize "800x600" }}

{# Fit (crop to exact size) #}
{{ $fit := $img.Fit "800x600" }}

{# Fill (zoom to fill) #}
{{ $fill := $img.Fill "800x600 center" }}

{# Convert format #}
{{ $webp := $img.Resize "800x webp" }}

{# Filters #}
{{ $processed := $img | images.Filter (images.GaussianBlur 6) }}

{# Automatic srcset #}
<img srcset="{{ range $img.Resize "300x, 600x, 900x" }}{{ .RelPermalink }} {{ .Width }}w{{ end }}">
```

**Features:**
- ✅ Resize (scale)
- ✅ Fit (crop to dimensions)
- ✅ Fill (zoom and crop)
- ✅ Format conversion (WebP, AVIF, PNG, JPG)
- ✅ Quality control
- ✅ Filters (blur, brightness, contrast, etc.)
- ✅ Automatic responsive images
- ✅ EXIF data extraction
- ✅ Smart cropping (face detection)

---

### 3. CSS/JS Processing

#### Bengal ✅ Basic Minification
```python
# Automatic minification
# style.css → style.a1b2c3d4.css (minified)
# main.js → main.e5f6g7h8.js (minified)
```

**Features:**
- ✅ CSS minification (csscompressor)
- ✅ JS minification (jsmin)
- ✅ Fingerprinting
- ❌ No SCSS/SASS
- ❌ No PostCSS
- ❌ No bundling
- ❌ No tree shaking
- ❌ No transpiling (Babel, TypeScript)

**Workaround:** Use external build tools (npm, webpack, vite) and output to `assets/`

---

#### Hugo ✅ Full CSS/JS Pipeline
```go
{# SCSS compilation #}
{{ $css := resources.Get "scss/main.scss" }}
{{ $css = $css | resources.ToCSS (dict "targetPath" "css/main.css") }}

{# PostCSS processing #}
{{ $css = $css | resources.PostCSS }}

{# Minify and fingerprint #}
{{ $css = $css | resources.Minify | resources.Fingerprint }}

{# Bundle multiple files #}
{{ $js := resources.Get "js/lib1.js" | resources.Concat "js/bundle.js" }}
{{ $js = $js | resources.Minify | resources.Fingerprint }}

{# Babel transpiling #}
{{ $js = resources.Get "js/es6.js" | js.Build (dict "target" "es2015") }}
```

**Features:**
- ✅ SCSS/SASS compilation (LibSass)
- ✅ PostCSS processing (Tailwind, Autoprefixer, etc.)
- ✅ JS bundling (esbuild)
- ✅ Babel transpiling
- ✅ TypeScript compilation
- ✅ Tree shaking
- ✅ Source maps
- ✅ Minification
- ✅ Concatenation

---

### 4. Theme Assets

#### All Three Support Theme Assets ✅

**Bengal:**
```
themes/default/assets/
  css/style.css
  js/main.js

# Site assets override theme assets
assets/
  css/style.css  ← This wins
```

**Hugo:**
```
themes/mytheme/assets/
  scss/main.scss

# Site overrides
assets/
  scss/main.scss  ← This wins
```

**Sphinx:**
```python
# Theme specifies static files
html_theme_path = ['_themes']
html_static_path = ['_static']  # Site overrides
```

**All three** allow:
- ✅ Theme assets
- ✅ Site assets override theme
- ✅ Asset discovery from both locations

---

### 5. Fingerprinting & Cache Busting

#### Bengal ✅ SHA256 Fingerprinting
```bash
# Input
assets/css/style.css

# Output
public/assets/css/style.a1b2c3d4.css

# Template automatically uses fingerprinted path
<link rel="stylesheet" href="/assets/css/style.a1b2c3d4.css">
```

**Features:**
- ✅ SHA256 hashing (8 characters)
- ✅ Automatic path rewriting in templates
- ✅ Content-based (changes with content)
- ❌ No query string option
- ❌ No SRI (Subresource Integrity)

---

#### Hugo ✅ Multiple Hash Algorithms + SRI
```go
{{ $css := resources.Get "css/main.css" | resources.Fingerprint "sha384" }}
<link rel="stylesheet" href="{{ $css.RelPermalink }}" integrity="{{ $css.Data.Integrity }}">

# Output:
# /css/main.min.a1b2c3d4e5f6.css
# integrity="sha384-abc123..."
```

**Features:**
- ✅ Multiple algorithms (SHA256, SHA384, SHA512, MD5)
- ✅ SRI hashes for security
- ✅ Flexible hash length
- ✅ Query string option

---

#### Sphinx ⚠️ Version Query String
```python
# Adds ?v=123 to assets
# style.css?v=1234567890
```

**Features:**
- ⚠️ Basic query string versioning
- ❌ Not content-based
- ❌ No SRI

---

### 6. Asset Bundling

#### Bengal ❌ No Bundling
**Status**: Not implemented

**Workaround:**
```bash
# Use external bundler
npm install --save-dev esbuild
npx esbuild src/app.js --bundle --outfile=assets/js/bundle.js

# Then Bengal copies to output
bengal build
```

---

#### Hugo ✅ Built-in Bundling
```go
# Concatenate multiple JS files
{{ $js := slice
  (resources.Get "js/jquery.js")
  (resources.Get "js/app.js")
  | resources.Concat "js/bundle.js"
  | resources.Minify
}}

# Bundle with esbuild
{{ $js := resources.Get "js/main.js" | js.Build (dict "minify" true) }}
```

**Features:**
- ✅ `resources.Concat` for simple bundling
- ✅ esbuild integration for smart bundling
- ✅ Tree shaking
- ✅ Code splitting
- ✅ External dependencies

---

### 7. Performance

#### Bengal ✅ Parallel Processing
```toml
[build]
parallel = true        # Default: true
max_workers = 8        # Auto-detect by default
```

**Performance:**
- ✅ Parallel asset processing (3-4x speedup for 50+ assets)
- ✅ Incremental builds (only changed assets)
- ✅ Smart thresholds (5+ assets for parallelism)
- ✅ Efficient file I/O (atomic writes)

**Benchmarks:**
- 50 assets: 3.01x speedup
- 100 assets: 4.21x speedup

---

#### Hugo ✅ Fast Native Performance
- ✅ Native Go (very fast)
- ✅ Parallel processing
- ✅ Efficient caching

---

#### Sphinx ⚠️ Sequential Only
- ❌ No parallel processing
- ❌ No optimization
- ⚠️ Slow for large sites

---

## Feature Gaps

### Bengal Missing Features

#### High Priority (Common Use Cases)
1. **SCSS/SASS Compilation** ⚠️
   - **Impact**: Many projects use SCSS
   - **Workaround**: External build step (npm scripts)
   - **Recommendation**: Add `libsass` or `dart-sass` support

2. **Asset Bundling** ⚠️
   - **Impact**: Multiple JS files = multiple HTTP requests
   - **Workaround**: External bundler (webpack, esbuild)
   - **Recommendation**: Add simple concatenation at minimum

3. **Image Resizing** ⚠️
   - **Impact**: Responsive images require manual work
   - **Workaround**: Pre-process images externally
   - **Recommendation**: Add `Pillow` resize/crop methods

#### Medium Priority (Nice to Have)
4. **PostCSS Processing**
   - **Impact**: Tailwind CSS users need this
   - **Workaround**: External postcss-cli
   - **Recommendation**: Add postcss-cli integration

5. **Advanced Image Optimization**
   - **Impact**: Better compression, WebP conversion
   - **Workaround**: External tools (imagemin, sharp)
   - **Recommendation**: Add format conversion, better compression

6. **Subresource Integrity (SRI)**
   - **Impact**: Security best practice for CDN assets
   - **Workaround**: Manual hash generation
   - **Recommendation**: Add SRI hash generation

#### Low Priority (Advanced Users)
7. **Remote Asset Fetching**
   - **Impact**: Fetch assets from URLs
   - **Workaround**: Download manually
   - **Recommendation**: Add `resources.GetRemote` equivalent

8. **Asset Templates**
   - **Impact**: Generate assets with templates
   - **Workaround**: Pre-generate
   - **Recommendation**: Low priority

9. **Page Bundles**
   - **Impact**: Per-page asset organization
   - **Workaround**: Global assets directory
   - **Recommendation**: Consider for v2.0

---

## Recommendations

### Short Term (v0.3.0)
1. ✅ **Keep current features** - They work well
2. ⚠️ **Add SCSS compilation** - Use `libsass-python` or subprocess to `sass` CLI
3. ⚠️ **Add simple bundling** - Concatenate multiple files
4. ⚠️ **Add basic image resizing** - Use Pillow `.resize()` and `.thumbnail()`
5. ✅ **Document workarounds** - Show how to use external tools

### Medium Term (v0.4.0)
6. ⚠️ **Add PostCSS integration** - Subprocess to `postcss` CLI
7. ⚠️ **Add WebP conversion** - Use Pillow for image format conversion
8. ⚠️ **Add SRI hashes** - Generate integrity attributes
9. ⚠️ **Add multiple asset directories** - Support `[assets.dirs]` in config

### Long Term (v0.5.0+)
10. ⚠️ **Asset pipeline DSL** - Template functions for asset processing
11. ⚠️ **Remote asset fetching** - Download and cache remote assets
12. ⚠️ **Asset templates** - Execute templates on assets

---

## Conclusion

### Current State: **7/10** (Good Foundation)

**Strengths:**
- ✅ Solid basics (minify, optimize, fingerprint)
- ✅ Parallel processing (faster than sequential)
- ✅ Theme assets + overrides
- ✅ Incremental builds for assets
- ✅ Clean, simple configuration
- ✅ **Better than Sphinx** (which has almost nothing)

**Gaps vs Hugo:**
- ❌ No SCSS/SASS (major gap)
- ❌ No bundling (workaround required)
- ❌ No image resizing (manual work)
- ❌ No PostCSS (Tailwind users need this)
- ❌ No advanced features (SRI, remote, templates)

**Verdict:**
- **For simple sites**: Bengal is **sufficient** ✅
- **For modern workflows** (SCSS, Tailwind, bundling): **Need workarounds** ⚠️
- **Vs Hugo**: Bengal has **60-70% of Hugo's asset features** 📊
- **Vs Sphinx**: Bengal is **significantly better** ✅

### Recommended Priorities

1. **SCSS compilation** (most requested)
2. **Image resizing** (common need)
3. **Asset bundling** (performance)
4. **PostCSS support** (Tailwind, Autoprefixer)
5. **SRI hashes** (security)

**Target:** Reach **85-90%** parity with Hugo's most-used features by v0.5.0

