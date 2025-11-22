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
- **LLM Text** (`index.txt`): AI-friendly plain text format optimized for **RAG** (Retrieval-Augmented Generation) and LLM consumption. RAG allows AI models to "read" your documentation to answer questions accurately.

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
# exclude_sections = ["private"] # Sections to exclude from output formats
```

:::{note}
**Visibility**: Output formats currently expose all rendered pages unless specifically excluded via `exclude_sections` or `exclude_patterns`. Drafts are handled by the main build configuration (excluded by default unless `--drafts` is used).
:::

## Use Cases

### 1. Client-Side Search

Fetch the site index to implement fast, client-side search without a backend.

```html
<!-- Simple search UI -->
<input type="text" id="search-input" placeholder="Search...">
<ul id="search-results"></ul>

<script>
  const searchInput = document.getElementById('search-input');
  const resultsList = document.getElementById('search-results');
  let searchIndex = [];

  // Fetch index once
  fetch('/index.json')
    .then(response => response.json())
    .then(data => {
      searchIndex = data.pages;
    });

  // Filter and display results
  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase();
    if (query.length < 2) {
      resultsList.innerHTML = '';
      return;
    }

    const results = searchIndex.filter(page => 
      (page.title && page.title.toLowerCase().includes(query)) || 
      (page.excerpt && page.excerpt.toLowerCase().includes(query))
    ).slice(0, 10); // Limit to 10 results

    resultsList.innerHTML = results.map(page => `
      <li>
        <a href="${page.url}">
          <strong>${page.title}</strong>
          <p>${page.excerpt}</p>
        </a>
      </li>
    `).join('');
  });
</script>
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

