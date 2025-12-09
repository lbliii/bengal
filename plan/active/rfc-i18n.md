# RFC: Built-in Internationalization (i18n)

**Status**: Draft  
**Created**: 2025-12-08  
**Author**: AI Assistant  
**Confidence**: 70% 🟡

---

## Executive Summary

Add first-class internationalization support to Bengal with minimal configuration. Define languages in config, use locale suffixes on files (`guide.es.md`), and Bengal handles language switching, `hreflang` tags, fallback to default language, and translation coverage reports.

---

## Problem Statement

### Current State

Bengal has no built-in i18n support. Users must:
1. Create parallel directory structures per language
2. Manually build language switchers
3. Handle `hreflang` tags themselves
4. Track translation coverage manually
5. Hope the URL structure is SEO-friendly

**Evidence**:
- No i18n modules in codebase
- No language configuration in site config schema

### Pain Points

1. **Complex setup**: Every team reinvents the wheel
2. **SEO mistakes**: Missing `hreflang`, wrong canonicals
3. **Inconsistent URLs**: `/en/docs/` vs `/docs/en/` vs subdomains
4. **No coverage visibility**: Which pages are translated?
5. **Fallback complexity**: What to show when translation missing?

### User Impact

International users get broken experiences. Documentation teams avoid i18n because it's too hard. English-only docs limit product adoption.

---

## Goals & Non-Goals

**Goals**:
- Simple configuration: list languages in `bengal.toml`
- Flexible content structure: locale suffix OR folder-based
- Automatic SEO: `hreflang`, canonical URLs, sitemaps
- Language switcher data for themes
- Translation coverage reports
- Fallback to default language

**Non-Goals**:
- Translation management (use Crowdin, Lokalise, etc.)
- Machine translation (use external tools)
- RTL layout support (separate RFC, CSS concern)
- Multi-region (same language, different regions)

---

## Architecture Impact

**Affected Subsystems**:
- **Core** (`bengal/core/`): Page locale awareness
- **Discovery** (`bengal/discovery/`): Locale-aware content discovery
- **Rendering** (`bengal/rendering/`): Language context in templates
- **Postprocess** (`bengal/postprocess/`): Sitemap with alternates
- **Health** (`bengal/health/`): Translation coverage checks

**New Components**:
- `bengal/i18n/` - Internationalization system
- `bengal/i18n/locale.py` - Locale handling
- `bengal/i18n/resolver.py` - Content resolution by locale
- `bengal/i18n/coverage.py` - Translation coverage analysis

---

## Content Structure Options

### Option A: Locale Suffix (Recommended for Most)

```
content/
├─ docs/
│   ├─ guide.md           # English (default)
│   ├─ guide.es.md        # Spanish
│   ├─ guide.ja.md        # Japanese
│   ├─ tutorial.md        # English only (no translations)
│   └─ advanced/
│       ├─ plugins.md
│       ├─ plugins.es.md
│       └─ plugins.ja.md
```

**Pros**:
- Translations live next to originals
- Easy to see what's translated
- Simple file operations

**Cons**:
- Many files in one directory
- Can get cluttered

---

### Option B: Locale Folders

```
content/
├─ en/                    # English (default)
│   └─ docs/
│       ├─ guide.md
│       └─ advanced/
│           └─ plugins.md
├─ es/                    # Spanish
│   └─ docs/
│       ├─ guide.md
│       └─ advanced/
│           └─ plugins.md
└─ ja/                    # Japanese
    └─ docs/
        └─ guide.md       # Only guide translated
```

**Pros**:
- Clean separation
- Familiar to Docusaurus users
- Easy to have different structures per locale

**Cons**:
- Duplication of directory structure
- Harder to see translation gaps

---

### Option C: Hybrid (Support Both)

```toml
# bengal.toml
[i18n]
mode = "suffix"  # or "folder" or "auto"
```

With `auto`, Bengal detects which pattern is used.

---

## Proposed Configuration

```toml
# bengal.toml
[i18n]
# Enable internationalization
enabled = true

# Default language
default_locale = "en"

# Available languages
locales = [
    { code = "en", name = "English", default = true },
    { code = "es", name = "Español" },
    { code = "ja", name = "日本語" },
    { code = "de", name = "Deutsch" },
]

# Content organization
mode = "suffix"  # "suffix" (.es.md) or "folder" (/es/)

# URL structure
url_strategy = "prefix"  # "prefix" (/es/docs/) or "subdomain" (es.example.com)

# Fallback behavior
fallback_to_default = true

# Hide default locale from URLs
hide_default_locale = true  # /docs/ instead of /en/docs/

# Sitemap configuration
[i18n.sitemap]
include_alternates = true
default_priority = 0.8
```

---

## URL Strategies

### Prefix Strategy (Recommended)

```
https://example.com/docs/guide/          # English (default, no prefix)
https://example.com/es/docs/guide/       # Spanish
https://example.com/ja/docs/guide/       # Japanese
```

### Subdomain Strategy

```
https://example.com/docs/guide/          # English
https://es.example.com/docs/guide/       # Spanish
https://ja.example.com/docs/guide/       # Japanese
```

### Generated HTML

```html
<!-- On English page -->
<html lang="en">
<head>
    <link rel="canonical" href="https://example.com/docs/guide/">
    <link rel="alternate" hreflang="en" href="https://example.com/docs/guide/">
    <link rel="alternate" hreflang="es" href="https://example.com/es/docs/guide/">
    <link rel="alternate" hreflang="ja" href="https://example.com/ja/docs/guide/">
    <link rel="alternate" hreflang="x-default" href="https://example.com/docs/guide/">
</head>
```

---

## Detailed Design

### Locale-Aware Page

```python
# bengal/core/page/i18n.py
from dataclasses import dataclass

@dataclass
class LocalizedPage:
    """Page with i18n awareness."""

    # Original page
    page: Page

    # Locale information
    locale: str
    is_default_locale: bool

    # Translations
    translations: dict[str, 'LocalizedPage']  # locale -> page

    # URL with locale
    localized_url: str

    # Fallback info
    is_fallback: bool = False  # True if showing default for missing translation

    @property
    def available_locales(self) -> list[str]:
        """Get list of locales this page is available in."""
        return [self.locale] + list(self.translations.keys())

    @property
    def hreflang_tags(self) -> list[dict]:
        """Generate hreflang link data."""
        tags = []

        # Self
        tags.append({
            "hreflang": self.locale,
            "href": self.localized_url,
        })

        # Translations
        for locale, page in self.translations.items():
            tags.append({
                "hreflang": locale,
                "href": page.localized_url,
            })

        # x-default (points to default locale version)
        if self.is_default_locale:
            tags.append({
                "hreflang": "x-default",
                "href": self.localized_url,
            })

        return tags
```

### Content Resolver

```python
# bengal/i18n/resolver.py

class LocaleResolver:
    """Resolve content for a specific locale."""

    def __init__(self, config: I18nConfig):
        self.config = config
        self.default_locale = config.default_locale

    def resolve_page(
        self,
        page_path: str,
        locale: str,
    ) -> tuple[Page, bool]:
        """
        Resolve page for locale.
        Returns (page, is_fallback).
        """

        if self.config.mode == "suffix":
            # Try locale-specific file first
            localized_path = self._add_locale_suffix(page_path, locale)
            if self._exists(localized_path):
                return (self._load(localized_path), False)

            # Try default locale
            if locale != self.default_locale and self.config.fallback_to_default:
                default_path = self._add_locale_suffix(page_path, self.default_locale)
                if self._exists(default_path):
                    return (self._load(default_path), True)

                # Try without suffix (implicit default)
                if self._exists(page_path):
                    return (self._load(page_path), True)

        elif self.config.mode == "folder":
            # Try locale folder
            localized_path = f"{locale}/{page_path}"
            if self._exists(localized_path):
                return (self._load(localized_path), False)

            # Fallback to default
            if locale != self.default_locale and self.config.fallback_to_default:
                default_path = f"{self.default_locale}/{page_path}"
                if self._exists(default_path):
                    return (self._load(default_path), True)

        raise PageNotFoundError(f"No content found for {page_path} in {locale}")

    def find_translations(self, page: Page) -> dict[str, Page]:
        """Find all translations of a page."""
        translations = {}
        base_path = self._strip_locale(page.source_path)

        for locale in self.config.locales:
            if locale.code == page.locale:
                continue

            try:
                translated, _ = self.resolve_page(base_path, locale.code)
                translations[locale.code] = translated
            except PageNotFoundError:
                pass

        return translations

    def _add_locale_suffix(self, path: str, locale: str) -> str:
        """Add locale suffix to path: guide.md -> guide.es.md"""
        if locale == self.default_locale:
            return path

        stem = path.rsplit(".", 1)[0]
        ext = path.rsplit(".", 1)[1] if "." in path else "md"
        return f"{stem}.{locale}.{ext}"
```

### Language Switcher Data

```python
# bengal/i18n/switcher.py

class LanguageSwitcher:
    """Generate language switcher data for templates."""

    def get_switcher_data(
        self,
        current_page: LocalizedPage,
        site: Site,
    ) -> list[dict]:
        """Generate data for language switcher component."""

        items = []

        for locale in site.config.i18n.locales:
            # Find translation or fallback
            if locale.code == current_page.locale:
                url = current_page.localized_url
                available = True
            elif locale.code in current_page.translations:
                url = current_page.translations[locale.code].localized_url
                available = True
            else:
                # Link to homepage in that locale
                url = f"/{locale.code}/" if not locale.default else "/"
                available = False

            items.append({
                "code": locale.code,
                "name": locale.name,
                "url": url,
                "current": locale.code == current_page.locale,
                "available": available,
            })

        return items
```

### Template Usage

```html
<!-- templates/partials/language-switcher.html -->
<div class="language-switcher">
    <button class="language-current">
        {{ page.locale_name }}
        <span class="arrow">▼</span>
    </button>
    <ul class="language-list">
        {% for lang in language_switcher %}
        <li class="{% if lang.current %}current{% endif %} {% if not lang.available %}unavailable{% endif %}">
            <a href="{{ lang.url }}" {% if lang.current %}aria-current="true"{% endif %}>
                {{ lang.name }}
                {% if not lang.available %}
                <span class="badge">Not translated</span>
                {% endif %}
            </a>
        </li>
        {% endfor %}
    </ul>
</div>
```

### Coverage Analysis

```python
# bengal/i18n/coverage.py

class TranslationCoverage:
    """Analyze translation coverage."""

    def analyze(self, site: Site) -> CoverageReport:
        """Generate translation coverage report."""

        report = CoverageReport()
        default_locale = site.config.i18n.default_locale

        # Get all pages in default locale
        default_pages = [p for p in site.pages if p.locale == default_locale]

        for locale in site.config.i18n.locales:
            if locale.code == default_locale:
                continue

            locale_pages = [p for p in site.pages if p.locale == locale.code]
            locale_paths = {self._normalize_path(p) for p in locale_pages}

            translated = 0
            missing = []

            for page in default_pages:
                norm_path = self._normalize_path(page)
                if norm_path in locale_paths:
                    translated += 1
                else:
                    missing.append(page.path)

            coverage_pct = (translated / len(default_pages)) * 100 if default_pages else 100

            report.locales[locale.code] = LocaleCoverage(
                locale=locale.code,
                total_pages=len(default_pages),
                translated_pages=translated,
                missing_pages=missing,
                coverage_percent=coverage_pct,
            )

        return report

    def print_report(self, report: CoverageReport):
        """Print coverage report to console."""

        console.print("\n📊 [bold]Translation Coverage Report[/bold]\n")

        table = Table()
        table.add_column("Locale")
        table.add_column("Translated")
        table.add_column("Missing")
        table.add_column("Coverage")

        for locale, coverage in report.locales.items():
            pct = coverage.coverage_percent
            color = "green" if pct >= 80 else "yellow" if pct >= 50 else "red"

            table.add_row(
                locale,
                str(coverage.translated_pages),
                str(len(coverage.missing_pages)),
                f"[{color}]{pct:.1f}%[/{color}]",
            )

        console.print(table)

        # Show missing pages for low-coverage locales
        for locale, coverage in report.locales.items():
            if coverage.missing_pages and coverage.coverage_percent < 80:
                console.print(f"\n[yellow]Missing in {locale}:[/yellow]")
                for path in coverage.missing_pages[:10]:
                    console.print(f"  • {path}")
                if len(coverage.missing_pages) > 10:
                    console.print(f"  ... and {len(coverage.missing_pages) - 10} more")
```

---

## CLI Interface

### Build with i18n

```bash
# Build all locales
bengal build

# Build specific locale only
bengal build --locale es

# Build default locale only (for testing)
bengal build --locale en --no-other-locales
```

### Coverage Report

```bash
bengal i18n coverage

# Output:
#
# 📊 Translation Coverage Report
#
# Locale    Translated    Missing    Coverage
# ──────────────────────────────────────────
# es        45            12         79.0%
# ja        28            29         49.1%
# de        52            5          91.2%
#
# Missing in ja:
#   • docs/advanced/plugins.md
#   • docs/api/reference.md
#   • docs/tutorials/quickstart.md
#   ... and 26 more
```

### Extract Strings (Future)

```bash
# Extract translatable strings for external tools
bengal i18n extract --format xliff --output translations/

# Import translations
bengal i18n import translations/es.xliff
```

---

## Sitemap Generation

```python
# bengal/postprocess/sitemap.py (enhanced)

def generate_sitemap_with_i18n(site: Site) -> str:
    """Generate sitemap with hreflang alternates."""

    urls = []

    for page in site.pages:
        url_entry = {
            "loc": page.absolute_url,
            "lastmod": page.last_modified,
            "priority": page.sitemap_priority,
        }

        # Add alternates for i18n
        if site.config.i18n.enabled:
            alternates = []
            for locale, translation in page.translations.items():
                alternates.append({
                    "hreflang": locale,
                    "href": translation.absolute_url,
                })
            # Add self
            alternates.append({
                "hreflang": page.locale,
                "href": page.absolute_url,
            })
            # Add x-default
            if page.is_default_locale:
                alternates.append({
                    "hreflang": "x-default",
                    "href": page.absolute_url,
                })

            url_entry["alternates"] = alternates

        urls.append(url_entry)

    return render_sitemap_xml(urls)
```

---

## Implementation Plan

### Phase 1: Core i18n (2 weeks)
- [ ] Locale configuration schema
- [ ] Suffix-based content resolution
- [ ] Page locale awareness

### Phase 2: URL Generation (1 week)
- [ ] Prefix URL strategy
- [ ] Hide default locale option
- [ ] hreflang tag generation

### Phase 3: Template Integration (1 week)
- [ ] Language switcher data
- [ ] Template context with locale
- [ ] Fallback indicators

### Phase 4: Coverage & Polish (2 weeks)
- [ ] Coverage analysis
- [ ] Sitemap with alternates
- [ ] Folder-based mode support
- [ ] Documentation

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| URL migration breaks SEO | High | Medium | Redirect generation, gradual rollout docs |
| Complex fallback logic | Medium | Medium | Clear configuration, good defaults |
| Large sites slow with many locales | Medium | Low | Parallel build per locale, caching |
| RTL languages need special handling | Medium | High | Document as separate concern, CSS-level |

---

## Open Questions

1. **Should we support per-section locale configuration?**
   - e.g., `/blog/` only in English, `/docs/` in all languages
   - Proposal: Yes, via section frontmatter

2. **How to handle locale-specific assets?**
   - Images with text, locale-specific screenshots
   - Proposal: Same suffix convention: `hero.es.png`

3. **Should default locale be hidden from URLs?**
   - `/docs/` vs `/en/docs/`
   - Proposal: Configurable, default to hidden

4. **Integration with translation management tools?**
   - Crowdin, Lokalise, Transifex
   - Proposal: Future RFC for integrations

---

## Success Criteria

- [ ] Basic i18n setup in <5 minutes
- [ ] hreflang tags generated correctly
- [ ] Language switcher works out of the box
- [ ] Coverage report identifies gaps
- [ ] Build time scales linearly with locales

---

## References

- [Google hreflang Guide](https://developers.google.com/search/docs/specialty/international/localized-versions)
- [Docusaurus i18n](https://docusaurus.io/docs/i18n/introduction)
- [Next.js Internationalization](https://nextjs.org/docs/advanced-features/i18n-routing)
- [W3C Internationalization](https://www.w3.org/International/)
