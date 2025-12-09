---
title: Graph Analysis
description: Analyze your site's structure, improve internal linking, and optimize
  navigation
weight: 10
draft: false
lang: en
tags:
- analysis
- graph
- seo
- optimization
keywords:
- graph analysis
- pagerank
- community detection
- link suggestions
- seo
category: guide
---

# Graph Analysis

Bengal's graph analysis tools help you understand your site's structure, identify optimization opportunities, and improve internal linking.

## Overview

Graph analysis examines how your pages connect through:
- **Internal links** — Cross-references between pages
- **Taxonomies** — Tags and categories that group related content
- **Navigation menus** — Menu items that reference pages
- **Related posts** — Pre-computed relationships

This analysis helps you:
- Find orphaned pages that need links
- Identify your most important content (PageRank)
- Discover topical communities
- Find navigation bottlenecks
- Get smart link suggestions

## Quick Start

Start with a basic analysis of your site:

```bash
bengal utils graph analyze site/
```

This shows:
- Total pages and links
- Connectivity distribution (hubs, mid-tier, leaves)
- Top hub pages
- Orphaned pages
- **Actionable recommendations** for improvement

## Understanding the Analysis

### Connectivity Types

Bengal categorizes pages by connectivity:

- **Hubs** (>10 incoming links): Highly connected pages, often index pages or popular content
- **Mid-tier** (3-10 links): Moderately connected pages
- **Leaves** (≤2 links): Low connectivity pages, often one-off content

### Key Metrics

- **Total links**: Number of connections between pages
- **Average links**: Links per page (aim for 2-5 for good SEO)
- **Orphaned pages**: Pages with no incoming or outgoing links
- **Hub pages**: Pages with many incoming links (important for navigation)

## Command Reference

### Analyze Site Structure

Get an overview of your site's connectivity:

```bash
bengal utils graph analyze site/
```

**Options**:
- `--tree`: Show site structure as a tree visualization
- `--output path/to/graph.html`: Generate interactive HTML visualization

### PageRank Analysis

Identify your most important pages using Google's PageRank algorithm:

```bash
bengal utils graph pagerank site/ --top-n 20
```

**Options**:
- `--top-n N`: Show top N pages (default: 20)
- `--damping FLOAT`: PageRank damping factor (default: 0.85)
- `--format FORMAT`: Output format - `table`, `json`, `csv`, or `summary`

### Community Detection

Discover topical clusters in your content:

```bash
bengal utils graph communities site/ --top-n 10 --min-size 3
```

**Options**:
- `--min-size N`: Minimum community size to show (default: 2)
- `--resolution FLOAT`: Resolution parameter - higher = more communities (default: 1.0)
- `--top-n N`: Number of communities to show (default: 10)

### Bridge Pages Analysis

Find critical navigation pages:

```bash
bengal utils graph bridges site/ --top-n 20
```

**Metrics**:
- **Betweenness**: Pages that connect different parts of the site (bridge pages)
- **Closeness**: Pages easy to reach from anywhere (accessible pages)

### Link Suggestions

Get smart recommendations for internal linking:

```bash
bengal utils graph suggest site/ --top-n 50 --min-score 0.5
```

**Options**:
- `--top-n N`: Number of suggestions to show (default: 50)
- `--min-score FLOAT`: Minimum score threshold (default: 0.3)
- `--format FORMAT`: Output format - `table`, `json`, or `markdown`

## Common Workflows

### Improving Internal Linking

1. **Find orphaned pages**:
   ```bash
   bengal utils graph analyze site/
   ```

2. **Get link suggestions**:
   ```bash
   bengal utils graph suggest site/ --min-score 0.5 --format markdown > suggestions.md
   ```

3. **Prioritize by importance**:
   ```bash
   bengal utils graph pagerank site/ --top-n 30 --format csv > important-pages.csv
   ```

4. **Review and implement** — Start with high-score suggestions.

### Optimizing Navigation

1. **Find bridge pages**:
   ```bash
   bengal utils graph bridges site/ --metric betweenness --top-n 10
   ```

2. **Ensure bridge pages are prominent** — Add to main navigation menus.

3. **Check accessibility**:
   ```bash
   bengal utils graph bridges site/ --metric closeness --top-n 10
   ```

## Understanding Recommendations

The `analyze` command provides actionable recommendations:

| Recommendation | Meaning | Action |
|----------------|---------|--------|
| 🔗 Orphaned Pages | Pages with no links | Add links from related pages |
| ⭐ Underlinked Content | Important pages that aren't well-linked | Add links from navigation |
| 📊 Low Link Density | Average links < 2 per page | Add more internal links |
| 🌉 Bridge Pages | Pages connecting site sections | Make prominent in menus |
| 🏆 Hub Pages | Pages with many incoming links | Keep updated and maintained |

## Best Practices

### Regular Analysis

Run analysis regularly to track improvements:

```bash
# Save results for comparison
bengal utils graph analyze site/ > analysis-$(date +%Y%m%d).txt
bengal utils graph pagerank site/ --format csv > pagerank-$(date +%Y%m%d).csv
```

### Focus on High-Impact Changes

1. **Start with orphaned pages** — Easy wins
2. **Link to high PageRank pages** — Maximum SEO benefit
3. **Improve bridge pages** — Better navigation
4. **Add internal links gradually** — Don't over-link

## See Also

- [CLI Graph Commands](/cli/utils/graph/) — Complete CLI reference
- [Analysis API](/api/analysis/) — Programmatic access
