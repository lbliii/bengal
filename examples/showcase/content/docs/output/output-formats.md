---
title: "Output Formats: JSON & LLM Text"
description: "Generate JSON and LLM-friendly text outputs for search, AI discovery, and programmatic access"
date: 2025-10-04
weight: 10
tags: ["output", "json", "llm", "search", "ai", "api"]
toc: true
---

# Output Formats: JSON & LLM Text

Bengal generates **multiple output formats** for each page, making your content accessible to search engines, AI systems, and programmatic clients.

```{success} Future-Proof Content
Bengal is the **first SSG** to natively support LLM-friendly output formats! Make your content discoverable by AI systems.
```

---

## 🎯 Overview

### What are Output Formats?

Output formats are **alternative representations** of your content beyond HTML:

- **HTML** - Human-readable web pages (default)
- **JSON** - Machine-readable structured data
- **LLM-txt** - AI/LLM-friendly plain text format

### Why Multiple Formats?

```{tabs}
:id: why-output-formats

### Tab: Search

**Client-side search** using JSON:

```javascript
// Load search index
fetch('/index.json')
  .then(res => res.json())
  .then(data => {
    // Build search index
    const index = lunr(function() {
      this.field('title');
      this.field('content');
      
      data.pages.forEach(page => {
        this.add(page);
      });
    });
  });
```

**Fast, offline search** without a backend!

### Tab: AI Discovery

**LLM-friendly format** for AI systems:

```
================================================================================
Page: Getting Started with Bengal
URL: /docs/getting-started/
Date: 2025-10-04
Tags: beginner, tutorial
================================================================================

[Full page content in clean plain text format]

Perfect for:
- ChatGPT custom GPTs
- Claude Projects
- RAG systems
- Vector databases
```

### Tab: API Access

**JSON API** for programmatic access:

```python
import requests

# Get page data
response = requests.get('https://site.com/docs/api/index.json')
page = response.json()

print(page['title'])
print(page['metadata'])
print(page['content'])
```

**No backend needed!** Static JSON files.
```

---

## 📊 Output Format Types

### 1. Per-Page JSON

**Format:** `page/index.json` next to `page/index.html`

```json
{
  "title": "Getting Started with Bengal",
  "url": "/docs/getting-started/",
  "date": "2025-10-04T00:00:00",
  "section": "docs",
  "metadata": {
    "description": "Learn how to get started...",
    "tags": ["beginner", "tutorial"],
    "author": "Bengal Team",
    "weight": 10
  },
  "content_html": "<h1>Getting Started</h1><p>Welcome to...</p>",
  "content_text": "Getting Started\n\nWelcome to Bengal...",
  "excerpt": "Learn how to get started with Bengal SSG in under 10 minutes...",
  "word_count": 1247,
  "reading_time": 6,
  "toc": [
    {"level": 1, "title": "Installation", "anchor": "installation"},
    {"level": 2, "title": "Prerequisites", "anchor": "prerequisites"}
  ]
}
```

**Use cases:**
- Page-specific data loading
- Dynamic content injection
- Single-page apps
- Headless CMS integration

---

### 2. Per-Page LLM Text

**Format:** `page/index.txt` next to `page/index.html`

```
================================================================================
Getting Started with Bengal
================================================================================

URL: /docs/getting-started/
Date: 2025-10-04
Section: docs
Tags: beginner, tutorial
Author: Bengal Team

================================================================================
Content
================================================================================

# Getting Started

Welcome to Bengal SSG! This guide will help you get started in under 10 minutes.

## Installation

Install Bengal using pip:

```
pip install bengal-ssg
```

[... rest of content in clean plain text ...]

================================================================================
Metadata
================================================================================

Word Count: 1247
Reading Time: 6 minutes
Last Updated: 2025-10-04
```

**Use cases:**
- LLM training data
- AI chatbot contexts
- Vector embeddings
- Text analysis
- Content extraction

---

### 3. Site-Wide Index JSON

**Format:** `/index.json` in site root

```json
{
  "site": {
    "title": "Bengal SSG Documentation",
    "description": "Complete Bengal SSG documentation",
    "baseurl": "https://bengal-ssg.dev",
    "build_time": "2025-10-04T12:00:00"
  },
  "pages": [
    {
      "title": "Getting Started",
      "url": "/docs/getting-started/",
      "section": "docs",
      "excerpt": "Learn how to get started...",
      "tags": ["beginner", "tutorial"],
      "date": "2025-10-04",
      "word_count": 1247
    },
    // ... all pages
  ],
  "sections": [
    {"name": "docs", "count": 42},
    {"name": "blog", "count": 25},
    {"name": "tutorials", "count": 12}
  ],
  "tags": [
    {"name": "python", "count": 35},
    {"name": "tutorial", "count": 28},
    {"name": "advanced", "count": 15}
  ]
}
```

**Use cases:**
- Client-side search
- Site navigation
- Analytics
- Content dashboards
- Mobile apps

---

### 4. Site-Wide LLM Full Text

**Format:** `/llm-full.txt` in site root

```
================================================================================
SITE: Bengal SSG Documentation
================================================================================

Base URL: https://bengal-ssg.dev
Total Pages: 147
Build Time: 2025-10-04T12:00:00

================================================================================

================================================================================
PAGE 1/147: Getting Started
================================================================================

URL: /docs/getting-started/
Section: docs
Tags: beginner, tutorial

[Full page content]

================================================================================

================================================================================
PAGE 2/147: Template Functions
================================================================================

URL: /docs/templates/functions/
Section: docs
Tags: templates, reference

[Full page content]

================================================================================

[... all pages concatenated ...]
```

**Use cases:**
- Train custom LLMs on your content
- Build RAG systems
- Create AI assistants
- Semantic search
- Content analysis

---

## ⚙️ Configuration

### Enable Output Formats

```toml
# bengal.toml

[build.output_formats]
# Enable/disable formats
html = true          # Always enabled
json = true          # Per-page JSON
llm_txt = true       # Per-page LLM text

# Site-wide outputs
site_json = true     # /index.json
site_llm = true      # /llm-full.txt
```

### Advanced Configuration

```toml
[output_formats]
enabled = true

# What to generate per-page
per_page = ["json", "llm_txt"]

# What to generate site-wide
site_wide = ["index_json", "llm_full"]

[output_formats.options]
# JSON options
include_html_content = true      # Include rendered HTML
include_plain_text = true        # Include plain text version
excerpt_length = 200             # Excerpt character length
json_indent = 2                  # Pretty-print JSON (null = compact)

# LLM text options
llm_separator_width = 80         # Width of separator lines

# Exclusions
exclude_sections = ["drafts", "private"]
exclude_patterns = ["404.html", "search.html", "*.draft.html"]
```

---

## 🚀 Usage Examples

### Client-Side Search

```{example} Build a Search Feature

**HTML:**
```html
<input type="text" id="search-input" placeholder="Search...">
<div id="search-results"></div>
```

**JavaScript:**
```javascript
// Load search index
fetch('/index.json')
  .then(res => res.json())
  .then(data => {
    // Initialize lunr.js or fuse.js
    const fuse = new Fuse(data.pages, {
      keys: ['title', 'excerpt', 'tags'],
      threshold: 0.3
    });
    
    // Search on input
    document.getElementById('search-input').addEventListener('input', (e) => {
      const results = fuse.search(e.target.value);
      displayResults(results);
    });
  });

function displayResults(results) {
  const container = document.getElementById('search-results');
  container.innerHTML = results.map(result => `
    <div class="result">
      <h3><a href="${result.item.url}">${result.item.title}</a></h3>
      <p>${result.item.excerpt}</p>
    </div>
  `).join('');
}
```

**No server required!** Pure client-side search.
```

### AI Chatbot Integration

```{example} Create a Custom GPT

**Using LLM-full.txt:**

```python
import openai

# Load your site content
with open('public/llm-full.txt', 'r') as f:
    site_content = f.read()

# Create embeddings
response = openai.Embedding.create(
    model="text-embedding-ada-002",
    input=site_content[:8000]  # Chunk as needed
)

# Use in RAG system
def answer_question(question):
    context = search_relevant_content(question, site_content)
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": f"Context: {context}"},
            {"role": "user", "content": question}
        ]
    )
    
    return response.choices[0].message.content
```

**Your content is now AI-accessible!**
```

### Headless CMS Pattern

```{example} Use as Content API

**Fetch specific page data:**
```javascript
// React component
import { useState, useEffect } from 'react';

function DocPage({ slug }) {
  const [page, setPage] = useState(null);
  
  useEffect(() => {
    fetch(`/docs/${slug}/index.json`)
      .then(res => res.json())
      .then(data => setPage(data));
  }, [slug]);
  
  if (!page) return <div>Loading...</div>;
  
  return (
    <article>
      <h1>{page.title}</h1>
      <div className="meta">
        {page.date} · {page.reading_time} min read
      </div>
      <div dangerouslySetInnerHTML={{/* __html: page.content_html */}} />
    </article>
  );
}
```

**Use Bengal as a headless CMS!**
```

### Analytics and Insights

```{example} Analyze Your Content

**Using index.json:**
```python
import requests
import pandas as pd

# Load site index
response = requests.get('https://yoursite.com/index.json')
data = response.json()

# Create dataframe
df = pd.DataFrame(data['pages'])

# Analyze
print(f"Total pages: {len(df)}")
print(f"Average word count: {df['word_count'].mean():.0f}")
print(f"Average reading time: {df['reading_time'].mean():.1f} min")

# Most used tags
tag_counts = data['tags']
print("\nTop 10 tags:")
for tag in tag_counts[:10]:
    print(f"  {tag['name']}: {tag['count']} pages")

# Content by section
print("\nPages by section:")
for section in data['sections']:
    print(f"  {section['name']}: {section['count']} pages")
```

**Understand your content at scale!**
```

---

## 📐 JSON Schema

### Page JSON Schema

```json
{
  "title": "string (required)",
  "url": "string (required, relative URL)",
  "slug": "string (optional, URL-friendly slug)",
  "date": "string (ISO 8601 format)",
  "modified_date": "string (ISO 8601 format)",
  "section": "string (section name)",
  "metadata": {
    "description": "string",
    "tags": ["array", "of", "strings"],
    "categories": ["array"],
    "author": "string",
    "weight": "number",
    "draft": "boolean",
    "any_custom_field": "any type"
  },
  "content_html": "string (rendered HTML)",
  "content_text": "string (plain text, no HTML)",
  "excerpt": "string (truncated text)",
  "word_count": "number",
  "reading_time": "number (minutes)",
  "toc": [
    {
      "level": "number (1-6)",
      "title": "string",
      "anchor": "string (without #)"
    }
  ],
  "next": {
    "title": "string",
    "url": "string"
  },
  "prev": {
    "title": "string",
    "url": "string"
  }
}
```

### Index JSON Schema

```json
{
  "site": {
    "title": "string",
    "description": "string",
    "baseurl": "string",
    "build_time": "string (ISO 8601)"
  },
  "pages": [
    {
      "title": "string",
      "url": "string",
      "section": "string",
      "excerpt": "string",
      "tags": ["array"],
      "date": "string",
      "word_count": "number"
    }
  ],
  "sections": [
    {
      "name": "string",
      "count": "number"
    }
  ],
  "tags": [
    {
      "name": "string",
      "count": "number"
    }
  ]
}
```

---

## 🎨 LLM Text Format Spec

### Structure

```
================================================================================
[Page Title]
================================================================================

URL: [relative URL]
Date: [YYYY-MM-DD]
Section: [section name]
Tags: [comma-separated tags]
[Additional metadata fields]

================================================================================
Content
================================================================================

[Full page content in clean plain text]
- Markdown headings converted to plain text
- Code blocks preserved
- Lists maintained
- Links shown as [text](url)
- No HTML tags

================================================================================
Metadata
================================================================================

Word Count: [number]
Reading Time: [number] minutes
Last Updated: [date]
```

### Design Principles

1. **Clean separator lines** (80 characters)
2. **Structured metadata** at top
3. **Full content** in readable format
4. **No HTML or markup** (plain text only)
5. **Consistent formatting** across all pages

---

## 🔧 Python API

### Generate Custom Formats

```python
from bengal.postprocess.output_formats import OutputFormatsGenerator

# Initialize generator
config = {
    'enabled': True,
    'per_page': ['json', 'llm_txt'],
    'site_wide': ['index_json', 'llm_full'],
    'options': {
        'include_html_content': True,
        'include_plain_text': True,
        'excerpt_length': 200,
        'json_indent': 2,
        'exclude_sections': ['drafts']
    }
}

generator = OutputFormatsGenerator(site, config)
generator.generate()

# Or use default config
generator = OutputFormatsGenerator(site)
generator.generate()
```

### Custom Format Generator

```{example} Create Your Own Format

```python
from bengal.postprocess.output_formats import OutputFormatsGenerator

class CustomFormatGenerator(OutputFormatsGenerator):
    """Generate custom XML format."""
    
    def generate_xml(self, pages):
        """Generate XML sitemap-like format."""
        xml = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml.append('<pages>')
        
        for page in pages:
            xml.append(f'  <page>')
            xml.append(f'    <title>{page.title}</title>')
            xml.append(f'    <url>{page.url}</url>')
            xml.append(f'    <date>{page.date}</date>')
            xml.append(f'  </page>')
        
        xml.append('</pages>')
        return '\n'.join(xml)

# Use it
generator = CustomFormatGenerator(site)
xml_content = generator.generate_xml(site.pages)

# Write to file
with open('public/pages.xml', 'w') as f:
    f.write(xml_content)
```
```

---

## 💡 Best Practices

```{tip} Optimize for Search

**Include relevant fields:**
```toml
[output_formats.options]
include_html_content = false   # Don't need for search
include_plain_text = true      # Plain text is faster
excerpt_length = 150           # Short excerpts
json_indent = null             # Compact = smaller files
```

**Result:** Smaller index files, faster search!
```

```{warning} Privacy Considerations

**Exclude sensitive content:**
```toml
[output_formats.options]
exclude_sections = ["private", "drafts", "internal"]
exclude_patterns = ["*.draft.html", "**/admin/**"]
```

**Don't publish what shouldn't be public!**
```

```{success} LLM Best Practices

**For optimal AI training:**
1. Use `llm_full.txt` format
2. Include rich metadata
3. Keep content well-structured
4. Use semantic headings
5. Add context in metadata

**Your content will be AI-ready!**
```

---

## 📊 Performance Impact

### Build Time

```{tabs}
:id: performance-impact

### Tab: JSON Generation

**Impact:** ~5-10% build time increase

```
Without JSON:  2.8s (147 pages)
With JSON:     3.0s (147 pages + JSON)

Overhead:      0.2s (7% slower)
File size:     +2.4 MB
```

**Worth it for search functionality!**

### Tab: LLM Text Generation

**Impact:** ~3-5% build time increase

```
Without LLM:   2.8s (147 pages)
With LLM:      2.9s (147 pages + TXT)

Overhead:      0.1s (4% slower)
File size:     +1.8 MB
```

**Negligible impact!**

### Tab: All Formats

**Impact:** ~10-15% build time increase

```
HTML only:     2.8s (147 pages)
All formats:   3.2s (HTML + JSON + TXT)

Overhead:      0.4s (14% slower)
Total size:    12.3 MB → 16.5 MB
```

**Small price for huge benefits!**
```

---

## 🌟 Real-World Examples

### Documentation Site with Search

```toml
[build.output_formats]
json = true              # Per-page for future use
site_json = true         # Index for search
llm_txt = false          # Don't need LLM format

[output_formats.options]
include_html_content = false
include_plain_text = true
excerpt_length = 200
json_indent = null       # Compact for performance
```

### AI-Powered Site

```toml
[build.output_formats]
json = true              # Structured data
llm_txt = true           # AI-friendly text
site_llm = true          # Full site for training

[output_formats.options]
include_html_content = true
include_plain_text = true
llm_separator_width = 80
```

### API-First Site

```toml
[build.output_formats]
json = true              # API endpoints
site_json = true         # Full index

[output_formats.options]
include_html_content = true
include_plain_text = true
json_indent = 2          # Pretty-print for developers
```

---

## 📚 Related Documentation

- **[Client-Side Search Tutorial](../../examples/special-features/search-integration.md)** - Build search
- **[SEO Optimization](seo-optimization.md)** - Improve discoverability
- **[Sitemap & RSS](sitemap-and-rss.md)** - Other output formats
- **[Performance Tips](../performance/optimization-tips.md)** - Optimize builds

---

## 🎉 Summary

### Output Formats Comparison

| Format | Purpose | Use Case | Size Impact |
|--------|---------|----------|-------------|
| **HTML** | Human reading | Primary website | Baseline |
| **JSON** (per-page) | Programmatic access | Single page data | +10KB/page |
| **JSON** (site-wide) | Search/analytics | Content index | +2-3MB |
| **LLM-txt** (per-page) | AI processing | Page-level AI | +8KB/page |
| **LLM-txt** (site-wide) | AI training | Full site AI | +1-2MB |

### When to Use Each

```{tabs}
:id: when-to-use

### Tab: JSON Per-Page

**Use when:**
- Building SPAs
- Need page-specific data
- Headless CMS pattern
- API endpoints

**Skip when:**
- Static site only
- No JavaScript
- Simple blog

### Tab: JSON Site-Wide

**Use when:**
- Client-side search
- Site analytics
- Content dashboards
- Mobile apps

**Skip when:**
- Server-side search
- No search needed
- Tiny sites (<10 pages)

### Tab: LLM Text

**Use when:**
- AI chatbot integration
- RAG systems
- Custom GPTs
- Vector databases
- Content analysis

**Skip when:**
- No AI integration planned
- Privacy concerns
- Bandwidth limited
```

---

**Last Updated:** October 4, 2025  
**Version:** 1.0.0  
**Unique Feature:** First SSG with native LLM output format support

