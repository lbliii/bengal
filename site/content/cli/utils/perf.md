
---
title: "perf"
type: cli-command
css_class: api-content
description: "Show performance metrics and trends.  Displays build performance metrics collected from previous builds. Metrics are automatically saved to .bengal-metrics/ directory."
source_file: "bengal/bengal/cli/commands/perf.py"
source_line: 6
---

# perf

Show performance metrics and trends.

Displays build performance metrics collected from previous builds.
Metrics are automatically saved to .bengal-metrics/ directory.


## Usage

```bash
bengal utils perf [OPTIONS]
```


## Options

### --compare, -c

Compare last two builds

**Type:** Flag (boolean)
**Default:** `False`

### --format, -f

Output format

**Type:** `choice`
**Default:** `table`

### --last, -n

Show last N builds (default: 10)

**Type:** `integer`
**Default:** `10`



## Examples

```bash
bengal perf              # Show last 10 builds as table
bengal perf -n 20        # Show last 20 builds
bengal perf -f summary   # Show summary of latest build
bengal perf -f json      # Output as JSON
bengal perf --compare    # Compare last two builds
```



## Help

```bash
bengal utils perf --help
```