---
title: SEO & Discovery
nav_title: SEO
description: Use Bengal's built-in metadata, sitemap, feeds, social cards, and output formats to make sites easier to discover
weight: 35
icon: globe
tags:
- seo
- discovery
- sitemap
- rss
- social cards
- search
keywords:
- python static site generator seo
- sitemap
- canonical url
- open graph
- social cards
- search index
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
- Generated special pages such as `404` and `robots.txt`
- Version-aware canonical URLs for versioned documentation

These features help avoid duplicate-content problems and give search engines a clean map
of your site.

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

- Per-page `index.json`
- Site-wide `index.json`
- `search-index.json`
- `llm-full.txt`

See [Output Formats](./output-formats.md) for configuration details.

These outputs help with search, internal tooling, and AI consumption without adding a
backend.

## Practical Strategy

If you want Bengal sites to rank and convert better, focus on this order:

1. Write pages that match real search intent: installation, quickstart, tutorials, migration guides, troubleshooting, and comparisons.
2. Give every important page a clear `title` and `description`.
3. Use tags, categories, and internal links so related pages reinforce each other.
4. Configure `baseurl` so canonical URLs and metadata resolve to the right domain.
5. Enable social cards for content people are likely to share publicly.
6. Publish feeds, sitemap, and search indexes as part of normal builds.

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
