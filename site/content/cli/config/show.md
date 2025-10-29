
---
title: "show"
type: doc
description: "📋 Display merged configuration.  Shows the effective configuration after merging defaults, environment, and profile settings."
source_file: "bengal/bengal/cli/commands/config.py"
source_line: 39
---

📋 Display merged configuration.

Shows the effective configuration after merging defaults, environment,
and profile settings.


## Usage

```bash
bengal config show [ARGUMENTS] [OPTIONS]
```

## Arguments

### source

**Type:** `path`
**Required:** No
**Default:** `.`


## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--environment`, `-e` |`text` |- |Environment to load (auto-detected if not specified) |
| `--format` |`choice` |`yaml` |Output format |
| `--origin` |Flag |`False` |Show which file contributed each config key |
| `--profile`, `-p` |`text` |- |Profile to load (optional) |
| `--section`, `-s` |`text` |- |Show only specific section (e.g., 'site', 'build') |


## Examples

```bash
bengal config show
bengal config show --environment production
bengal config show --profile dev --origin
bengal config show --section site
```



## Help

```bash
bengal config show --help
```