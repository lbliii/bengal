# Multiple Output Formats & Offline Support - Implementation Plan

**Status**: 📋 Planning  
**Owner**: TBD  
**Target Version**: v0.3.0  
**Created**: 2025-10-12  
**Priority**: Medium-High (Competitive Feature)

## Overview

Extend Bengal to support multiple output formats (PDF, ePub, LaTeX) and optimize for offline/static hosting (S3, CDN). This closes the gap with Sphinx while maintaining Bengal's performance advantages.

### Goals

1. **Multiple formats**: Generate PDF, ePub alongside HTML
2. **Offline-first**: Service workers, app manifest, offline caching
3. **S3/CDN optimized**: Proper paths, asset manifests, CDN-friendly structure
4. **Incremental**: Only regenerate changed formats
5. **Fast**: Parallel format generation, minimal overhead
6. **Configurable**: Per-format options, selective generation

### Non-Goals

- Real-time format conversion (all formats generated at build time)
- Print CSS only (need actual PDF files)
- Video/audio formats (focus on document formats)
- Server-side rendering (static output only)

## Architecture

### Output Format Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    Build Pipeline                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Core Build                                              │
│     └─> HTML output (existing)                             │
│                                                             │
│  2. Format Generation ⭐ NEW                                │
│     ├─> PDF Generator                                      │
│     │   └─> Uses HTML + print CSS                         │
│     │   └─> WeasyPrint or Playwright                      │
│     ├─> ePub Generator                                     │
│     │   └─> EPUB3 format                                   │
│     │   └─> EbookLib                                       │
│     ├─> LaTeX Generator (optional)                         │
│     │   └─> Template-based conversion                     │
│     └─> Markdown Bundle (optional)                         │
│         └─> Standalone markdown archive                    │
│                                                             │
│  3. Offline Optimization ⭐ NEW                             │
│     ├─> Service Worker Generation                          │
│     ├─> Web App Manifest                                   │
│     ├─> Asset Manifest (for versioning)                    │
│     └─> Offline page generation                            │
│                                                             │
│  4. S3/CDN Optimization ⭐ NEW                              │
│     ├─> Asset fingerprinting (existing)                    │
│     ├─> Immutable asset headers manifest                   │
│     ├─> CDN path rewriting                                 │
│     └─> Deployment manifest                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Format Architecture

```python
# Core abstraction
class OutputFormat:
    """Base class for all output formats."""

    name: str           # "pdf", "epub", "latex"
    extension: str      # ".pdf", ".epub", ".tex"
    mimetype: str      # "application/pdf"

    def generate(self, site: Site, config: dict) -> Path:
        """Generate format output."""
        pass

    def should_regenerate(self, cache: BuildCache) -> bool:
        """Check if format needs regeneration."""
        pass

# Format registry
class FormatRegistry:
    formats: dict[str, OutputFormat] = {
        'pdf': PDFFormat(),
        'epub': EPubFormat(),
        'latex': LaTeXFormat(),
        'markdown': MarkdownFormat(),
    }
```

## Implementation Phases

### Phase 1: PDF Generation (Week 1-2)

**Goal**: Generate high-quality PDF from HTML

#### Approach A: WeasyPrint (Recommended)

**Pros:**
- Pure Python, easy to install
- CSS Paged Media support
- Good typography
- Fast (2-5 seconds for 100 pages)

**Cons:**
- Limited JavaScript support
- Some CSS3 features missing

```python
# bengal/postprocess/formats/pdf.py
from weasyprint import HTML, CSS

class PDFFormat(OutputFormat):
    name = "pdf"
    extension = ".pdf"
    mimetype = "application/pdf"

    def generate(self, site: Site, config: dict) -> Path:
        """Generate PDF from HTML."""
        output_path = site.output_dir / "site.pdf"

        # Collect all pages in order
        pages = self._get_ordered_pages(site, config)

        # Build single HTML document
        html_content = self._build_pdf_document(pages, site)

        # Generate PDF with print CSS
        pdf = HTML(string=html_content, base_url=str(site.output_dir))

        # Add print stylesheet
        print_css = CSS(filename=self._get_print_css(site))

        pdf.write_pdf(
            output_path,
            stylesheets=[print_css],
            **config.get('pdf_options', {})
        )

        return output_path

    def _build_pdf_document(self, pages: list[Page], site: Site) -> str:
        """Build single HTML for PDF."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{site.config['site']['title']}</title>
        </head>
        <body>
            {self._render_cover_page(site)}
            {self._render_toc(pages)}
            {''.join(self._render_page(p) for p in pages)}
        </body>
        </html>
        """

    def _render_page(self, page: Page) -> str:
        """Render page with page breaks."""
        return f"""
        <section class="page" id="{page.slug}">
            <h1>{page.title}</h1>
            {page.rendered_html}
        </section>
        """
```

#### Approach B: Playwright (Alternative)

**Pros:**
- Perfect HTML/CSS/JS rendering (uses Chromium)
- What you see is what you get

**Cons:**
- Heavier dependency (Chromium binary)
- Slower (10-20 seconds for 100 pages)
- More memory usage

```python
# Alternative implementation
from playwright.sync_api import sync_playwright

class PDFFormatPlaywright(OutputFormat):
    def generate(self, site: Site, config: dict) -> Path:
        """Generate PDF using Chromium."""
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            # Load HTML
            html_path = self._build_single_page_html(site)
            page.goto(f"file://{html_path}")

            # Generate PDF
            page.pdf(
                path=site.output_dir / "site.pdf",
                format="A4",
                print_background=True,
                **config.get('pdf_options', {})
            )

            browser.close()
```

#### Print CSS

```css
/* bengal/themes/default/assets/css/print.css */

/* Page setup */
@page {
    size: A4;
    margin: 2cm 1.5cm;

    @top-center {
        content: string(book-title);
    }

    @bottom-center {
        content: counter(page);
    }
}

/* Cover page */
.cover-page {
    page-break-after: always;
    text-align: center;
    padding-top: 30%;
}

/* Chapters */
section.page {
    page-break-before: always;
}

h1, h2, h3 {
    page-break-after: avoid;
}

/* Code blocks */
pre, .highlight {
    page-break-inside: avoid;
    font-size: 9pt;
    background: #f5f5f5;
    border: 1px solid #ddd;
}

/* Links */
a[href^="http"]::after {
    content: " (" attr(href) ")";
    font-size: 0.8em;
    color: #666;
}

/* Table of contents */
.pdf-toc {
    page-break-after: always;
}

.pdf-toc a::after {
    content: leader('.') target-counter(attr(href), page);
}

/* Hide UI elements */
nav, .search, .edit-link, .github-link {
    display: none !important;
}
```

#### Configuration

```toml
# bengal.toml
[output_formats.pdf]
enabled = true
filename = "site.pdf"  # or "{title}.pdf" for template

# PDF options
[output_formats.pdf.options]
# Page setup
page_size = "A4"           # A4, Letter, Legal
margin_top = "2cm"
margin_bottom = "2cm"
margin_left = "1.5cm"
margin_right = "1.5cm"

# Cover page
include_cover = true
cover_template = "pdf/cover.html"

# Table of contents
include_toc = true
toc_depth = 3

# Content
include_pages = "all"      # all, docs_only, api_only
exclude_pages = ["search", "404"]

# Typography
font_size = "11pt"
line_height = 1.5

# Advanced
engine = "weasyprint"      # weasyprint, playwright
optimize = true            # Compress PDF
```

#### Deliverables (Week 1-2)

- ✅ `bengal/postprocess/formats/pdf.py` - PDF generator
- ✅ Print CSS in default theme
- ✅ Configuration options
- ✅ Cover page template
- ✅ TOC generation for PDF
- ✅ Tests (90%+ coverage)
- ✅ Documentation

**Testing:**
```bash
# Generate PDF
bengal build --format pdf

# Custom config
bengal build --format pdf --pdf-config custom.toml

# Test output
pytest tests/unit/postprocess/formats/test_pdf.py -v
```

---

### Phase 2: ePub Generation (Week 3)

**Goal**: Generate EPUB3 ebook format

#### Implementation

```python
# bengal/postprocess/formats/epub.py
from ebooklib import epub

class EPubFormat(OutputFormat):
    name = "epub"
    extension = ".epub"
    mimetype = "application/epub+zip"

    def generate(self, site: Site, config: dict) -> Path:
        """Generate ePub from content."""
        book = epub.EpubBook()

        # Metadata
        book.set_identifier(site.config['site']['baseurl'])
        book.set_title(site.config['site']['title'])
        book.set_language('en')

        # Add cover
        if cover := config.get('cover_image'):
            book.set_cover('cover.jpg', open(cover, 'rb').read())

        # Add chapters
        chapters = []
        for page in self._get_ordered_pages(site, config):
            chapter = self._create_chapter(page)
            book.add_item(chapter)
            chapters.append(chapter)

        # Add CSS
        style = epub.EpubItem(
            uid="style",
            file_name="style.css",
            media_type="text/css",
            content=self._get_epub_css(site)
        )
        book.add_item(style)

        # TOC and spine
        book.toc = self._build_toc(chapters)
        book.spine = ['nav'] + chapters

        # Navigation
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # Write ePub
        output_path = site.output_dir / f"{site.config['site']['title']}.epub"
        epub.write_epub(output_path, book)

        return output_path

    def _create_chapter(self, page: Page) -> epub.EpubHtml:
        """Convert page to ePub chapter."""
        chapter = epub.EpubHtml(
            title=page.title,
            file_name=f"{page.slug}.xhtml",
            lang='en'
        )

        # Clean HTML for ePub
        content = self._clean_for_epub(page.rendered_html)
        chapter.content = f"""
        <html>
        <head>
            <title>{page.title}</title>
            <link rel="stylesheet" href="style.css" />
        </head>
        <body>
            <h1>{page.title}</h1>
            {content}
        </body>
        </html>
        """

        return chapter

    def _clean_for_epub(self, html: str) -> str:
        """Remove non-ePub compatible elements."""
        # Remove interactive elements
        # Convert relative links to anchors
        # etc.
        return html
```

#### Configuration

```toml
[output_formats.epub]
enabled = true
filename = "{title}.epub"

[output_formats.epub.options]
# Metadata
author = "Your Name"
publisher = "Your Organization"
language = "en"
isbn = ""

# Cover
cover_image = "assets/images/cover.jpg"

# Content
include_pages = "all"
exclude_pages = ["search", "404"]

# TOC
toc_depth = 3

# Styling
css = "themes/default/assets/css/epub.css"
```

#### Deliverables (Week 3)

- ✅ `bengal/postprocess/formats/epub.py`
- ✅ ePub CSS stylesheet
- ✅ Metadata extraction
- ✅ TOC generation
- ✅ Tests
- ✅ Documentation

---

### Phase 3: Offline Support (Week 4)

**Goal**: Enable offline-first web app with service workers

#### Service Worker Generation

```javascript
// bengal/postprocess/offline/templates/service-worker.js.jinja2

const CACHE_NAME = 'bengal-site-{{ cache_version }}';
const OFFLINE_URL = '/offline/';

// Assets to cache on install
const PRECACHE_URLS = [
    '/',
    '/offline/',
    {{ precache_assets | tojson }}
];

// Install - cache core assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(PRECACHE_URLS))
            .then(() => self.skipWaiting())
    );
});

// Activate - cleanup old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(
                keys.filter(key => key !== CACHE_NAME)
                    .map(key => caches.delete(key))
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') return;

    event.respondWith(
        caches.match(event.request)
            .then(response => {
                if (response) {
                    return response;
                }

                return fetch(event.request)
                    .then(response => {
                        // Cache successful responses
                        if (response.ok) {
                            const copy = response.clone();
                            caches.open(CACHE_NAME)
                                .then(cache => cache.put(event.request, copy));
                        }
                        return response;
                    })
                    .catch(() => {
                        // Offline fallback
                        return caches.match(OFFLINE_URL);
                    });
            })
    );
});
```

#### Implementation

```python
# bengal/postprocess/offline/service_worker.py

class ServiceWorkerGenerator:
    """Generate service worker for offline support."""

    def generate(self, site: Site, config: dict) -> None:
        """Generate service worker and manifest."""

        # 1. Generate service worker
        sw_content = self._render_service_worker(site, config)
        sw_path = site.output_dir / "service-worker.js"
        sw_path.write_text(sw_content)

        # 2. Generate web app manifest
        manifest = self._generate_manifest(site, config)
        manifest_path = site.output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        # 3. Generate offline page
        self._generate_offline_page(site)

        # 4. Inject service worker registration
        self._inject_sw_registration(site)

    def _render_service_worker(self, site: Site, config: dict) -> str:
        """Render service worker from template."""
        # Get assets to precache
        precache_assets = self._get_precache_assets(site, config)

        # Generate cache version (hash of content)
        cache_version = self._compute_cache_version(site)

        template = self._load_template('service-worker.js.jinja2')
        return template.render(
            cache_version=cache_version,
            precache_assets=precache_assets,
            config=config
        )

    def _get_precache_assets(self, site: Site, config: dict) -> list[str]:
        """Get list of assets to precache."""
        assets = []

        # Critical CSS/JS
        assets.extend(self._get_critical_assets(site))

        # Core pages (if specified)
        if pages := config.get('precache_pages', []):
            assets.extend(pages)

        # Fonts
        if config.get('precache_fonts', True):
            assets.extend(self._get_font_urls(site))

        return assets

    def _generate_manifest(self, site: Site, config: dict) -> dict:
        """Generate web app manifest."""
        return {
            "name": site.config['site']['title'],
            "short_name": config.get('short_name', site.config['site']['title'][:12]),
            "description": site.config['site'].get('description', ''),
            "start_url": "/",
            "display": "standalone",
            "background_color": config.get('background_color', '#ffffff'),
            "theme_color": config.get('theme_color', '#3b82f6'),
            "icons": self._get_icons(site, config)
        }

    def _generate_offline_page(self, site: Site) -> None:
        """Generate offline fallback page."""
        template = self._load_template('offline.html.jinja2')
        content = template.render(site=site)

        offline_path = site.output_dir / "offline" / "index.html"
        offline_path.parent.mkdir(parents=True, exist_ok=True)
        offline_path.write_text(content)

    def _inject_sw_registration(self, site: Site) -> None:
        """Inject service worker registration into HTML pages."""
        registration_script = """
        <script>
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/service-worker.js')
                    .then(reg => console.log('SW registered:', reg))
                    .catch(err => console.error('SW registration failed:', err));
            });
        }
        </script>
        """
        # Inject into base template or each HTML file
        # Implementation depends on template structure
```

#### Configuration

```toml
[offline]
enabled = true

# Service worker
[offline.service_worker]
# Strategy: cache-first, network-first, stale-while-revalidate
strategy = "cache-first"
cache_name = "bengal-site"

# What to precache
precache_pages = ["/", "/docs/"]
precache_fonts = true
precache_images = false  # Can be large

# Cache limits
max_age_days = 30
max_entries = 100

# Web app manifest
[offline.manifest]
short_name = "Bengal"
background_color = "#ffffff"
theme_color = "#3b82f6"
display = "standalone"

# Icons (PWA)
icons = [
    { src = "/assets/icons/icon-192.png", sizes = "192x192", type = "image/png" },
    { src = "/assets/icons/icon-512.png", sizes = "512x512", type = "image/png" },
]
```

#### Deliverables (Week 4)

- ✅ `bengal/postprocess/offline/service_worker.py`
- ✅ Service worker template
- ✅ Web app manifest generation
- ✅ Offline page template
- ✅ Registration script injection
- ✅ Tests
- ✅ Documentation

---

### Phase 4: S3/CDN Optimization (Week 5)

**Goal**: Optimize output for static hosting and CDNs

#### Asset Manifest

```python
# bengal/postprocess/deployment/asset_manifest.py

class AssetManifestGenerator:
    """Generate manifest for S3/CDN deployment."""

    def generate(self, site: Site) -> dict:
        """Generate asset manifest with metadata."""
        manifest = {
            "version": self._get_build_version(site),
            "build_time": site.build_time.isoformat(),
            "assets": {},
            "pages": {},
            "deployment": {}
        }

        # Scan all output files
        for file_path in site.output_dir.rglob('*'):
            if not file_path.is_file():
                continue

            rel_path = file_path.relative_to(site.output_dir)
            url_path = '/' + str(rel_path).replace('\\', '/')

            # Asset metadata
            metadata = {
                "path": str(rel_path),
                "url": url_path,
                "size": file_path.stat().st_size,
                "hash": self._hash_file(file_path),
                "mime_type": self._get_mime_type(file_path),
                "cache_control": self._get_cache_control(file_path),
                "immutable": self._is_immutable(file_path),
            }

            # Categorize
            if self._is_page(file_path):
                manifest["pages"][url_path] = metadata
            else:
                manifest["assets"][url_path] = metadata

        # Deployment metadata
        manifest["deployment"] = self._generate_deployment_config(site)

        return manifest

    def _get_cache_control(self, file_path: Path) -> str:
        """Determine cache control header."""
        # Fingerprinted assets - immutable
        if self._has_fingerprint(file_path):
            return "public, max-age=31536000, immutable"

        # HTML pages - short cache with revalidation
        if file_path.suffix == '.html':
            return "public, max-age=3600, must-revalidate"

        # Static assets - medium cache
        if file_path.suffix in ('.css', '.js', '.png', '.jpg', '.svg'):
            return "public, max-age=86400"

        # Default
        return "public, max-age=3600"

    def _generate_deployment_config(self, site: Site) -> dict:
        """Generate deployment-specific config."""
        return {
            "s3": {
                "bucket": site.config.get('deployment', {}).get('s3_bucket'),
                "region": site.config.get('deployment', {}).get('s3_region', 'us-east-1'),
                "cloudfront": site.config.get('deployment', {}).get('cloudfront_id'),
            },
            "headers": self._get_custom_headers(site),
            "redirects": self._get_redirects(site),
        }

    def save(self, manifest: dict, output_path: Path) -> None:
        """Save manifest to file."""
        output_path.write_text(json.dumps(manifest, indent=2))
```

#### Deployment Helper

```python
# bengal/postprocess/deployment/s3_deploy.py

class S3Deployer:
    """Deploy to S3 with optimal settings."""

    def __init__(self, manifest: dict):
        self.manifest = manifest
        self.s3_client = None

    def deploy(self, site: Site, config: dict) -> None:
        """Deploy site to S3."""
        import boto3

        # Initialize S3 client
        self.s3_client = boto3.client('s3',
            region_name=config['region']
        )

        bucket = config['bucket']

        # Upload assets with optimal settings
        for asset_path, metadata in self.manifest['assets'].items():
            self._upload_file(
                bucket=bucket,
                local_path=site.output_dir / metadata['path'],
                s3_key=metadata['path'],
                metadata=metadata
            )

        # Upload pages
        for page_path, metadata in self.manifest['pages'].items():
            self._upload_file(
                bucket=bucket,
                local_path=site.output_dir / metadata['path'],
                s3_key=metadata['path'],
                metadata=metadata
            )

        # Invalidate CloudFront cache
        if cloudfront_id := config.get('cloudfront_id'):
            self._invalidate_cloudfront(cloudfront_id)

    def _upload_file(self, bucket: str, local_path: Path,
                     s3_key: str, metadata: dict) -> None:
        """Upload file with optimal headers."""
        extra_args = {
            'ContentType': metadata['mime_type'],
            'CacheControl': metadata['cache_control'],
        }

        # Gzip text files
        if self._should_gzip(local_path):
            extra_args['ContentEncoding'] = 'gzip'
            # TODO: Gzip the file

        self.s3_client.upload_file(
            str(local_path),
            bucket,
            s3_key,
            ExtraArgs=extra_args
        )

    def _invalidate_cloudfront(self, distribution_id: str) -> None:
        """Invalidate CloudFront cache."""
        import boto3
        cf = boto3.client('cloudfront')

        cf.create_invalidation(
            DistributionId=distribution_id,
            InvalidationBatch={
                'Paths': {
                    'Quantity': 1,
                    'Items': ['/*']
                },
                'CallerReference': str(time.time())
            }
        )
```

#### Configuration

```toml
[deployment]
# S3 settings
provider = "s3"  # s3, netlify, vercel, cloudflare
s3_bucket = "my-site-bucket"
s3_region = "us-east-1"
cloudfront_id = "E1234567890ABC"

# Asset optimization
[deployment.assets]
gzip_text_files = true
gzip_threshold = 1024  # bytes
fingerprint_assets = true  # Already done in build

# Cache headers
[deployment.cache]
# HTML pages
html_max_age = 3600
html_must_revalidate = true

# Static assets
static_max_age = 86400

# Fingerprinted assets
immutable_max_age = 31536000

# Custom headers
[deployment.headers]
"/*.html" = { "X-Frame-Options" = "DENY", "X-Content-Type-Options" = "nosniff" }
"/assets/*" = { "Access-Control-Allow-Origin" = "*" }

# Redirects
[deployment.redirects]
"/old-page/" = "/new-page/"
"/docs/" = "/documentation/"
```

#### CLI Integration

```bash
# Generate asset manifest
bengal build --manifest

# Deploy to S3
bengal deploy --provider s3

# Deploy with custom config
bengal deploy --config deployment.toml

# Dry run
bengal deploy --dry-run
```

#### Deliverables (Week 5)

- ✅ `bengal/postprocess/deployment/asset_manifest.py`
- ✅ `bengal/postprocess/deployment/s3_deploy.py`
- ✅ Asset manifest generation
- ✅ S3 deployment script
- ✅ CloudFront invalidation
- ✅ CLI commands
- ✅ Tests
- ✅ Documentation

---

## Format Orchestration

### Unified Format Generation

```python
# bengal/postprocess/formats/__init__.py

class FormatOrchestrator:
    """Orchestrate multiple format generation."""

    def __init__(self):
        self.formats = {
            'pdf': PDFFormat(),
            'epub': EPubFormat(),
            'latex': LaTeXFormat(),
        }

    def generate_formats(self, site: Site, parallel: bool = True) -> dict[str, Path]:
        """Generate all enabled formats."""
        enabled = self._get_enabled_formats(site.config)

        if not enabled:
            return {}

        logger.info(f"Generating {len(enabled)} format(s): {', '.join(enabled)}")

        # Generate in parallel
        if parallel and len(enabled) > 1:
            return self._generate_parallel(site, enabled)
        else:
            return self._generate_sequential(site, enabled)

    def _generate_parallel(self, site: Site, formats: list[str]) -> dict[str, Path]:
        """Generate formats in parallel."""
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=len(formats)) as executor:
            futures = {
                executor.submit(self._generate_format, site, fmt): fmt
                for fmt in formats
            }

            results = {}
            for future in futures:
                fmt = futures[future]
                try:
                    results[fmt] = future.result()
                except Exception as e:
                    logger.error(f"Format generation failed ({fmt}): {e}")

        return results

    def _generate_format(self, site: Site, format_name: str) -> Path:
        """Generate single format."""
        format_obj = self.formats[format_name]
        config = site.config.get('output_formats', {}).get(format_name, {})

        logger.info(f"Generating {format_name}...")
        start = time.time()

        output_path = format_obj.generate(site, config)

        elapsed = time.time() - start
        size = output_path.stat().st_size
        logger.info(f"Generated {format_name}: {size:,} bytes ({elapsed:.2f}s)")

        return output_path
```

### Integration into Build Pipeline

```python
# In bengal/orchestration/build.py

def build(self, site: Site) -> BuildStats:
    # ... existing phases ...

    # Phase 8: Post-processing
    self._run_postprocessing(site)

    # Phase 9: Generate additional formats ⭐ NEW
    if site.config.get('output_formats', {}).get('enabled', False):
        orchestrator = FormatOrchestrator()
        formats = orchestrator.generate_formats(site, parallel=True)
        stats.formats_generated = formats

    # Phase 10: Offline optimization ⭐ NEW
    if site.config.get('offline', {}).get('enabled', False):
        sw_gen = ServiceWorkerGenerator()
        sw_gen.generate(site, site.config['offline'])

    # Phase 11: Deployment manifest ⭐ NEW
    if site.config.get('deployment', {}).get('generate_manifest', False):
        manifest_gen = AssetManifestGenerator()
        manifest = manifest_gen.generate(site)
        manifest_gen.save(manifest, site.output_dir / 'asset-manifest.json')

    return stats
```

## Configuration Reference

### Complete bengal.toml

```toml
[output_formats]
enabled = true

# PDF Generation
[output_formats.pdf]
enabled = true
filename = "{title}.pdf"
engine = "weasyprint"  # weasyprint, playwright

[output_formats.pdf.options]
page_size = "A4"
include_cover = true
include_toc = true
toc_depth = 3
exclude_pages = ["search", "404"]

# ePub Generation
[output_formats.epub]
enabled = true
filename = "{title}.epub"

[output_formats.epub.options]
author = "Your Name"
cover_image = "assets/images/cover.jpg"
toc_depth = 3

# LaTeX (optional)
[output_formats.latex]
enabled = false
template = "book"  # article, book, report

# Offline Support
[offline]
enabled = true

[offline.service_worker]
strategy = "cache-first"
precache_pages = ["/", "/docs/"]
precache_fonts = true

[offline.manifest]
short_name = "Bengal"
theme_color = "#3b82f6"

# Deployment
[deployment]
generate_manifest = true
provider = "s3"

[deployment.s3]
bucket = "my-site-bucket"
region = "us-east-1"
cloudfront_id = "E1234567890ABC"

[deployment.assets]
gzip_text_files = true

[deployment.cache]
html_max_age = 3600
static_max_age = 86400
```

## Testing Strategy

### Unit Tests

```
tests/unit/postprocess/formats/
├── test_pdf.py                 # PDF generation
│   ├── test_weasyprint_generation
│   ├── test_cover_page
│   ├── test_toc_generation
│   └── test_print_css
│
├── test_epub.py                # ePub generation
│   ├── test_epub_structure
│   ├── test_metadata
│   └── test_chapter_creation
│
tests/unit/postprocess/offline/
└── test_service_worker.py      # Service worker generation
    ├── test_sw_generation
    ├── test_manifest_generation
    └── test_precache_list
│
tests/unit/postprocess/deployment/
├── test_asset_manifest.py      # Asset manifest
│   ├── test_manifest_structure
│   ├── test_cache_headers
│   └── test_deployment_config
│
└── test_s3_deploy.py           # S3 deployment
    ├── test_upload_logic
    ├── test_cloudfront_invalidation
    └── test_gzip_compression
```

### Integration Tests

```
tests/integration/
├── test_format_generation.py
│   ├── test_pdf_from_site
│   ├── test_epub_from_site
│   └── test_parallel_generation
│
├── test_offline_support.py
│   ├── test_sw_installation
│   ├── test_offline_functionality
│   └── test_pwa_manifest
│
└── test_deployment.py
    ├── test_s3_upload
    └── test_manifest_accuracy
```

### Performance Tests

```
tests/performance/
├── test_pdf_performance.py
│   ├── test_pdf_generation_speed      # < 10s for 100 pages
│   └── test_pdf_file_size             # Reasonable compression
│
└── test_offline_overhead.py
    └── test_sw_cache_size             # Cache size limits
```

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| **PDF generation (100 pages)** | < 10 seconds | WeasyPrint baseline |
| **ePub generation (100 pages)** | < 5 seconds | Lighter format |
| **Service worker generation** | < 100ms | Template rendering |
| **Asset manifest generation** | < 500ms | File scanning |
| **S3 upload (100 files)** | < 30 seconds | Network dependent |
| **Build overhead** | < 5% | When formats disabled |

## Dependencies

### New Python Dependencies

```toml
# pyproject.toml additions
dependencies = [
    # ... existing ...

    # PDF generation (choose one)
    "weasyprint>=60.0",        # Recommended
    # "playwright>=1.40.0",    # Alternative

    # ePub generation
    "ebooklib>=0.18",

    # Deployment
    "boto3>=1.34.0",           # AWS S3/CloudFront
]
```

## Timeline

### Week 1-2: PDF Generation (Oct 22 - Nov 2)
- ✅ PDFFormat class
- ✅ WeasyPrint integration
- ✅ Print CSS
- ✅ Cover & TOC generation
- ✅ Tests & docs

### Week 3: ePub Generation (Nov 5-9)
- ✅ EPubFormat class
- ✅ EPUB3 generation
- ✅ Metadata & TOC
- ✅ Tests & docs

### Week 4: Offline Support (Nov 12-16)
- ✅ Service worker generation
- ✅ Web app manifest
- ✅ Offline page
- ✅ PWA features
- ✅ Tests & docs

### Week 5: S3/CDN (Nov 19-23)
- ✅ Asset manifest
- ✅ S3 deployment
- ✅ CloudFront integration
- ✅ CLI commands
- ✅ Tests & docs

**Total: 5 weeks**

## Success Criteria

- ✅ Generate PDF with < 10s for 100 pages
- ✅ Generate valid EPUB3 files
- ✅ Service worker caches assets correctly
- ✅ Offline mode works without network
- ✅ Asset manifest includes all metadata
- ✅ S3 deployment sets correct headers
- ✅ 90%+ test coverage for new code
- ✅ Documentation complete
- ✅ CLI integration seamless

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **WeasyPrint CSS limitations** | Medium | Fall back to Playwright or document limitations |
| **Large PDF file sizes** | Medium | Implement compression, optimize images |
| **Service worker compatibility** | Low | Progressive enhancement, feature detection |
| **S3 deployment errors** | Low | Dry-run mode, validation, rollback |
| **Build time increase** | Medium | Parallel generation, make formats optional |

## Future Enhancements (Post-v0.3.0)

1. **More formats**: AsciiDoc, Markdown bundles
2. **Better PDF**: Bookmarks, cross-references, index
3. **Progressive Web App**: Full PWA with install prompt
4. **Deployment providers**: Netlify, Vercel, Cloudflare Pages
5. **Format plugins**: Custom format support
6. **Optimization**: Image optimization in PDF/ePub

## References

- [WeasyPrint Docs](https://doc.courtbouillon.org/weasyprint/)
- [EbookLib](https://github.com/aerkalov/ebooklib)
- [Service Workers API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [Web App Manifest](https://developer.mozilla.org/en-US/docs/Web/Manifest)
- [AWS S3 Static Hosting](https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html)

---

**Next Steps:**
1. Review and approve this plan
2. Install and test WeasyPrint
3. Create sample PDF templates
4. Begin Phase 1 development
