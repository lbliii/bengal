---
title: Glossary
description: Definitions of terms used throughout Bengal documentation
weight: 30
tags:
- reference
- glossary
- terminology
---

# Glossary

Quick reference for terms used in Bengal documentation. Terms are listed alphabetically.

---

## A

**Asset**
: A static file (CSS, JS, image, font) that Bengal processes, optimizes, and optionally fingerprints. Assets live in `assets/` at the project root or alongside content in page bundles.

**Asset Fingerprinting**
: Adding a content-based hash to filenames (e.g., `style.a1b2c3.css`) for cache-busting. When file content changes, the hash changes, forcing browsers to fetch the new version. Enabled by default.

**Autodoc**
: Bengal's automatic documentation generator. Extracts docstrings and signatures from Python source code (via AST parsing), CLI applications (Click, Typer, argparse), and OpenAPI specifications to generate API reference pages as virtual pages during the build.

---

## B

**Base Template**
: The root template (`base.html`) that defines the HTML structure inherited by all other templates. Contains `{% block %}` placeholders that child templates override.

**Build Cache**
: Stored state from previous builds that enables incremental rebuilding. Located in `.bengal/cache/` by default.

**Build Profile**
: A configuration preset (`writer`, `theme-dev`, `dev`) that adjusts output verbosity, validation strictness, and enabled features. Set via `--profile` flag or `bengal project profile`.

**Bundle (Page Bundle)**
: A folder containing a page's Markdown file alongside its dedicated assets (images, data files). Keeps related files together and enables relative asset references.

---

## C

**Cascade**
: Front matter values that flow down from section `_index.md` files to child pages. Used for section-wide defaults like `author`, `type`, or `draft` status.

**Content Directory**
: The folder containing your Markdown source files. Defaults to `content/` but configurable via `[build] content_dir`.

**Content Type**
: The template category used to render a page (e.g., `post`, `doc`, `page`). Set via `type:` in front matter. Maps to templates in `templates/<type>/`.

---

## D

**Directive**
: A MyST Markdown extension that adds special functionality. Written as `:::{directive-name}` blocks. Examples: `note`, `warning`, `tab-set`, `dropdown`.

**Draft**
: A page with `draft: true` in front matter. Excluded from production builds by default. Drafts are visible in development mode (`bengal serve`).

---

## F

**Fast Mode**
: Build configuration that enables parallel processing and reduces output verbosity. Enable via `bengal build --fast` or `fast_mode = true` in config.

**Front Matter**
: YAML or TOML metadata at the top of a Markdown file, delimited by `---`. Controls page properties like title, date, tags, layout, and custom fields.

**Free-Threaded Python**
: Python 3.14+ builds with the GIL disabled (`PYTHON_GIL=0`). Per PEP 703, this enables true parallel execution in `ThreadPoolExecutor`, providing 1.5–2x faster builds. Bengal auto-detects free-threaded Python and logs when true parallelism is active.

---

## G

**GIL (Global Interpreter Lock)**
: Python's mechanism that allows only one thread to execute at a time. Disabling it (`PYTHON_GIL=0`) in Python 3.14+ enables true parallelism.

---

## H

**Health Check**
: Automated validation that detects issues like broken links, missing images, invalid front matter, or orphaned pages. Run via `bengal validate` or `bengal health linkcheck`.

---

## I

**Incremental Build**
: Building only files that changed since the last build, rather than regenerating the entire site. Bengal's incremental rebuilds complete in 35–80 ms for single-page changes. Tracks dependencies so template changes also trigger appropriate rebuilds.

**Index File**
: Special Markdown files that define sections or pages:
  - `_index.md` creates a **section** (a folder that contains child pages)
  - `index.md` creates a **leaf page** with its own URL folder

---

## J

**Jinja2**
: A Python templating engine. Bengal supports Jinja2 as an alternative engine (set `template_engine: jinja2`), but defaults to [[ext:kida:docs/get-started|Kida]] for better performance and modern syntax.

---

## K

**Kida**
: Bengal's default template engine. A high-performance alternative to Jinja2 with unified block endings (`{% end %}`), pattern matching, pipeline operators (`|>`), and automatic caching. Designed for Python 3.14t free-threading. See [[ext:kida:docs/get-started|Kida documentation]] for details.

---

## L

**Layout**
: A template that defines HTML structure for a specific content type. Written in [[ext:kida:|Kida]] (or Jinja2). Lives in `templates/` (project) or in the active theme.

**Live Reload**
: Automatic browser refresh when source files change during development. Enabled by default with `bengal serve`.

---

## M

**Menu**
: Navigation structure defined in configuration via `[[menu.main]]` entries (in `bengal.toml`) or `menu.main` sections (in `bengal.yaml` or directory-based config). Accessible in templates via `site.menus.main`. Supports nested hierarchies and weights.

**MyST Markdown**
: Markedly Structured Text—an extended Markdown syntax that adds directives, roles, and cross-references. Used by Bengal for admonitions, tabs, and other rich content.

---

## O

**Output Directory**
: The folder where Bengal writes generated HTML, CSS, and assets. Defaults to `public/` but configurable via `[build] output_dir`.

**Output Format**
: Alternative renderings of content beyond HTML. Bengal supports JSON, RSS, sitemap, and LLM-optimized text formats.

---

## P

**Page**
: A single piece of content, typically a Markdown file. Rendered to HTML using templates. Has properties like title, URL, date, tags, and content.

---

## R

**Rosettes**
: Bengal's syntax highlighting engine. A modern, thread-safe highlighter designed for Python 3.14t free-threading with 55+ supported languages. Provides semantic CSS classes and configurable themes. See [[ext:rosettes:docs/get-started|Rosettes documentation]] for details.

**Partial**
: A reusable template fragment (e.g., `header.html`, `footer.html`, `sidebar.html`). Included in other templates via `{% include "partials/name.html" %}`.

**Post-Processing**
: Operations performed after rendering, such as HTML minification, sitemap generation, and RSS feed creation.

---

## S

**Section**
: A content folder with an `_index.md` file. Represents a group of related pages (e.g., `content/blog/`, `content/docs/`). Has its own landing page and can contain child pages or nested sections.

**Shortcode**
: A reusable content component invoked within Markdown. Bengal uses MyST directive syntax (`:::{shortcode}`) for shortcodes.

**Site**
: The top-level container representing your entire Bengal project. Provides access to all pages, sections, menus, and configuration in templates via the `site` variable.

---

## T

**Taxonomy**
: A classification system for organizing content. Common taxonomies include tags, categories, and authors. Each taxonomy term gets its own listing page.

**Template**
: A [[ext:kida:|Kida]] file that defines how content is rendered to HTML. Templates use [[ext:kida:docs/syntax/inheritance|inheritance]] (extending base templates) and composition (including partials).

**Template Engine**
: Bengal's system for rendering templates. Defaults to [[ext:kida:docs/get-started|Kida]] (high-performance with modern syntax) but also supports Jinja2. Provides built-in filters, functions, and the `site`/`page`/`section` context variables.

**Theme**
: A package of templates, assets, and styles that defines site appearance. Themes can be:
  - **Bundled**: Included with Bengal (e.g., `default`)
  - **Installed**: Via pip/uv (e.g., `bengal-theme-starter`)
  - **Project**: Local in your `themes/` directory

---

## W

**Weight**
: A numeric value controlling sort order in menus and page listings. Lower weight appears first. Set via `weight:` in front matter or menu config.

---

:::{seealso}
- [[docs/about/concepts|Core Concepts]] — Detailed explanations of how Bengal works
- [[docs/reference/architecture/tooling/config|Configuration Reference]] — All configuration options
- [[docs/about/faq|FAQ]] — Answers to common questions
:::
