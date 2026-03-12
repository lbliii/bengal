---
title: SEO & Discovery
nav_title: SEO
description: Use Bengal's built-in metadata, sitemap, feeds, social cards, content signals, and output formats to make sites easier to discover
weight: 35
icon: globe
tags:
- seo
- discovery
- sitemap
- rss
- social cards
- search
- content signals
keywords:
- python static site generator seo
- sitemap
- canonical url
- open graph
- social cards
- search index
- content signals
- ai training
- robots.txt
---

# SEO & Discovery

Bengal already ships with most of the technical building blocks needed for search and
discovery. The main work is using those features well and publishing pages that
match real search intent.

## What Bengal Supports

### Page Metadata

Bengal pages can carry structured front matter such as:

- `title`
- `description`
- `keywords`
- `canonical`
- `noindex`

The default theme uses those fields to render metadata such as descriptions, keyword
tags, canonical URLs, Open Graph tags, Twitter cards, and robots directives.

See [SEO Functions](../reference/template-functions/seo-image-functions/) for the
template helpers that power these tags.

### Search Engine Discovery

Bengal's post-processing pipeline includes:

- XML sitemap generation for search engines
- RSS feeds for blog-style content
- Generated special pages such as `404`
- Generated `robots.txt` with [Content Signals](https://contentsignals.org/) directives
- Version-aware canonical URLs for versioned documentation
- `.well-known/content-signals.json` machine-readable policy manifest

These features help avoid duplicate-content problems, give search engines a clean map
of your site, and let you control how AI systems use your content.

### Social Sharing

Bengal supports social sharing metadata through:

- Open Graph URL and description tags
- Open Graph image support
- Auto-generated social cards
- Twitter card metadata in the default theme

For projects that rely on docs links shared in Slack, Discord, X, or GitHub,
social cards are one of the highest-leverage discovery features after page titles and
descriptions.

### On-Site Discovery

Bengal also improves discovery inside the site itself:

- Client-side search indexes
- Pre-built Lunr search indexes
- Related-content patterns through tags and template queries
- Broken-link detection and health checks
- Content analysis for orphan pages and internal-link quality

These do not directly rank pages, but they make sites easier to navigate, which often
leads to better content structure and clearer internal linking.

### Machine Discovery

Bengal can generate machine-friendly output formats such as:

- Per-page `index.json` (with optional heading-level chunks for RAG)
- Site-wide `index.json`
- `search-index.json`
- `llm-full.txt` — full plain-text corpus of all pages
- `llms.txt` — curated site overview per the [llms.txt spec](https://llmstxt.org/)
- `changelog.json` — per-build diff of added, modified, and removed pages
- `agent.json` — hierarchical site structure for agent discovery

See [Output Formats](./output-formats.md) for configuration details.

`llms.txt` is a short Markdown table of contents that tells AI agents what the site
is and where to find things. It is auto-generated from the site's section hierarchy
and page descriptions. Unlike `llm-full.txt` (a full content dump), `llms.txt` is
a lightweight navigation aid — typically under 100 lines.

Per-page JSON includes structured navigation, freshness data, and optional heading-level chunks for AI agents:

```json
{
  "url": "/docs/getting-started/installation/",
  "title": "Installation",
  "navigation": {
    "parent": "/docs/getting-started/",
    "prev": "/docs/getting-started/quickstart/",
    "next": "/docs/getting-started/configuration/",
    "related": ["/docs/building/deployment/"]
  },
  "last_modified": "2026-03-10T14:30:00",
  "content_hash": "a1b2c3...",
  "chunks": [
    {"anchor": "prerequisites", "title": "Prerequisites", "level": 2, "content": "...", "content_hash": "..."},
    {"anchor": "steps", "title": "Steps", "level": 2, "content": "...", "content_hash": "..."}
  ]
}
```

- `navigation` lets agents traverse docs without parsing HTML nav elements
- `last_modified` comes from frontmatter (`lastmod`, `last_modified`, `updated`) or file mtime
- `content_hash` is a SHA-256 of the plain text, so RAG pipelines know when to re-index
- `chunks` (when enabled) splits content by headings for finer-grained RAG retrieval

These outputs help with search, internal tooling, and AI consumption without adding a
backend.

#### Connect to IDE (Cursor MCP)

Bengal can show a "Connect to IDE" button that opens Cursor and adds your docs as an
MCP server via a one-click install. Requires a hosted Streamable HTTP MCP server —
Bengal generates the button; you provide the server. See [Connect to IDE](./connect-to-ide.md) for setup.

### Content Signals

Bengal generates a `robots.txt` with [Content Signals](https://contentsignals.org/)
directives that declare how automated systems may use your content. Three signals
are supported:

| Signal     | Default | Meaning                                    |
| ---------- | ------- | ------------------------------------------ |
| `search`   | `true`  | Allow search engine indexing                |
| `ai_input` | `true`  | Allow AI input (RAG, grounding, AI answers) |
| `ai_train` | `false` | Allow AI model training and fine-tuning     |

The default posture is **privacy-first**: content is discoverable and citable by AI
systems, but not available for training. Users opt in to `ai_train`.

#### Site-Wide Configuration

Set defaults in `bengal.toml`:

```toml
[content_signals]
search = true
ai_input = true
ai_train = false  # opt-in for training

# Target specific crawlers
[content_signals.user_agents.GPTBot]
ai_train = false
ai_input = true
```

#### Per-Page and Per-Section Control

Override signals using the `visibility` frontmatter. These values cascade through
sections via `_index.md`:

```yaml
# Per page
---
visibility:
  ai_train: false
  ai_input: true
---

# Section cascade (docs/_index.md) — all children inherit
---
cascade:
  visibility:
    ai_train: true
---
```

#### Disabling Content Signals

To skip `robots.txt` and manifest generation entirely:

```toml
[content_signals]
enabled = false
```

#### Enforcement

Content Signals are not just advisory. Bengal **enforces** them at the output format
level:

- Pages with `ai_input: false` do not get `page.json` or `page.txt` generated
- Pages with `ai_train: false` are excluded from `llm-full.txt`
- Pages with `search: false` are excluded from `index.json`
- Draft pages are excluded from all machine-readable outputs regardless of visibility

The format simply does not exist on disk for denied or draft pages.

#### Generated Files

| File                                 | Purpose                                                              |
| ------------------------------------ | -------------------------------------------------------------------- |
| `robots.txt`                         | Content-Signal directives per the [spec](https://contentsignals.org/) |
| `.well-known/content-signals.json`   | Machine-readable policy manifest for AI discovery                    |
| `llms.txt`                           | Curated site overview for AI agents per [llmstxt.org](https://llmstxt.org/) |
| `changelog.json`                     | Per-build diff of added, modified, removed pages (for incremental indexing) |
| `agent.json`                         | Hierarchical site structure and available formats (for agent discovery) |

The meta tags `content-signal:ai-train` and `content-signal:ai-input` are also
emitted in the HTML `<head>` when a page restricts any signal.

## Practical Strategy

If you want Bengal sites to rank and convert better, focus on this order:

1. Write pages that match real search intent: installation, quickstart, tutorials, migration guides, troubleshooting, and comparisons.
2. Give every important page a clear `title` and `description`.
3. Use tags, categories, and internal links so related pages reinforce each other.
4. Configure `baseurl` so canonical URLs and metadata resolve to the right domain.
5. Enable social cards for content people are likely to share publicly.
6. Publish feeds, sitemap, and search indexes as part of normal builds.
7. Review your content signals policy — decide which sections allow AI training.

## Recommended Page Types

Bengal works well when a project publishes some mix of:

- `Install <project>`
- `<project> quickstart`
- `<project> tutorial`
- `<project> vs <alternative>`
- `Migrate from <other tool>`
- `<project> troubleshooting`

Those titles line up with how Python developers search for libraries.

## Example Front Matter

```yaml
---
title: Build a Documentation Site with Bengal
description: Create a Python-powered documentation site with search, sitemap, RSS, and social sharing metadata.
keywords:
  - python static site generator
  - documentation site generator
  - bengal
canonical: https://example.com/docs/build-a-documentation-site/
visibility:
  ai_train: true  # allow training on this page
---
```

## Content Over Tricks

The technical side of SEO in Bengal is already strong. The bigger opportunity is
publishing better discovery pages:

- sharper README copy
- better docs landing pages
- migration guides
- comparison pages
- tutorial pages for concrete workflows

That is where many of the biggest gains come from.
