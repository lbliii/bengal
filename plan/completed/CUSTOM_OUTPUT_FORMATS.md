# Custom Output Formats Implementation Plan

**Date:** October 4, 2025  
**Status:** 🚧 In Progress  
**Priority:** High - Modern feature for search, AI discovery, programmatic access

---

## 🎯 Goal

Implement custom output formats similar to Hugo's output formats feature, enabling:
- **Per-page outputs**: JSON and LLM-friendly text for each article
- **Aggregate outputs**: Site-wide index.json and llm-full.txt

---

## 📋 Use Cases

### 1. Search Functionality
```javascript
// Client-side search can fetch index.json
fetch('/index.json')
  .then(r => r.json())
  .then(pages => {
    // Build search index from all pages
  });
```

### 2. AI/LLM Discovery
```
# llm-full.txt provides complete site content in AI-friendly format
curl https://mysite.com/llm-full.txt

# Per-page LLM format for specific articles
curl https://mysite.com/docs/intro.txt
```

### 3. Programmatic Access
```python
# API-like access to content
import requests
data = requests.get('https://mysite.com/api/index.json').json()
pages = data['pages']
```

### 4. Static Search Engines
```
Tools like Pagefind, Lunr.js, or custom search can use JSON index
```

---

## 🏗️ Architecture

### Similar to Existing Postprocessing

```
bengal/postprocess/
  ├── __init__.py
  ├── rss.py              ← Site-wide XML feed (existing)
  ├── sitemap.py          ← Site-wide XML index (existing)
  └── output_formats.py   ← NEW: Custom output formats
```

### Generator Pattern

Like RSS and Sitemap generators, the new `OutputFormatsGenerator`:
- Iterates over all pages
- Generates output files based on configuration
- Writes to output directory
- Supports parallel execution

---

## 📝 Output Format Specifications

### 1. Per-Page JSON (`page.json`)

```json
{
  "url": "/docs/intro/",
  "title": "Introduction to Bengal",
  "description": "Getting started with Bengal SSG",
  "date": "2025-10-04T00:00:00Z",
  "content": "<p>Full rendered HTML content...</p>",
  "plain_text": "Full rendered content without HTML tags...",
  "excerpt": "Getting started with Bengal SSG. Bengal is a...",
  "metadata": {
    "author": "John Doe",
    "tags": ["docs", "intro"],
    "weight": 10
  },
  "section": "docs",
  "word_count": 1234,
  "reading_time": 5
}
```

**Placement:** Next to HTML file
```
public/docs/intro/
  ├── index.html    ← Regular HTML
  └── index.json    ← JSON output
```

### 2. Per-Page LLM Text (`page.txt`)

```
# Introduction to Bengal

URL: /docs/intro/
Section: docs
Tags: docs, intro
Date: 2025-10-04

---

Getting started with Bengal SSG. Bengal is a modern, fast static site generator...

[Full plain text content without HTML tags]

---

Metadata:
- Author: John Doe
- Word Count: 1234
- Reading Time: 5 minutes
```

**Placement:** Next to HTML file
```
public/docs/intro/
  ├── index.html    ← Regular HTML
  └── index.txt     ← LLM text
```

### 3. Site-Wide Index (`index.json`)

```json
{
  "site": {
    "title": "Bengal Documentation",
    "description": "Modern static site generator",
    "baseurl": "https://bengal.dev",
    "build_time": "2025-10-04T12:00:00Z"
  },
  "pages": [
    {
      "url": "/docs/intro/",
      "title": "Introduction",
      "description": "Getting started",
      "date": "2025-10-04",
      "section": "docs",
      "tags": ["docs", "intro"],
      "excerpt": "Getting started with Bengal...",
      "word_count": 1234,
      "reading_time": 5
    },
    {
      "url": "/blog/my-post/",
      "title": "My Blog Post",
      "description": "A great post",
      "date": "2025-10-03",
      "section": "blog",
      "tags": ["news"],
      "excerpt": "This is a great post about...",
      "word_count": 800,
      "reading_time": 3
    }
  ],
  "sections": [
    {"name": "docs", "count": 15},
    {"name": "blog", "count": 8}
  ],
  "tags": [
    {"name": "docs", "count": 12},
    {"name": "tutorial", "count": 8}
  ]
}
```

**Placement:** Root of public directory
```
public/
  ├── index.html
  └── index.json    ← Site index
```

### 4. Site-Wide LLM Text (`llm-full.txt`)

```
# Bengal Documentation

Site: https://bengal.dev
Build Date: 2025-10-04T12:00:00Z
Total Pages: 23

================================================================================

## Page 1/23: Introduction to Bengal

URL: /docs/intro/
Section: docs
Tags: docs, intro

Getting started with Bengal SSG...

[Full content]

================================================================================

## Page 2/23: Installation Guide

URL: /docs/install/
Section: docs
Tags: docs, installation

How to install Bengal...

[Full content]

================================================================================
```

**Placement:** Root of public directory
```
public/
  ├── index.html
  └── llm-full.txt  ← Full site text
```

---

## ⚙️ Configuration

### bengal.toml

```toml
# Enable/disable output formats
[output_formats]
enabled = true

# Per-page formats
per_page = ["json", "llm_txt"]  # json, llm_txt, or both

# Site-wide formats
site_wide = ["index_json", "llm_full"]  # index_json, llm_full, or both

# Options
[output_formats.options]
# Include full HTML content in JSON? (default: true)
include_html_content = true

# Include full plain text in JSON? (default: true)
include_plain_text = true

# Maximum excerpt length for site index (default: 200)
excerpt_length = 200

# Exclude sections from outputs (default: [])
exclude_sections = ["admin", "private"]

# Exclude pages by pattern (default: [])
exclude_patterns = ["404.html", "search.html"]

# Pretty-print JSON? (default: false for size)
json_indent = false

# LLM text separator (default: 80 = chars)
llm_separator_width = 80
```

### Sensible Defaults

If no config specified:
```python
{
    'enabled': True,
    'per_page': ['json'],  # JSON by default, LLM text opt-in
    'site_wide': ['index_json'],  # Index by default, llm-full opt-in
    'options': {
        'include_html_content': True,
        'include_plain_text': True,
        'excerpt_length': 200,
        'exclude_sections': [],
        'exclude_patterns': ['404.html', 'search.html'],
        'json_indent': False,
        'llm_separator_width': 80,
    }
}
```

---

## 🔧 Implementation

### File Structure

```python
# bengal/postprocess/output_formats.py

class OutputFormatsGenerator:
    """
    Generates custom output formats for pages.
    
    Supports:
    - Per-page JSON output
    - Per-page LLM text output
    - Site-wide index.json
    - Site-wide llm-full.txt
    """
    
    def __init__(self, site, config):
        self.site = site
        self.config = config or self._default_config()
    
    def generate(self):
        """Generate all enabled output formats."""
        if not self.config.get('enabled', True):
            return
        
        per_page = self.config.get('per_page', ['json'])
        site_wide = self.config.get('site_wide', ['index_json'])
        
        # Per-page outputs
        if 'json' in per_page:
            self._generate_page_json()
        
        if 'llm_txt' in per_page:
            self._generate_page_txt()
        
        # Site-wide outputs
        if 'index_json' in site_wide:
            self._generate_site_index_json()
        
        if 'llm_full' in site_wide:
            self._generate_site_llm_txt()
    
    def _generate_page_json(self):
        """Generate JSON file for each page."""
        pass
    
    def _generate_page_txt(self):
        """Generate LLM-friendly text for each page."""
        pass
    
    def _generate_site_index_json(self):
        """Generate site-wide index.json."""
        pass
    
    def _generate_site_llm_txt(self):
        """Generate site-wide llm-full.txt."""
        pass
```

### Integration Point

```python
# bengal/orchestration/postprocess.py

def run(self, parallel: bool = True) -> None:
    """Perform post-processing tasks."""
    print("\n🔧 Post-processing:")
    
    tasks = []
    
    if self.site.config.get("generate_sitemap", True):
        tasks.append(('sitemap', self._generate_sitemap))
    
    if self.site.config.get("generate_rss", True):
        tasks.append(('rss', self._generate_rss))
    
    # NEW: Custom output formats
    if self.site.config.get("output_formats", {}).get("enabled", True):
        tasks.append(('output formats', self._generate_output_formats))
    
    # ... rest of implementation

def _generate_output_formats(self) -> None:
    """Generate custom output formats."""
    from bengal.postprocess.output_formats import OutputFormatsGenerator
    config = self.site.config.get("output_formats", {})
    generator = OutputFormatsGenerator(self.site, config)
    generator.generate()
```

---

## 🎨 Helper Functions

### Extract Plain Text from HTML

```python
def _extract_plain_text(self, html: str) -> str:
    """
    Extract plain text from HTML content.
    
    Similar to strip_html but more sophisticated:
    - Preserves paragraph breaks
    - Handles lists properly
    - Decodes HTML entities
    """
    # Use existing strip_html from template functions
    from bengal.rendering.template_functions.strings import strip_html
    return strip_html(html)
```

### Generate Excerpt

```python
def _generate_excerpt(self, content: str, length: int = 200) -> str:
    """Generate smart excerpt from content."""
    # Use existing excerpt function from template functions
    from bengal.rendering.template_functions.strings import excerpt
    return excerpt(content, length=length)
```

### Calculate Reading Time

```python
def _reading_time(self, content: str) -> int:
    """Calculate reading time in minutes."""
    # Use existing reading_time function
    from bengal.rendering.template_functions.strings import reading_time
    return reading_time(content)
```

---

## 🚀 Benefits

### 1. Search Functionality
- ✅ Zero-dependency client-side search
- ✅ Fast static index
- ✅ Works with popular search tools (Pagefind, Lunr.js, Fuse.js)

### 2. AI Discovery
- ✅ LLM-friendly text format
- ✅ Easy for AI to parse and index
- ✅ Per-page and full-site options

### 3. Programmatic Access
- ✅ JSON API-like interface
- ✅ No server required
- ✅ Works with static hosting

### 4. Flexibility
- ✅ Enable/disable per format
- ✅ Configurable options
- ✅ Extensible for future formats

---

## 📊 Performance Considerations

### File Size

**Per-page JSON:**
- ~2-5 KB per page (without content)
- ~10-50 KB per page (with full HTML)
- Negligible for modern hosting

**Site index:**
- ~100-500 KB for 100 pages
- Compresses well with gzip (~20-30%)

**LLM full text:**
- ~500 KB - 2 MB for 100 pages
- Very compressible (~50-70% with gzip)

### Build Time

**Impact:** ~5-15ms per format
- JSON serialization: fast
- Text extraction: moderate
- File I/O: minimal

**Total overhead:** < 100ms for 100 pages

---

## 🎯 Success Criteria

- [ ] Per-page JSON output works
- [ ] Per-page LLM text output works
- [ ] Site-wide index.json aggregates correctly
- [ ] Site-wide llm-full.txt concatenates properly
- [ ] Configuration via bengal.toml works
- [ ] Excluded sections/patterns honored
- [ ] Performance impact < 100ms
- [ ] Works with parallel builds
- [ ] Integrates with incremental builds
- [ ] Documentation complete

---

## 🔮 Future Enhancements

### Phase 2: Additional Formats
- **YAML output** (for static APIs)
- **CSV output** (for data exports)
- **Markdown output** (for export/backup)

### Phase 3: Custom Templates
```toml
[output_formats.custom]
formats = [
    { name = "api", template = "api.json", extension = ".api.json" }
]
```

### Phase 4: Per-Section Configuration
```toml
[output_formats.sections.docs]
per_page = ["json", "llm_txt", "yaml"]

[output_formats.sections.blog]
per_page = ["json"]  # Only JSON for blog
```

---

## 📚 References

### Hugo Output Formats
- https://gohugo.io/templates/output-formats/
- Supports JSON, AMP, Calendar, etc.
- Per-page and custom formats

### Jekyll Data Files
- https://jekyllrb.com/docs/datafiles/
- JSON/YAML data access
- Limited output format support

### Pagefind
- https://pagefind.app/
- Modern search for static sites
- Can use JSON index

---

## ✅ Next Steps

1. **Implement OutputFormatsGenerator** (this session)
2. **Integrate into postprocess orchestrator**
3. **Test with quickstart example**
4. **Add configuration to bengal.toml**
5. **Document in GETTING_STARTED.md**
6. **Add to feature comparison docs**

---

**End of Plan**

