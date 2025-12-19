# RFC: PDF and EPUB Export — Stellar Offline Documentation Experience

**Status**: Draft  
**Author**: AI Assistant + Lawrence Lane  
**Created**: 2025-12-10  
**Priority**: P2 (Medium)  
**Target**: Bengal 1.x  

---

## Executive Summary

Add first-class PDF and EPUB export to Bengal, enabling users to generate beautiful, production-ready offline documentation with a single command. This fills a significant gap—Bengal's comprehensive web-based documentation system has no native path to print/offline formats.

**Key Proposals**:

1. **Build-time generation** — `bengal build --pdf` and `bengal build --epub` integrate into existing pipeline
2. **Print-optimized CSS** — CSS Paged Media with `@page` rules, automatic TOC, cross-references
3. **Dual rendering engines** — WeasyPrint (default, pure Python) + optional Paged.js (browser-based, highest fidelity)
4. **Bengal directive support** — Tabs collapse to first item, dropdowns expand, code blocks preserve syntax highlighting
5. **Professional typography** — Proper widows/orphans control, hyphenation, running headers/footers
6. **EPUB 3.3 compliance** — Reflowable content, semantic structure, accessibility features

**Primary Value**:
- **Single source of truth** — Same markdown generates web, PDF, and EPUB
- **Professional output** — Typography and layout rivaling commercial documentation
- **Zero friction** — Works out of the box with default theme

---

## 1. Problem Statement

### 1.1 Current Gap

Bengal produces excellent web documentation but offers no path to offline formats. Users who need:

- **Printed documentation** for workshops, training, compliance
- **Offline reading** on planes, in facilities without internet
- **Archival formats** for regulatory/legal requirements
- **E-reader distribution** for technical books, guides
- **Corporate distribution** where PDFs are the standard

...must currently resort to:
- Browser "Print to PDF" (poor quality, broken layouts)
- Manual copy-paste into Word/InDesign (time-consuming, loses source control)
- Third-party tools that don't understand Bengal's directives (broken tabs, cards, etc.)

### 1.2 What Users Experience Today

```bash
# User wants a PDF of their Bengal docs
bengal build
# ... now what?

# Option 1: Browser print (poor results)
# - Tabs show all content stacked (confusing)
# - Dropdowns are collapsed (missing content!)
# - Code blocks overflow page width
# - No table of contents
# - No page numbers

# Option 2: External tool (complex, broken)
# - wkhtmltopdf: deprecated, security issues
# - pandoc: doesn't understand Bengal directives
# - Headless Chrome: massive dependency, still poor results
```

### 1.3 Impact

| User Type | Current Experience | Desired Experience |
|-----------|-------------------|-------------------|
| Technical Writer | Hours of manual reformatting | `bengal build --pdf` |
| Enterprise User | Browser PDF, looks unprofessional | Branded, paginated PDF |
| Author/Publisher | Can't use Bengal for books | EPUB + PDF ready |
| Trainer | Manual slide/handout creation | Print-ready guides |
| Compliance Team | Screenshot-based archives | Proper PDF/A archives |

---

## 2. Goals and Non-Goals

### 2.1 Goals

**Primary Goals** (stellar experience):

1. **🎯 Single command export** — `bengal build --pdf` and `bengal build --epub`
2. **🎯 Directive-aware rendering** — Tabs, dropdowns, cards render appropriately for print
3. **🎯 Professional typography** — Proper page breaks, hyphenation, running headers
4. **🎯 Automatic TOC** — Generated from headings, with page numbers
5. **🎯 Cross-reference preservation** — Internal links become page references

**Secondary Goals** (excellent experience):

6. **Customizable templates** — Users can override PDF/EPUB templates
7. **Multiple output modes** — Full site, single page, section
8. **Cover page support** — Configurable title page with metadata
9. **Print stylesheets in theme** — Theme authors can provide `print.css`
10. **Incremental generation** — Only regenerate changed pages

**Tertiary Goals** (good to have):

11. **PDF/A compliance** — Archival format for long-term storage
12. **Accessibility** — Tagged PDF, EPUB accessibility features
13. **Multiple paper sizes** — A4, Letter, custom
14. **Batch export** — Generate PDF per section or per page

### 2.2 Non-Goals

1. **Real-time preview** — Not building a WYSIWYG editor
2. **Word/DOCX export** — Different problem space (editable vs. final)
3. **Interactive PDFs** — No JavaScript in output
4. **Print-on-demand integration** — No direct Lulu/Amazon publishing
5. **Complex multi-column layouts** — Magazine-style layouts out of scope
6. **Video/audio in PDF** — EPUB supports; PDF will show poster/link

---

## 3. Proposed Design

### 3.0 Architecture Overview

```
                                ┌─────────────────────────────────────┐
                                │           Bengal Build              │
                                └─────────────────────────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
            ┌───────────────┐         ┌───────────────┐         ┌───────────────┐
            │   HTML Output │         │   PDF Output  │         │  EPUB Output  │
            │   (default)   │         │   (optional)  │         │  (optional)   │
            └───────────────┘         └───────────────┘         └───────────────┘
                                              │                         │
                                              ▼                         ▼
                                    ┌─────────────────┐       ┌─────────────────┐
                                    │  Print Renderer │       │  EPUB Packager  │
                                    │  (HTML → PDF)   │       │  (HTML → EPUB)  │
                                    └─────────────────┘       └─────────────────┘
                                              │                         │
                            ┌─────────────────┼─────────────────┐       │
                            ▼                                   ▼       ▼
                    ┌───────────────┐                   ┌───────────────┐
                    │  WeasyPrint   │                   │   Paged.js    │
                    │  (default)    │                   │  (optional)   │
                    └───────────────┘                   └───────────────┘
```

### 3.1 CLI Interface

```bash
# Generate PDF alongside HTML
bengal build --pdf

# Generate EPUB alongside HTML
bengal build --epub

# Generate both
bengal build --pdf --epub

# PDF only, no HTML
bengal build --pdf-only

# Single page/section PDF
bengal build --pdf --scope docs/api/

# Custom output location
bengal build --pdf --pdf-output ./dist/manual.pdf

# Specific paper size
bengal build --pdf --paper-size A4

# Include cover page
bengal build --pdf --cover docs/cover.md
```

### 3.2 Configuration

```yaml
# bengal.yaml
export:
  pdf:
    enabled: true
    engine: weasyprint  # or "paged.js"

    # Output options
    output: public/docs.pdf  # or "per-section" for multiple PDFs
    scope: all  # "all", "docs", "blog", or specific path

    # Page setup
    paper_size: Letter  # A4, Letter, Legal, or custom [width, height]
    orientation: portrait  # portrait, landscape
    margins:
      top: 1in
      bottom: 1in
      left: 1in
      right: 1in

    # Content options
    cover:
      enabled: true
      template: pdf/cover.html  # in theme
      # OR
      page: docs/book-cover.md  # markdown page with frontmatter

    toc:
      enabled: true
      depth: 3  # h1-h3
      title: "Table of Contents"

    # Typography
    typography:
      hyphenation: true
      widows: 2  # minimum lines at page top
      orphans: 2  # minimum lines at page bottom
      font_size: 11pt
      line_height: 1.4

    # Headers and footers
    running_headers:
      odd: "{{ section.title }}"  # Right pages
      even: "{{ site.title }}"     # Left pages
    running_footers:
      center: "{{ page_number }}"

    # Code blocks
    code:
      font_size: 9pt
      line_numbers: true
      max_height: null  # null = no limit; or "6in" to break long blocks
      syntax_highlighting: true

    # Advanced
    pdf_a: false  # PDF/A compliance for archival
    compress: true
    metadata:
      author: "{{ site.author }}"
      subject: "{{ site.description }}"
      keywords: "{{ site.tags | join(', ') }}"

  epub:
    enabled: true
    output: public/docs.epub

    # Metadata
    title: "{{ site.title }}"
    author: "{{ site.author }}"
    language: "{{ site.language | default('en') }}"
    publisher: ""
    isbn: ""

    # Cover
    cover:
      image: assets/cover.jpg  # 1600x2400 recommended
      # OR generate from template
      template: epub/cover.html

    # Structure
    toc:
      depth: 3
      landmarks: true  # EPUB 3 landmarks for accessibility

    # Content
    include_sections:
      - docs
      - tutorials
    exclude_patterns:
      - "**/autodoc/python/**"  # Too dense for e-readers

    # Styling
    stylesheet: epub/styles.css  # in theme
    font_embedding: subset  # "none", "subset", "full"

    # Validation
    validate: true  # Run EPUBCheck after generation
```

### 3.3 Print-Aware Rendering

Bengal directives need special handling for print. The key insight: **print is linear**, while web is interactive.

#### 3.3.1 Directive Transformations

| Directive | Web Behavior | Print Behavior |
|-----------|--------------|----------------|
| `tabs` / `tab-set` | Interactive tabs | Show all tabs sequentially with headers |
| `dropdown` | Collapsed by default | Expanded, with visual separator |
| `code-tabs` | Language switcher | Show primary language only (configurable) |
| `cards` | Grid layout | Linear list with visual separation |
| `steps` | Numbered steps | Same, with page-break-inside: avoid |
| `admonitions` | Styled boxes | Same, with print-friendly styling |
| `video` | Embedded player | Poster image + QR code to video URL |
| `button` | Clickable link | Text with URL in parentheses |

#### 3.3.2 Print CSS Strategy

```css
/* bengal/themes/default/assets/css/print.css */

@media print {
  /* Hide navigation chrome */
  .sidebar, .navbar, .toc-sidebar, .footer {
    display: none !important;
  }

  /* Expand dropdowns */
  details.dropdown {
    display: block !important;
  }
  details.dropdown > summary {
    font-weight: bold;
    border-bottom: 1px solid #ccc;
    margin-bottom: 0.5em;
  }
  details.dropdown[open] > summary::after {
    content: none; /* Remove toggle icon */
  }

  /* Transform tabs to sequential content */
  .tab-set {
    border: none;
  }
  .tab-set .tab-item {
    display: block !important;
    padding: 1em;
    border-left: 3px solid #3b82f6;
    margin-bottom: 1em;
    page-break-inside: avoid;
  }
  .tab-set .tab-item::before {
    content: attr(data-tab-label);
    font-weight: bold;
    display: block;
    margin-bottom: 0.5em;
    color: #1e40af;
  }
  .tab-set .tab-navigation {
    display: none;
  }

  /* Code blocks */
  pre, code {
    font-size: 9pt;
    page-break-inside: avoid;
    overflow-wrap: break-word;
    white-space: pre-wrap;
  }

  /* Links show URL */
  a[href^="http"]::after {
    content: " (" attr(href) ")";
    font-size: 0.8em;
    color: #666;
  }
  a[href^="#"]::after {
    content: " (p. " target-counter(attr(href), page) ")";
  }

  /* Cards become list */
  .cards-grid {
    display: block;
  }
  .cards-grid .card {
    display: block;
    border: 1px solid #e5e7eb;
    padding: 1em;
    margin-bottom: 1em;
    page-break-inside: avoid;
  }

  /* Video to QR code */
  .video-embed {
    page-break-inside: avoid;
  }
  .video-embed iframe {
    display: none;
  }
  .video-embed .print-fallback {
    display: block !important;
  }
}
```

#### 3.3.3 CSS Paged Media for PDF

```css
/* bengal/themes/default/assets/css/paged.css */

@page {
  size: Letter;
  margin: 1in;

  /* Running headers */
  @top-center {
    content: string(chapter-title);
    font-size: 10pt;
    color: #666;
  }

  /* Page numbers */
  @bottom-center {
    content: counter(page);
  }

  /* First page of chapter */
  @top-center:first {
    content: none;
  }
}

/* Chapter titles set the running header */
h1 {
  string-set: chapter-title content();
  page-break-before: always;
  page-break-after: avoid;
}

h2, h3, h4 {
  page-break-after: avoid;
}

/* Keep code and figures together */
pre, figure, table {
  page-break-inside: avoid;
}

/* Avoid widows and orphans */
p {
  widows: 2;
  orphans: 2;
}

/* Table of contents */
.toc a::after {
  content: leader('.') target-counter(attr(href), page);
}

/* Footnotes */
.footnote {
  float: footnote;
  footnote-display: block;
}

/* Cross-references with page numbers */
a.internal-ref::after {
  content: " (page " target-counter(attr(href), page) ")";
}
```

### 3.4 Table of Contents Generation

Automatic TOC from document structure:

```python
# bengal/export/toc.py

@dataclass
class TOCEntry:
    """Table of contents entry."""
    title: str
    level: int  # 1=h1, 2=h2, etc.
    anchor: str
    page: Page
    children: list[TOCEntry] = field(default_factory=list)

class TOCGenerator:
    """Generate table of contents from page structure."""

    def __init__(self, depth: int = 3):
        self.depth = depth

    def generate(self, pages: list[Page], order: list[str]) -> list[TOCEntry]:
        """
        Generate TOC entries from pages.

        Args:
            pages: All pages to include
            order: Page order (from menu or nav config)

        Returns:
            Hierarchical TOC structure
        """
        entries = []

        for page in self._ordered_pages(pages, order):
            # Top-level entry for the page
            entry = TOCEntry(
                title=page.title,
                level=1,
                anchor=f"#{page.slug}",
                page=page,
            )

            # Add heading entries from page content
            if self.depth > 1:
                entry.children = self._extract_headings(page)

            entries.append(entry)

        return entries

    def _extract_headings(self, page: Page) -> list[TOCEntry]:
        """Extract h2-hN headings from page AST."""
        headings = []
        for node in page.ast:
            if node["type"] == "heading":
                level = node["attrs"]["level"]
                if 2 <= level <= self.depth:
                    headings.append(TOCEntry(
                        title=node["children"][0]["raw"],
                        level=level,
                        anchor=f"#{page.slug}#{node['attrs']['id']}",
                        page=page,
                    ))
        return self._nest_headings(headings)

    def _nest_headings(self, flat: list[TOCEntry]) -> list[TOCEntry]:
        """Convert flat heading list to nested structure."""
        # ... nesting logic ...
        pass
```

**Rendered TOC:**

```html
<!-- PDF TOC page -->
<nav class="toc" role="doc-toc">
  <h1>Table of Contents</h1>
  <ol>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ol>
        <li><a href="#getting-started#installation">Installation</a></li>
        <li><a href="#getting-started#configuration">Configuration</a></li>
      </ol>
    </li>
    <li>
      <a href="#core-concepts">Core Concepts</a>
      <ol>
        <li><a href="#core-concepts#pages">Pages</a></li>
        <li><a href="#core-concepts#sections">Sections</a></li>
      </ol>
    </li>
  </ol>
</nav>
```

### 3.5 PDF Generation Engine: WeasyPrint

WeasyPrint is chosen as the default engine for its:
- Pure Python implementation (no external dependencies)
- Excellent CSS Paged Media support
- Active maintenance
- Permissive license (BSD)

```python
# bengal/export/pdf/weasyprint_engine.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.export.config import PDFConfig

@dataclass
class PDFEngine:
    """WeasyPrint-based PDF generation engine."""

    config: PDFConfig
    font_config: FontConfiguration = None

    def __post_init__(self):
        self.font_config = FontConfiguration()

    def generate(
        self,
        html_content: str,
        output_path: Path,
        base_url: str,
        stylesheets: list[Path],
    ) -> Path:
        """
        Generate PDF from HTML content.

        Args:
            html_content: Combined HTML document
            output_path: Where to write PDF
            base_url: Base URL for resolving relative paths
            stylesheets: CSS files to apply

        Returns:
            Path to generated PDF
        """
        # Load stylesheets
        css_list = [
            CSS(filename=str(css), font_config=self.font_config)
            for css in stylesheets
        ]

        # Add print and paged CSS
        css_list.extend([
            CSS(string=self._paged_css()),
            CSS(string=self._custom_css()),
        ])

        # Generate PDF
        html = HTML(
            string=html_content,
            base_url=base_url,
        )

        html.write_pdf(
            target=str(output_path),
            stylesheets=css_list,
            font_config=self.font_config,
            optimize_images=True,
            jpeg_quality=85,
            dpi=150,
        )

        return output_path

    def _paged_css(self) -> str:
        """Generate @page rules from config."""
        return f"""
        @page {{
            size: {self.config.paper_size} {self.config.orientation};
            margin: {self.config.margins.top} {self.config.margins.right}
                    {self.config.margins.bottom} {self.config.margins.left};

            @top-center {{
                content: string(section-title);
                font-size: 9pt;
                color: #666;
            }}

            @bottom-center {{
                content: counter(page);
                font-size: 9pt;
            }}
        }}

        @page :first {{
            @top-center {{ content: none; }}
            @bottom-center {{ content: none; }}
        }}

        h1 {{
            string-set: section-title content();
            page-break-before: always;
        }}

        h1:first-of-type {{
            page-break-before: avoid;
        }}
        """

    def _custom_css(self) -> str:
        """Additional CSS from config."""
        css = ""

        if self.config.typography.hyphenation:
            css += """
            p, li {
                hyphens: auto;
                -webkit-hyphens: auto;
            }
            """

        css += f"""
        p {{
            widows: {self.config.typography.widows};
            orphans: {self.config.typography.orphans};
        }}

        body {{
            font-size: {self.config.typography.font_size};
            line-height: {self.config.typography.line_height};
        }}

        pre, code {{
            font-size: {self.config.code.font_size};
        }}
        """

        return css
```

### 3.6 EPUB Generation

EPUB 3.3 compliant generation using Python's `zipfile` and XML libraries:

```python
# bengal/export/epub/generator.py

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.export.config import EPUBConfig

@dataclass
class EPUBGenerator:
    """Generate EPUB 3.3 compliant e-books."""

    config: EPUBConfig

    def generate(
        self,
        pages: list[Page],
        output_path: Path,
        assets: list[Asset],
    ) -> Path:
        """
        Generate EPUB from pages and assets.

        EPUB structure:
        ├── mimetype
        ├── META-INF/
        │   └── container.xml
        └── OEBPS/
            ├── content.opf       (package document)
            ├── toc.xhtml         (navigation)
            ├── toc.ncx           (EPUB 2 compat)
            ├── content/          (XHTML content)
            │   ├── chapter-1.xhtml
            │   └── chapter-2.xhtml
            ├── css/
            │   └── styles.css
            └── images/
                └── ...

        Args:
            pages: Pages to include
            output_path: Where to write EPUB
            assets: Images, CSS to include

        Returns:
            Path to generated EPUB
        """
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as epub:
            # mimetype must be first and uncompressed
            epub.writestr('mimetype', 'application/epub+zip',
                         compress_type=zipfile.ZIP_STORED)

            # Container
            epub.writestr('META-INF/container.xml', self._container_xml())

            # Package document
            epub.writestr('OEBPS/content.opf',
                         self._package_document(pages, assets))

            # Navigation
            epub.writestr('OEBPS/toc.xhtml', self._nav_document(pages))
            epub.writestr('OEBPS/toc.ncx', self._ncx_document(pages))

            # Content
            for page in pages:
                xhtml = self._page_to_xhtml(page)
                epub.writestr(f'OEBPS/content/{page.slug}.xhtml', xhtml)

            # Stylesheets
            epub.writestr('OEBPS/css/styles.css', self._stylesheet())

            # Assets (images)
            for asset in assets:
                epub.write(asset.source_path, f'OEBPS/images/{asset.filename}')

            # Cover image if configured
            if self.config.cover.image:
                epub.write(self.config.cover.image, 'OEBPS/images/cover.jpg')

        # Validate if configured
        if self.config.validate:
            self._validate(output_path)

        return output_path

    def _package_document(self, pages: list[Page], assets: list[Asset]) -> str:
        """Generate content.opf package document."""
        # EPUB 3.3 compliant package document
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="uid">{self.config.identifier}</dc:identifier>
    <dc:title>{self.config.title}</dc:title>
    <dc:language>{self.config.language}</dc:language>
    <dc:creator>{self.config.author}</dc:creator>
    <meta property="dcterms:modified">{self._timestamp()}</meta>
  </metadata>

  <manifest>
    <item id="nav" href="toc.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="css" href="css/styles.css" media-type="text/css"/>
    {self._manifest_items(pages, assets)}
  </manifest>

  <spine toc="ncx">
    {self._spine_items(pages)}
  </spine>
</package>"""

    def _page_to_xhtml(self, page: Page) -> str:
        """Convert page HTML to valid XHTML for EPUB."""
        # Transform Bengal HTML to EPUB-compatible XHTML
        # - Close all tags
        # - Namespace declarations
        # - Remove unsupported elements (iframes, scripts)
        # - Convert videos to images with links
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <title>{page.title}</title>
  <link rel="stylesheet" type="text/css" href="../css/styles.css"/>
</head>
<body epub:type="bodymatter">
  <section epub:type="chapter" aria-labelledby="{page.slug}-title">
    <h1 id="{page.slug}-title">{page.title}</h1>
    {self._transform_content(page.rendered_html)}
  </section>
</body>
</html>"""

    def _transform_content(self, html: str) -> str:
        """Transform HTML content for EPUB compatibility."""
        # Transform Bengal-specific elements
        transformations = [
            # Tabs: show all panels
            (r'<div class="tab-set".*?</div>', self._transform_tabs),
            # Dropdowns: expand
            (r'<details.*?</details>', self._transform_dropdown),
            # Videos: poster + link
            (r'<iframe.*?youtube.*?</iframe>', self._transform_video),
            # Remove scripts
            (r'<script.*?</script>', ''),
        ]

        for pattern, replacement in transformations:
            html = re.sub(pattern, replacement, html, flags=re.DOTALL)

        return html

    def _validate(self, epub_path: Path) -> None:
        """Run EPUBCheck validation."""
        try:
            import subprocess
            result = subprocess.run(
                ['epubcheck', str(epub_path)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logger.warning(
                    "epub_validation_warnings",
                    output=result.stderr,
                )
        except FileNotFoundError:
            logger.debug("epubcheck_not_installed")
```

### 3.7 Integration with Build Pipeline

```python
# bengal/export/__init__.py

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.export.pdf import PDFExporter
from bengal.export.epub import EPUBExporter
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.build_context import BuildContext

logger = get_logger(__name__)


def export_pdf(
    site: Site,
    context: BuildContext,
    output_path: Path | None = None,
) -> Path:
    """
    Export site to PDF.

    Called from build pipeline when --pdf flag is set.

    Args:
        site: Built site with rendered pages
        context: Build context with config
        output_path: Override output location

    Returns:
        Path to generated PDF
    """
    config = site.config.get("export", {}).get("pdf", {})
    exporter = PDFExporter(config, site)

    # Determine pages to include
    scope = config.get("scope", "all")
    pages = _filter_pages_by_scope(site.pages, scope)

    # Order pages for PDF
    ordered_pages = _order_pages_for_export(pages, site.menu)

    # Generate combined HTML document
    combined_html = exporter.combine_pages(ordered_pages)

    # Generate PDF
    output = output_path or Path(config.get("output", "public/docs.pdf"))
    pdf_path = exporter.generate(combined_html, output)

    logger.info(
        "pdf_generated",
        path=str(pdf_path),
        pages=len(ordered_pages),
        size_mb=pdf_path.stat().st_size / 1024 / 1024,
    )

    return pdf_path


def export_epub(
    site: Site,
    context: BuildContext,
    output_path: Path | None = None,
) -> Path:
    """
    Export site to EPUB.

    Called from build pipeline when --epub flag is set.
    """
    config = site.config.get("export", {}).get("epub", {})
    exporter = EPUBExporter(config, site)

    # Similar to PDF but with EPUB-specific handling
    pages = _filter_pages_by_scope(site.pages, config.get("scope", "all"))
    ordered_pages = _order_pages_for_export(pages, site.menu)

    # Collect required assets
    assets = _collect_assets_for_epub(ordered_pages, site)

    output = output_path or Path(config.get("output", "public/docs.epub"))
    epub_path = exporter.generate(ordered_pages, assets, output)

    logger.info(
        "epub_generated",
        path=str(epub_path),
        pages=len(ordered_pages),
        size_mb=epub_path.stat().st_size / 1024 / 1024,
    )

    return epub_path
```

---

## 4. Design Alternatives Considered

### 4.1 Alternative A: Headless Browser (Chrome/Puppeteer)

**Approach**: Use headless Chrome to "print to PDF"

```bash
# Conceptually
chrome --headless --print-to-pdf=output.pdf https://docs.site.com
```

**Pros**:
- Perfect CSS fidelity (same engine as browser)
- JavaScript execution (interactive diagrams)
- Easy implementation

**Cons**:
- **Massive dependency** — Chrome is 100MB+
- **Poor paged media** — No proper page breaks, no running headers
- **Security concerns** — Arbitrary JS execution
- **Slow** — ~5-10s per page
- **Resource intensive** — Memory-hungry

**Verdict**: ❌ Rejected — Too heavyweight, poor print support

### 4.2 Alternative B: Pandoc Pipeline

**Approach**: Convert Markdown → Pandoc AST → LaTeX → PDF

```bash
# Conceptually
bengal render-markdown | pandoc -o output.pdf
```

**Pros**:
- Excellent typography (LaTeX backend)
- Good PDF/A support
- Mature tooling

**Cons**:
- **Loses Bengal semantics** — Directives become raw HTML
- **LaTeX dependency** — Another large installation
- **Styling disconnect** — CSS doesn't apply; need LaTeX templates
- **Two rendering paths** — Must maintain Pandoc templates separately

**Verdict**: ❌ Rejected — Semantic loss, maintenance burden

### 4.3 Alternative C: Paged.js Only

**Approach**: Client-side PDF generation using Paged.js

```html
<script src="paged.js"></script>
<script>
  window.PagedPolyfill.preview(); // Renders to PDF
</script>
```

**Pros**:
- Best CSS Paged Media support
- Runs in browser (no Python deps)
- Great print preview

**Cons**:
- **Requires browser** — Need Puppeteer/Playwright to automate
- **Slower** — Full browser rendering
- **Complex setup** — JS bundling, server needed

**Verdict**: ⚠️ Optional — Offer as high-fidelity option, not default

### 4.4 Alternative D: ReportLab Direct

**Approach**: Generate PDF programmatically without HTML intermediate

```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

c = canvas.Canvas("output.pdf", pagesize=letter)
c.drawString(100, 750, "Hello World")
c.save()
```

**Pros**:
- Pure Python, fast
- Full control over layout
- No HTML conversion

**Cons**:
- **No HTML/CSS reuse** — Must rebuild all rendering
- **Complex for rich content** — Tables, code blocks, images
- **No style sharing** — Completely separate from web output

**Verdict**: ❌ Rejected — Too much reimplementation

### 4.5 Recommended: WeasyPrint + Optional Paged.js

**Approach**: WeasyPrint as default (simple), Paged.js as option (high-fidelity)

| Feature | WeasyPrint | Paged.js |
|---------|------------|----------|
| Dependencies | Pure Python | Browser + JS |
| Speed | Fast (~1s/page) | Slow (~5s/page) |
| CSS Paged Media | Good | Excellent |
| Running headers | ✅ | ✅ |
| Footnotes | ✅ | ✅ |
| Cross-references | Limited | ✅ |
| Complex layouts | Good | Excellent |
| Print preview | ❌ | ✅ (browser) |

**Verdict**: ✅ Recommended

---

## 5. Implementation Phases

### Phase 1: Foundation (Week 1-2)

```
├── bengal/export/
│   ├── __init__.py           # Public API
│   ├── config.py             # PDFConfig, EPUBConfig dataclasses
│   ├── toc.py                # TOC generation
│   └── utils.py              # Shared utilities
├── CLI integration
│   └── bengal build --pdf --epub flags
└── Basic tests
```

**Deliverables**:
- [ ] Export config schema
- [ ] CLI flags added to `build` command
- [ ] Basic print.css in default theme
- [ ] TOC generator from page structure

### Phase 2: PDF Core (Week 2-4)

```
├── bengal/export/pdf/
│   ├── __init__.py
│   ├── weasyprint_engine.py  # WeasyPrint integration
│   ├── page_combiner.py      # Combine pages to single doc
│   ├── directive_transforms.py  # Print-specific transforms
│   └── cover.py              # Cover page generation
└── CSS Paged Media
    ├── paged.css             # @page rules
    └── print.css             # Print-specific styles
```

**Deliverables**:
- [ ] WeasyPrint engine working
- [ ] Directive transforms (tabs, dropdowns, cards)
- [ ] Running headers/footers
- [ ] Page numbers
- [ ] Basic cover page

### Phase 3: PDF Polish (Week 4-5)

**Deliverables**:
- [ ] TOC with page numbers
- [ ] Cross-reference page numbers
- [ ] Code block line wrapping
- [ ] Image optimization
- [ ] Multiple paper sizes
- [ ] PDF metadata

### Phase 4: EPUB Core (Week 5-7)

```
├── bengal/export/epub/
│   ├── __init__.py
│   ├── generator.py          # EPUB assembly
│   ├── packager.py           # OPF, NCX generation
│   ├── xhtml_transformer.py  # HTML → XHTML
│   └── validator.py          # EPUBCheck integration
└── EPUB assets
    ├── epub.css              # E-reader styles
    └── cover template
```

**Deliverables**:
- [ ] EPUB 3.3 structure generation
- [ ] Content.opf generation
- [ ] XHTML transformation
- [ ] Navigation document
- [ ] CSS embedding
- [ ] Image handling

### Phase 5: EPUB Polish (Week 7-8)

**Deliverables**:
- [ ] EPUBCheck validation
- [ ] Cover generation
- [ ] Font subsetting (optional)
- [ ] Accessibility features
- [ ] Multiple EPUB output (per-section)

### Phase 6: Advanced Features (Week 8-10)

**Deliverables**:
- [ ] Paged.js engine option
- [ ] PDF/A compliance
- [ ] Incremental generation
- [ ] Per-section PDFs
- [ ] Theme template overrides

---

## 6. Architecture Impact

### 6.1 New Modules

```
bengal/export/
├── __init__.py               # export_pdf(), export_epub()
├── config.py                 # Dataclass configs
├── toc.py                    # TOC generation
├── pdf/
│   ├── __init__.py
│   ├── weasyprint_engine.py
│   ├── pagedjs_engine.py     # Optional
│   ├── page_combiner.py
│   ├── cover.py
│   └── transforms.py
└── epub/
    ├── __init__.py
    ├── generator.py
    ├── packager.py
    └── validator.py
```

### 6.2 Dependencies

```toml
# pyproject.toml additions

[project.optional-dependencies]
pdf = ["weasyprint>=60.0"]
epub = []  # No extra deps, uses stdlib
pdf-hifi = ["weasyprint>=60.0"]  # Future: Paged.js via Playwright

# Note: WeasyPrint requires system libraries:
# - cairo, pango, gdk-pixbuf (usually pre-installed)
# - Fonts for proper typography
```

### 6.3 Theme Integration

```
themes/default/
├── assets/
│   └── css/
│       ├── print.css         # @media print styles
│       └── paged.css         # @page rules for PDF
├── templates/
│   └── export/
│       ├── pdf-cover.html    # Cover page template
│       ├── pdf-toc.html      # TOC template
│       └── epub-cover.html   # EPUB cover template
```

---

## 7. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| WeasyPrint system dependencies | MEDIUM | HIGH | Document requirements; provide Docker image |
| Complex directive transforms | MEDIUM | MEDIUM | Progressive enhancement; degrade gracefully |
| Large PDFs slow to generate | LOW | MEDIUM | Incremental builds; progress indicators |
| EPUB validation failures | LOW | LOW | EPUBCheck in CI; warning on validation issues |
| Font rendering differences | MEDIUM | LOW | Embed fonts; test on multiple platforms |
| Print CSS conflicts with web | LOW | MEDIUM | Isolated print.css; thorough testing |

---

## 8. Success Criteria

### 8.1 Quantitative

- [ ] `bengal build --pdf` generates valid PDF in <30s for 100 pages
- [ ] `bengal build --epub` generates valid EPUB 3.3
- [ ] All 30+ directives render appropriately in print
- [ ] TOC accurate with page numbers
- [ ] Cross-references show page numbers

### 8.2 Qualitative

- [ ] **Professional appearance** — Output looks like commercial documentation
- [ ] **Single source** — No separate PDF/EPUB source needed
- [ ] **Zero configuration** — Works OOTB with default theme
- [ ] **Customizable** — Power users can override templates/CSS
- [ ] **Accessible** — Tagged PDF, EPUB landmarks

---

## 9. Open Questions

1. **Should PDF include interactive links?**
   - Pro: Useful for digital PDFs
   - Con: Broken in print; looks unprofessional

2. **How to handle versioned docs in PDF?**
   - Generate per-version PDFs?
   - Single PDF with version sections?

3. **Should code-tabs show all languages or just one?**
   - Config option?
   - Primary language only?

4. **Cover page: template or image?**
   - HTML template (flexible)
   - Image upload (simpler)
   - Both?

5. **Font embedding strategy?**
   - Full embedding (large files)
   - Subset embedding (smaller, complex)
   - System fonts only (smallest, inconsistent)

6. **Multi-file vs single-file EPUB?**
   - One XHTML per page (standard)
   - One XHTML per section (larger chapters)
   - Single XHTML (simple but limited)

---

## 10. References

- [WeasyPrint Documentation](https://doc.courtbouillon.org/weasyprint/stable/)
- [CSS Paged Media Module Level 3](https://www.w3.org/TR/css-page-3/)
- [EPUB 3.3 Specification](https://www.w3.org/TR/epub-33/)
- [Paged.js Documentation](https://pagedjs.org/documentation/)
- [EPUBCheck](https://github.com/w3c/epubcheck)
- [PDF/A Specification](https://www.pdfa.org/pdfa-specification/)

---

## Appendix A: Print CSS Quick Reference

```css
/* Essential @page rules */
@page {
  size: Letter;
  margin: 1in;
}

@page :first { margin-top: 2in; }
@page :left { margin-left: 1.5in; }
@page :right { margin-right: 1.5in; }

/* Running elements */
@page {
  @top-center { content: string(title); }
  @bottom-center { content: counter(page); }
}

/* Page breaks */
h1 { page-break-before: always; }
h2, h3 { page-break-after: avoid; }
table, figure { page-break-inside: avoid; }

/* Widows/orphans */
p { widows: 2; orphans: 2; }

/* Cross-references */
a::after { content: " (p. " target-counter(attr(href), page) ")"; }

/* Footnotes */
.footnote { float: footnote; }

/* TOC leaders */
.toc a::after { content: leader('.') target-counter(attr(href), page); }
```

---

## Appendix B: EPUB Structure Reference

```
my-book.epub (ZIP archive)
├── mimetype                    # Must be first, uncompressed
│   └── "application/epub+zip"
├── META-INF/
│   └── container.xml           # Points to content.opf
└── OEBPS/
    ├── content.opf             # Package document (manifest, spine)
    ├── toc.xhtml               # EPUB 3 navigation
    ├── toc.ncx                 # EPUB 2 navigation (compatibility)
    ├── content/
    │   ├── cover.xhtml
    │   ├── chapter-01.xhtml
    │   ├── chapter-02.xhtml
    │   └── ...
    ├── css/
    │   └── styles.css
    └── images/
        ├── cover.jpg
        └── ...
```

---

## Appendix C: Example Output

### PDF Example (conceptual)

```
┌─────────────────────────────────────────────┐
│                                             │
│              BENGAL DOCUMENTATION           │
│                   v1.0.0                    │
│                                             │
│              [Cover Image]                  │
│                                             │
│                                             │
│              Generated: Dec 2025            │
│                                             │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Table of Contents                           │
│─────────────────────────────────────────────│
│ 1. Getting Started ...................... 3 │
│    1.1 Installation ..................... 4 │
│    1.2 Configuration .................... 7 │
│ 2. Core Concepts ....................... 12 │
│    2.1 Pages ........................... 13 │
│    2.2 Sections ........................ 18 │
│ 3. Directives .......................... 25 │
│                                             │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Getting Started                 Bengal Docs │
│─────────────────────────────────────────────│
│                                             │
│ # Getting Started                           │
│                                             │
│ Welcome to Bengal! This guide will help     │
│ you build your first documentation site.    │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ 💡 Tip                                  │ │
│ │                                         │ │
│ │ Bengal works best with Python 3.14+    │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ ## Installation                             │
│                                             │
│ ┌─ Python ────────────────────────────────┐ │
│ │ pip install bengal                      │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ ┌─ macOS (Homebrew) ──────────────────────┐ │
│ │ brew install bengal                     │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│─────────────────────────────────────────────│
│                      3                      │
└─────────────────────────────────────────────┘
```

---

**End of RFC**
