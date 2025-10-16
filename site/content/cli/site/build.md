
---
title: "build"
type: cli-command
css_class: api-content
description: "🔨 Build the static site.  Generates HTML files from your content, applies templates, processes assets, and outputs a production-ready site."
source_file: "bengal/bengal/cli/commands/build.py"
source_line: 168
---

# build

🔨 Build the static site.

Generates HTML files from your content, applies templates,
processes assets, and outputs a production-ready site.


## Usage

```bash
bengal site build [ARGUMENTS] [OPTIONS]
```

## Arguments

### source

**Type:** `path`
**Required:** No
**Default:** `.`


## Options

````{dropdown} Options (18 total)
:open: false

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--assets-pipeline` |Flag |- |Enable/disable Node-based assets pipeline (overrides config) |
| `--autodoc` |Flag |- |Force regenerate autodoc before building (overrides config) |
| `--config` |`path` |`Sentinel.UNSET` |Path to config file (default: bengal.toml) |
| `--debug` |Flag |`False` |Show debug output and full tracebacks (maps to dev profile) |
| `--fast` |Flag |- |Fast mode: quiet output, guaranteed parallel, max speed (overrides config) |
| `--full-output` |Flag |`False` |Show full traditional output instead of live progress (useful for debugging) |
| `--incremental` |Flag |- |Incremental mode: auto when omitted (uses cache if present). |
| `--log-file` |`path` |`Sentinel.UNSET` |Write detailed logs to file (default: .bengal-build.log) |
| `--memory-optimized` |Flag |`False` |Use streaming build for memory efficiency (best for 5K+ pages) |
| `--parallel` |Flag |`True` |Enable parallel processing for faster builds (default: enabled) |
| `--perf-profile` |`path` |`Sentinel.UNSET` |Enable performance profiling and save to file (default: .bengal/profiles/profile.stats) |
| `--profile` |`choice` |`Sentinel.UNSET` |Build profile: writer (fast/clean), theme-dev (templates), dev (full debug) |
| `--quiet`, `-q` |Flag |`False` |Minimal output - only show errors and summary |
| `--strict` |Flag |`False` |Fail on template errors (recommended for CI/CD) |
| `--dev` |Flag |`False` |Use developer profile with full observability (shorthand for --profile dev) |
| `--theme-dev` |Flag |`False` |Use theme developer profile (shorthand for --profile theme-dev) |
| `--validate` |Flag |`False` |Validate templates before building (catch errors early) |
| `--verbose`, `-v` |Flag |`False` |Show detailed build information (maps to theme-dev profile) |

````




## Help

```bash
bengal site build --help
```