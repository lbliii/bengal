
---
title: "linkcheck"
type: cli-reference
css_class: api-content
description: "Check internal and external links in the site.  Validates that all links in your site work correctly: - Internal links point to existing pages and anchors - External links retur..."
source_file: "bengal/bengal/cli/commands/health.py"
source_line: 27
---

# linkcheck

Check internal and external links in the site.

Validates that all links in your site work correctly:
- Internal links point to existing pages and anchors
- External links return successful HTTP status codes


## Usage

```bash
bengal health linkcheck [OPTIONS]
```


## Options

````{dropdown} Options (12 total)
:open: false

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--exclude` |`text` | |URL pattern to exclude (repeatable, regex supported) |
| `--exclude-domain` |`text` | |Domain to exclude (repeatable, e.g., 'localhost') |
| `--external-only` |Flag |`False` |Only check external links (skip internal validation) |
| `--ignore-status` |`text` | |Status code or range to ignore (repeatable, e.g., '500-599', '403') |
| `--internal-only` |Flag |`False` |Only check internal links (skip external validation) |
| `--max-concurrency` |`integer` |`20` |Maximum concurrent HTTP requests |
| `--output` |`path` | |Output file (for JSON format) |
| `--format` |`choice` |`console` |Output format |
| `--per-host-limit` |`integer` |`4` |Maximum concurrent requests per host |
| `--retries` |`integer` |`2` |Number of retry attempts |
| `--retry-backoff` |`float` |`0.5` |Base backoff time for exponential backoff in seconds |
| `--timeout` |`float` |`10.0` |Request timeout in seconds |

````


## Examples

```bash
bengal health linkcheck
bengal health linkcheck --external-only
bengal health linkcheck --format json --output report.json
bengal health linkcheck --exclude "^/api/preview/" --ignore-status "500-599"
```



## Help

```bash
bengal health linkcheck --help
```
