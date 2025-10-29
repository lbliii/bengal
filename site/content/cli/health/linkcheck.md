
---
title: "linkcheck"
type: doc
description: "Check internal and external links in the site.  Validates that all links in your site work correctly: - Internal links point to existing pages and anchors - External links retur..."
source_file: "bengal/bengal/cli/commands/health.py"
source_line: 33
---

Check internal and external links in the site.

Validates that all links in your site work correctly:
- Internal links point to existing pages and anchors
- External links return successful HTTP status codes


## Usage

```bash
bengal health linkcheck [OPTIONS]
```


## Options

````{dropdown} Options (13 total)
:open: false

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--exclude` |`text` |- |URL pattern to exclude (repeatable, regex supported) |
| `--exclude-domain` |`text` |- |Domain to exclude (repeatable, e.g., 'localhost') |
| `--external-only` |Flag |`False` |Only check external links (skip internal validation) |
| `--ignore-status` |`text` |- |Status code or range to ignore (repeatable, e.g., '500-599', '403') |
| `--internal-only` |Flag |`False` |Only check internal links (skip external validation) |
| `--max-concurrency` |`integer` |- |Maximum concurrent HTTP requests (default: 20) |
| `--output` |`path` |- |Output file (for JSON format) |
| `--format` |`choice` |`console` |Output format |
| `--per-host-limit` |`integer` |- |Maximum concurrent requests per host (default: 4) |
| `--retries` |`integer` |- |Number of retry attempts (default: 2) |
| `--retry-backoff` |`float` |- |Base backoff time for exponential backoff in seconds (default: 0.5) |
| `--timeout` |`float` |- |Request timeout in seconds (default: 10.0) |
| `--traceback` |`choice` |- |Traceback verbosity: full | compact | minimal | off |

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