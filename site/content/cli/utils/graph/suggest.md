
---
title: "suggest"
type: cli-command
css_class: api-content
description: "💡 Generate smart link suggestions to improve internal linking.  Analyzes your content to recommend links based on: - Topic similarity (shared tags/categories) - Page importance ..."
source_file: "bengal/bengal/cli/commands/graph/suggest.py"
source_line: 12
---

# suggest

💡 Generate smart link suggestions to improve internal linking.

Analyzes your content to recommend links based on:
- Topic similarity (shared tags/categories)
- Page importance (PageRank scores)
- Navigation value (bridge pages)
- Link gaps (underlinked content)

Use link suggestions to:
- Improve internal linking structure
- Boost SEO through better connectivity
- Increase content discoverability
- Fill navigation gaps


## Usage

```bash
bengal utils graph suggest [ARGUMENTS] [OPTIONS]
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

### --min-score, -s

Minimum score threshold (default: 0.3)

**Type:** `float`
**Default:** `0.3`

### --top-n, -n

Number of suggestions to show (default: 50)

**Type:** `integer`
**Default:** `50`



## Examples

```bash
# Show top 50 link suggestions
bengal suggest
# Show only high-confidence suggestions
bengal suggest --min-score 0.5
# Export as JSON
bengal suggest --format json > suggestions.json
# Generate markdown checklist
bengal suggest --format markdown > TODO.md
```



## Help

```bash
bengal utils graph suggest --help
```
