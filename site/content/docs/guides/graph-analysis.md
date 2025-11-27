---
title: Graph Analysis Guide
description: Learn how to analyze your site's structure, improve internal linking, and optimize navigation using Bengal's graph analysis tools
weight: 50
type: doc
draft: false
lang: en
tags: [guides, analysis, graph-analysis, seo, optimization]
keywords: [graph analysis, PageRank, community detection, link suggestions, site structure, internal linking, SEO]
category: guides
---

# Graph Analysis Guide

Bengal's graph analysis tools help you understand your site's structure, identify optimization opportunities, and improve internal linking. This guide shows you how to use these powerful features.

## Overview

Graph analysis examines how your pages connect through:
- **Internal links** - Cross-references between pages
- **Taxonomies** - Tags and categories that group related content
- **Navigation menus** - Menu items that reference pages
- **Related posts** - Pre-computed relationships

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

### 1. Analyze Site Structure

Get an overview of your site's connectivity:

```bash
bengal utils graph analyze site/
```

**Options**:
- `--tree`: Show site structure as a tree visualization
- `--output path/to/graph.html`: Generate interactive HTML visualization

**Example Output**:
```
📊 Knowledge Graph Statistics
Total pages:        82
Total links:        79
Average links:      2.0 per page

Connectivity Distribution:
  Hubs (>10 refs):  1 pages (1.2%)
  Mid-tier (3-10):  23 pages (28.0%)
  Leaves (≤2):    58 pages (70.7%)

🎯 Actionable Recommendations:
  🔗 Link 48 orphaned pages. Start with: Release 0.1.1, Release 0.1.2...
  📊 Low link density (2.0 links/page). Consider adding more internal links...
  🌉 Top bridge pages: Start Writing, Documentation, Guides...
```

### 2. PageRank Analysis

Identify your most important pages using Google's PageRank algorithm:

```bash
bengal utils graph pagerank site/ --top-n 20
```

**Options**:
- `--top-n N`: Show top N pages (default: 20)
- `--damping FLOAT`: PageRank damping factor (default: 0.85)
- `--format FORMAT`: Output format - `table`, `json`, `csv`, or `summary`

**Use Cases**:
- Prioritize content updates
- Guide navigation design
- Find underlinked valuable content
- Identify pages that should pass more link equity

**Example**:
```bash
# Export as CSV for analysis
bengal utils graph pagerank site/ --top-n 50 --format csv > pagerank.csv
```

### 3. Community Detection

Discover topical clusters in your content:

```bash
bengal utils graph communities site/ --top-n 10 --min-size 3
```

**Options**:
- `--min-size N`: Minimum community size to show (default: 2)
- `--resolution FLOAT`: Resolution parameter - higher = more communities (default: 1.0)
- `--top-n N`: Number of communities to show (default: 10)
- `--format FORMAT`: Output format - `table`, `json`, `csv`, or `summary`

**Use Cases**:
- Discover hidden content structure
- Organize content into logical groups
- Guide taxonomy creation
- Identify topic clusters

**Example**:
```bash
# Find large communities
bengal utils graph communities site/ --min-size 10 --format csv > communities.csv
```

### 4. Bridge Pages Analysis

Find critical navigation pages:

```bash
bengal utils graph bridges site/ --top-n 20
```

**Options**:
- `--top-n N`: Number of pages to show (default: 20)
- `--metric METRIC`: Focus on `betweenness`, `closeness`, or `both` (default: both)
- `--format FORMAT`: Output format - `table`, `json`, `csv`, or `summary`

**Metrics**:
- **Betweenness**: Pages that connect different parts of the site (bridge pages)
- **Closeness**: Pages easy to reach from anywhere (accessible pages)

**Use Cases**:
- Optimize navigation structure
- Identify critical pages
- Improve content discoverability
- Find navigation gaps

**Example**:
```bash
# Find most accessible pages
bengal utils graph bridges site/ --metric closeness --top-n 10
```

### 5. Link Suggestions

Get smart recommendations for internal linking:

```bash
bengal utils graph suggest site/ --top-n 50 --min-score 0.5
```

**Options**:
- `--top-n N`: Number of suggestions to show (default: 50)
- `--min-score FLOAT`: Minimum score threshold (default: 0.3)
- `--format FORMAT`: Output format - `table`, `json`, or `markdown`

**Scoring Factors**:
- Topic similarity (shared tags/categories)
- PageRank importance
- Navigation value (bridge pages)
- Link gaps (underlinked content)

**Use Cases**:
- Improve internal linking structure
- Boost SEO through better connectivity
- Increase content discoverability
- Fill navigation gaps

**Example**:
```bash
# Generate markdown checklist
bengal utils graph suggest site/ --format markdown > link-suggestions.md
```

## Common Workflows

### Improving Internal Linking

1. **Find orphaned pages**:
   ```bash
   bengal utils graph analyze site/
   ```
   Look for orphaned pages in the output.

2. **Get link suggestions**:
   ```bash
   bengal utils graph suggest site/ --min-score 0.5 --format markdown > suggestions.md
   ```

3. **Prioritize by importance**:
   ```bash
   bengal utils graph pagerank site/ --top-n 30 --format csv > important-pages.csv
   ```
   Focus on linking to high PageRank pages.

4. **Review and implement**:
   - Start with high-score suggestions
   - Link orphaned pages to related content
   - Add links to high PageRank pages

### Optimizing Navigation

1. **Find bridge pages**:
   ```bash
   bengal utils graph bridges site/ --metric betweenness --top-n 10
   ```

2. **Ensure bridge pages are prominent**:
   - Add to main navigation menus
   - Link from index pages
   - Include in breadcrumbs

3. **Check accessibility**:
   ```bash
   bengal utils graph bridges site/ --metric closeness --top-n 10
   ```
   Ensure important pages are easily accessible.

### Content Organization

1. **Discover communities**:
   ```bash
   bengal utils graph communities site/ --min-size 5
   ```

2. **Review community structure**:
   - Do communities match your content organization?
   - Should you create index pages for large communities?
   - Are there unexpected relationships?

3. **Create navigation**:
   - Add index pages for large communities
   - Link related pages within communities
   - Create taxonomy pages for topic clusters

## Export Formats

All commands support multiple export formats:

### CSV Export

Perfect for spreadsheet analysis:

```bash
bengal utils graph pagerank site/ --format csv > pagerank.csv
bengal utils graph communities site/ --format csv > communities.csv
bengal utils graph bridges site/ --format csv > bridges.csv
```

### JSON Export

For programmatic processing:

```bash
bengal utils graph pagerank site/ --format json > pagerank.json
```

### Markdown Export

For link suggestions checklist:

```bash
bengal utils graph suggest site/ --format markdown > suggestions.md
```

## Visualization

Generate an interactive graph visualization:

```bash
bengal utils graph analyze site/ --output public/graph.html
```

Open `public/graph.html` in your browser to explore:
- Force-directed graph layout
- Node sizing by connectivity
- Node coloring by type/connectivity
- Interactive exploration

## Understanding Recommendations

The `analyze` command provides actionable recommendations:

### 🔗 Orphaned Pages

Pages with no incoming or outgoing links. These are often:
- Forgotten content
- Draft pages
- Pages that should be in navigation

**Action**: Add links from related pages or navigation menus.

### ⭐ Underlinked Valuable Content

High PageRank pages that aren't well-linked. These are important but hard to discover.

**Action**: Add links from related content and navigation.

### 📊 Link Density

Average links per page. Low density (<2) hurts SEO and discoverability.

**Action**: Add more internal links between related content.

### 🌉 Bridge Pages

Pages that connect different parts of your site. Critical for navigation.

**Action**: Ensure these pages are prominent in menus and linked from index pages.

### 🏆 Hub Pages

Pages with many incoming links. Your most important content.

**Action**: Keep these pages updated and well-maintained.

### ⚡ Performance Opportunities

High percentage of leaf pages indicates good performance potential.

**Action**: Consider lazy-loading leaf pages to reduce memory usage.

## Best Practices

### Regular Analysis

Run analysis regularly to track improvements:

```bash
# Save results for comparison
bengal utils graph analyze site/ > analysis-$(date +%Y%m%d).txt
bengal utils graph pagerank site/ --format csv > pagerank-$(date +%Y%m%d).csv
```

### Focus on High-Impact Changes

1. **Start with orphaned pages** - Easy wins
2. **Link to high PageRank pages** - Maximum SEO benefit
3. **Improve bridge pages** - Better navigation
4. **Add internal links gradually** - Don't over-link

### Use Multiple Metrics

Combine insights from different commands:
- PageRank shows importance
- Communities show topic structure
- Bridges show navigation patterns
- Suggestions show specific opportunities

## Troubleshooting

### No Links Detected

If analysis shows 0 links:
- Ensure pages have internal links in markdown (`[text](/path/)`)
- Check that links use correct paths
- Verify pages are in the same site

### Too Many Orphaned Pages

If you have many orphaned pages:
- Add navigation menus
- Create index pages for sections
- Link related content together
- Use the `suggest` command for ideas

### Low Link Density

If average links per page is low (<2):
- Add "Related Content" sections
- Link from index pages
- Cross-reference related topics
- Use tags/categories to find related content

## Advanced Usage

### Excluding Autodoc Pages

By default, API reference pages are excluded from analysis. To include them:

```python
from bengal.analysis import KnowledgeGraph

graph = KnowledgeGraph(site, exclude_autodoc=False)
graph.build()
```

### Custom Thresholds

Adjust hub/leaf thresholds:

```python
graph = KnowledgeGraph(site, hub_threshold=15, leaf_threshold=3)
```

### Programmatic Access

Use the analysis system in Python:

```python
from bengal.analysis import KnowledgeGraph
from bengal.core.site import Site

site = Site.from_config(Path("site"))
graph = KnowledgeGraph(site)
graph.build()

# Get recommendations
recommendations = graph.get_actionable_recommendations()
for rec in recommendations:
    print(rec)

# Get top pages by PageRank
results = graph.compute_pagerank()
top_pages = results.get_top_pages(10)
for page, score in top_pages:
    print(f"{page.title}: {score:.6f}")
```

## Related Documentation

- [Analysis System Reference](/docs/reference/architecture/subsystems/analysis/) - Technical API documentation
- [CLI Graph Commands](/cli/utils/graph/) - Complete CLI reference
- [Content Workflow Guide](/docs/guides/content-workflow/) - Content organization best practices
