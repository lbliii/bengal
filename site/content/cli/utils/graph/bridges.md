
---
title: "bridges"
type: cli-reference
css_class: api-content
description: "🌉 Identify bridge pages and navigation bottlenecks.  Analyzes navigation paths to find: - Bridge pages (high betweenness): Pages that connect different parts of the site - Acces..."
source_file: "bengal/bengal/cli/commands/graph/bridges.py"
source_line: 12
---

# bridges

🌉 Identify bridge pages and navigation bottlenecks.

Analyzes navigation paths to find:
- Bridge pages (high betweenness): Pages that connect different parts of the site
- Accessible pages (high closeness): Pages easy to reach from anywhere
- Navigation bottlenecks: Critical pages for site navigation

Use path analysis to:
- Optimize navigation structure
- Identify critical pages
- Improve content discoverability
- Find navigation gaps


## Usage

```bash
bengal utils graph bridges [ARGUMENTS] [OPTIONS]
```

## Arguments

### source

**Type:** `path`
**Required:** No
**Default:** `.`


## Options

### --config

Path to config file (default: bengal.toml)

**Type:** `path`
**Default:** `Sentinel.UNSET`

### --format, -f

Output format (default: table)

**Type:** `choice`
**Default:** `table`

### --metric, -m

Centrality metric to display (default: both)

**Type:** `choice`
**Default:** `both`

### --top-n, -n

Number of pages to show (default: 20)

**Type:** `integer`
**Default:** `20`



## Examples

```bash
# Show top 20 bridge pages
bengal bridges
# Show most accessible pages
bengal bridges --metric closeness
# Show only betweenness centrality
bengal bridges --metric betweenness
# Export as JSON
bengal bridges --format json > bridges.json
```



## Help

```bash
bengal utils graph bridges --help
```