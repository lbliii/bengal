---
title: Output Formats
nav_title: Output Formats
description: Generate JSON, LLM-ready text, and other output formats for search and AI discovery
weight: 40
---

# Output Formats

Bengal can generate multiple output formats for your content, enabling search functionality, AI discovery, and programmatic access.

## Available Formats

### Per-Page Formats

Generated for every page in your site:

- **JSON** (`index.json`): Structured data including metadata, HTML content, and plain text.
- **LLM Text** (`index.txt`): AI-friendly plain text format optimized for **RAG** (Retrieval-Augmented Generation) and LLM consumption.

### Site-Wide Formats

Generated at the site root:

- **Site Index** (`index.json`): A searchable index of all pages (useful for client-side search).
- **Full LLM Text** (`llm-full.txt`): The complete content of your site in a single plain text file.

## Configuration

Enable output formats in your config file.

:::{tab-set}
:::{tab-item} YAML (directory config)

```yaml
# config/_default/outputs.yaml
output_formats:
  enabled: true
  per_page: ["json"]
  site_wide: ["index_json"]
  options:
    excerpt_length: 200                    # Excerpt length for site index
    json_indent: null                      # null for compact JSON, 2 for pretty-print
    llm_separator_width: 80                # Width of LLM text separators
    include_full_content_in_index: false   # Include full content in site index
    exclude_sections: []                   # Sections to exclude from output formats
    exclude_patterns: ["404.html", "search.html"]  # Files to exclude
```

:::
:::{tab-item} TOML (single file)

```toml
# bengal.toml
[output_formats]
enabled = true
per_page = ["json"]
site_wide = ["index_json"]

[output_formats.options]
excerpt_length = 200
json_indent = null
llm_separator_width = 80
include_full_content_in_index = false
exclude_sections = []
exclude_patterns = ["404.html", "search.html"]
```

:::
:::{/tab-set}

:::{tip}
**Effective Defaults**: The `[features]` section controls which formats are enabled. With default features (`json = true`, `llm_txt = true`), Bengal generates:

- **per_page**: `["json", "llm_txt"]` (both JSON and LLM text)
- **site_wide**: `["index_json", "llm_full"]` (search index and full LLM text)

To disable LLM text generation, set `features.llm_txt = false` in your config.
:::

:::{note}
**Visibility**: Output formats respect page visibility settings. Hidden pages and drafts are excluded by default. Use `exclude_sections` or `exclude_patterns` for additional filtering.
:::

## Use Cases

### Client-Side Search

Fetch the site index to implement fast, client-side search without a backend.

:::{note}
For larger sites, enable the **Pre-built Lunr Index** to improve performance. This requires the `search` optional dependency:

```bash
pip install "bengal[search]"
```

This generates `search-index.json` (a pre-serialized Lunr index) in addition to `index.json`, which loads faster in the browser.
:::

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
    ).slice(0, 10);

    resultsList.innerHTML = results.map(page => `
      <li>
        <a href="${page.href}">
          <strong>${page.title}</strong>
          <p>${page.excerpt}</p>
        </a>
      </li>
    `).join('');
  });
</script>
```

### AI & LLM Discovery

Provide `llm-full.txt` to LLMs to allow them to ingest your entire documentation site efficiently.

```bash
curl https://mysite.com/llm-full.txt
```

### Static API

Use your static site as a read-only API for other applications.

```python
import requests

# Get page data
data = requests.get('https://mysite.com/docs/intro/index.json').json()
print(data['title'])
print(data['word_count'])
```
