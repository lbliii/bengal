# Bengal Content Processing API
**What Bengal Computes vs What Themes Display**

Last Updated: 2025-10-26

---

## Philosophy

**Bengal computes. Themes display.**

The `content` config section controls **what Bengal computes** during build time. These computed properties are available to ALL themes consistently. Themes decide whether to display them and how to style them.

---

## Current Computed Properties

### Page Properties (`page.*`)

| Property | Config Control | Template Access | Purpose |
|----------|---------------|-----------------|---------|
| `page.excerpt` | `excerpt_length` (200) | `{{ page.excerpt }}` | Content preview for cards/listings |
| `page.meta_description` | `summary_length` (160) | `{{ page.meta_description }}` | SEO meta description |
| `page.reading_time` | `reading_speed` (200 WPM) | `{{ page.reading_time }}` | Estimated reading time in minutes |
| `page.toc` | `toc_depth` (3), `toc_min_headings` (2), `toc_style` ("nested") | `{{ page.toc \| safe }}` | Generated table of contents HTML |
| `page.toc_items` | (derived from `toc`) | `{% for item in page.toc_items %}` | Structured TOC data for custom rendering |
| `page.related_posts` | `related_count` (3), `related_threshold` (0.3) | `{% for post in page.related_posts %}` | Related pages based on tag similarity |
| `page.url` | (automatic) | `{{ page.url }}` | Relative URL path |
| `page.permalink` | (automatic) | `{{ page.permalink }}` | Absolute URL with baseurl |
| `page.title` | (from metadata or generated) | `{{ page.title }}` | Page title (humanized from filename if missing) |
| `page.date` | `date_format` ("long") | `{{ page.date }}` | Parsed date object |
| `page.slug` | (from metadata or generated) | `{{ page.slug }}` | URL-safe slug |
| `page.keywords` | (from metadata) | `{{ page.keywords }}` | SEO keywords list |
| `page.is_home` | (automatic) | `{% if page.is_home %}` | Boolean: is this the home page? |
| `page.is_section` | (automatic) | `{% if page.is_section %}` | Boolean: is this a section? |
| `page.is_page` | (automatic) | `{% if page.is_page %}` | Boolean: is this a regular page? |
| `page.kind` | (automatic) | `{{ page.kind }}` | Page type: "home", "section", or "page" |
| `page.draft` | (from metadata) | `{% if page.draft %}` | Boolean: is this a draft? |
| `page.next` | (automatic) | `{% if page.next %}` | Next page in site-wide collection |
| `page.prev` | (automatic) | `{% if page.prev %}` | Previous page in site-wide collection |
| `page.next_in_section` | (respects `sort_pages_by`) | `{% if page.next_in_section %}` | Next page in same section |
| `page.prev_in_section` | (respects `sort_pages_by`) | `{% if page.prev_in_section %}` | Previous page in same section |
| `page.parent` | (automatic) | `{{ page.parent.title }}` | Parent section |
| `page.ancestors` | (automatic) | `{% for ancestor in page.ancestors %}` | List of ancestor sections |

### Section Properties (`section.*`)

| Property | Config Control | Template Access | Purpose |
|----------|---------------|-----------------|---------|
| `section.sorted_pages` | `sort_pages_by` ("weight"), `sort_order` ("asc") | `{% for page in section.sorted_pages %}` | Pages sorted by weight/date/title |
| `section.sorted_subsections` | (respects `weight` in index metadata) | `{% for sub in section.sorted_subsections %}` | Sorted child sections |
| `section.subsection_index_urls` | (automatic) | `{% if page.url not in section.subsection_index_urls %}` | Set of subsection index URLs (for nav de-duplication) |
| `section.regular_pages` | (automatic) | `{% for page in section.regular_pages %}` | Non-index pages in this section |
| `section.regular_pages_recursive` | (automatic) | `{% for page in section.regular_pages_recursive %}` | All descendant pages |
| `section.url` | (automatic) | `{{ section.url }}` | Section URL |
| `section.permalink` | (automatic) | `{{ section.permalink }}` | Section URL with baseurl |
| `section.hierarchy` | (automatic) | `{{ section.hierarchy }}` | List of section names from root |
| `section.depth` | (automatic) | `{{ section.depth }}` | Nesting depth |
| `section.root` | (automatic) | `{{ section.root.title }}` | Top-most ancestor section |
| `section.title` | (from index metadata or generated) | `{{ section.title }}` | Section title |
| `section.aggregate_content()` | (automatic) | `{{ section.aggregate_content().page_count }}` | Aggregated stats (page counts, tags) |

---

## Config Examples

### Current Computations

```yaml
# config/_default/content.yaml
content:
  # Default content type (affects template selection)
  default_type: "doc"
  
  # Excerpt generation
  excerpt_length: 200
  summary_length: 160
  
  # Reading time
  reading_speed: 250  # Words per minute
  
  # Related posts
  related_count: 5
  related_threshold: 0.25
  
  # Table of contents
  toc_depth: 4
  toc_min_headings: 3
  toc_style: "nested"
  
  # Content organization
  sort_pages_by: "weight"
  sort_order: "asc"
```

### Theme Display Preferences (Separate File)

```yaml
# config/_default/theme.yaml
theme:
  name: "default"
  
  # These control DISPLAY, not computation
  show_reading_time: true
  show_author: true
  show_breadcrumbs: true
  show_toc: true
```

**Key Insight**: Changing `content.excerpt_length` changes what `page.excerpt` returns. Changing `theme.show_excerpts` changes whether the theme displays it.

---

## Future Enhancements (Not Yet Implemented)

These are potential computed properties Bengal could provide in future versions:

### Word Count

```yaml
content:
  word_count_enabled: true  # Expose page.word_count
```

**Template Access**: `{{ page.word_count }} words`

**Rationale**: Currently computed internally for `reading_time` but not exposed. Useful for writers, analytics, and content dashboards.

### Author Formatting

```yaml
content:
  author_format: "name_email"  # Options: "name", "name_email", "full"
```

**Template Access**: `{{ page.author }}`

**Rationale**: Currently just raw metadata. Bengal could format consistently: "Jane Doe", "Jane Doe <jane@example.com>", "Jane Doe (Software Engineer)".

### Custom Excerpt Truncation

```yaml
content:
  excerpt_ellipsis: "... [continue reading]"
```

**Template Access**: `{{ page.excerpt }}`

**Rationale**: Currently hard-coded to "...". Custom endings improve UX: "... [read more]", "...(continued)", etc.

### Social Media Excerpts

```yaml
content:
  social_excerpt_length: 280  # Twitter-optimized
```

**Template Access**: `{{ page.social_excerpt }}`

**Rationale**: Different platforms have different length limits (Twitter 280, LinkedIn 600, Facebook 500). Separate property optimizes for each.

### Git-Based Last Modified

```yaml
content:
  last_modified_from_git: true
```

**Template Access**: `{{ page.last_modified }}`

**Rationale**: More accurate than file system timestamps. Shows "Last updated: 2025-10-25" based on git history.

### Reading Level Analysis

```yaml
content:
  reading_level_enabled: true  # Flesch-Kincaid grade level
```

**Template Access**: `{{ page.reading_level }}`

**Rationale**: Help content authors gauge readability. "Grade 8" means readable by 8th graders. Useful for docs targeting specific audiences.

### Section Statistics

```yaml
content:
  section_stats_enabled: true
```

**Template Access**: 
```jinja2
{{ section.total_words }}
{{ section.avg_reading_time }}
{{ section.content_freshness }}  # Days since last update
```

**Rationale**: Help site authors understand content health. "This section has 12,500 words across 8 articles, averaging 6 min read. Last updated 3 days ago."

---

## Non-Computational Properties (Raw Data)

These are NOT computed by Bengal but are available directly from frontmatter metadata:

- `page.metadata` - Raw frontmatter dict
- `page.tags` - Tags list
- `page.content` - Raw markdown content
- `page.rendered_html` - Rendered HTML
- `page.source_path` - Source file path
- `page.output_path` - Output file path
- `page.links` - Extracted links
- `page.lang` - Language code (i18n)
- `page.translation_key` - Translation identifier (i18n)
- `page.version` - Version string (for versioned docs)

These can be accessed directly without configuration:

```jinja2
{{ page.tags | join(", ") }}
{{ page.metadata.custom_field }}
```

---

## Architectural Boundaries

### ✅ Content Config SHOULD Control:

- **Computations**: How to calculate derived values
- **Algorithms**: Related posts similarity thresholds, TOC depth
- **Organization**: Sorting, filtering, grouping
- **Content Analysis**: Reading time, excerpts, word counts

### ❌ Content Config SHOULD NOT Control:

- **Display**: show/hide features (use `theme.yaml`)
- **Styling**: colors, fonts, layouts (use theme CSS)
- **Presentation**: card layouts, grid vs list (use theme templates)
- **Interactions**: animations, transitions (use theme JS)

### Examples

**✅ Good (Content Config)**:
```yaml
excerpt_length: 300  # Bengal computes a 300-char excerpt
reading_speed: 250   # Bengal calculates reading time at 250 WPM
```

**❌ Bad (Content Config)**:
```yaml
show_excerpts: true  # This is presentation (belongs in theme.yaml)
excerpt_color: "gray"  # This is styling (belongs in theme CSS)
```

**✅ Good (Theme Config)**:
```yaml
show_reading_time: true  # Theme displays reading time
show_excerpts_in_cards: true  # Theme shows excerpts in card layout
```

---

## Testing Computational API

To verify config-controlled computations work correctly:

```python
def test_excerpt_length_config():
    """Verify excerpt_length config controls page.excerpt."""
    config = {"content": {"excerpt_length": 100}}
    page = build_page(content="..." * 200, config=config)
    assert len(page.excerpt) <= 105  # ~100 + ellipsis
```

See `tests/unit/test_page_computed.py` for full test suite.

---

## Migration Guide: Hugo → Bengal

| Hugo Config | Bengal Equivalent | Reason |
|-------------|-------------------|--------|
| `params.show_reading_time` | `theme.show_reading_time` | Display control (theme) |
| `params.excerpt_length` | `content.excerpt_length` | Computation control (Bengal) |
| `params.default_content_type` | `content.default_type` | Content model control (Bengal) |
| `params.custom_var` | `params.custom_var` | User variable (unchanged) |

---

## Best Practices

1. **Config Organization**:
   - `content.yaml`: Controls **what Bengal computes**
   - `theme.yaml`: Controls **what themes display**
   - `params.yaml`: Custom variables for templates

2. **Theme Development**:
   - Always check `if page.toc` before rendering TOC
   - Use `page.excerpt` not `page.content[:200]`
   - Respect `theme.show_*` preferences

3. **Content Authoring**:
   - Override computed values via frontmatter: `excerpt: "Custom excerpt"`
   - Control page order via `weight` metadata
   - Use `draft: true` to hide pages

4. **Site Configuration**:
   - Start with defaults
   - Tune for your audience (faster readers? increase `reading_speed`)
   - Validate changes (lower `related_threshold` shows more related posts)

---

## Summary

**Bengal provides a clean separation**:

- **Content Config** → What Bengal computes (theme-independent)
- **Theme Config** → What themes display (presentation layer)
- **Params Config** → Custom user data (arbitrary variables)

This architecture ensures:
- ✅ Themes are interchangeable (computation is consistent)
- ✅ Config is composable (change one without affecting others)
- ✅ Upgrades are safe (new themes work with existing config)
- ✅ Behavior is predictable (same config = same computation)

**Core Principle**: Bengal's content API is a **contract** between the build system and themes. Config controls the contract. Themes consume the contract.

