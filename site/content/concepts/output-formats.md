---
title: Output Formats
description: Generate JSON, LLM-ready text, and custom output formats
weight: 30
---

Bengal can generate multiple output formats for your content, enabling search functionality, AI discovery, and programmatic access.

## Available Formats

### Per-Page Formats

Generated for every page in your site:

- **JSON** (`index.json`): Structured data including metadata, HTML content, and plain text.
- **LLM Text** (`index.txt`): AI-friendly plain text format optimized for RAG (Retrieval-Augmented Generation) and LLM consumption.

### Site-Wide Formats

Generated at the site root:

- **Site Index** (`index.json`): A searchable index of all pages (useful for client-side search).
- **Full LLM Text** (`llm-full.txt`): The complete content of your site in a single plain text file.

## Configuration

Enable output formats in `bengal.toml`:

```toml
[output_formats]
enabled = true
per_page = ["json", "llm_txt"]        # Formats for individual pages
site_wide = ["index_json", "llm_full"] # Formats for the whole site

[output_formats.options]
include_html_content = true    # Include full HTML in JSON
include_plain_text = true      # Include plain text in JSON
excerpt_length = 200           # Excerpt length for site index
json_indent = 2                # Pretty-print JSON (use null for compact)
```

## Use Cases

### 1. Client-Side Search

Fetch the site index to implement fast, client-side search without a backend.

```javascript
fetch('/index.json')
  .then(response => response.json())
  .then(data => {
    const results = data.pages.filter(page => 
      page.title.includes(query) || page.excerpt.includes(query)
    );
  });
```

### 2. AI & LLM Discovery

Provide `llm-full.txt` to LLMs to allow them to ingest your entire documentation site efficiently.

```bash
curl https://mysite.com/llm-full.txt
```

### 3. Static API

Use your static site as a read-only API for other applications.

```python
import requests

# Get page data
data = requests.get('https://mysite.com/docs/intro/index.json').json()
print(data['title'])
print(data['word_count'])
```

