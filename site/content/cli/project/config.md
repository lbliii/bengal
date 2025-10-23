
---
title: "config"
type: cli-reference
css_class: api-content
description: "⚙️  Manage Bengal configuration."
source_file: "bengal/bengal/cli/commands/project.py"
source_line: 346
---

# config

⚙️  Manage Bengal configuration.


## Usage

```bash
bengal project config [ARGUMENTS] [OPTIONS]
```

## Arguments

### key

**Type:** `text`
**Required:** No
**Default:** `Sentinel.UNSET`

### value

**Type:** `text`
**Required:** No
**Default:** `Sentinel.UNSET`


## Options

### --list

List all configuration options

**Type:** Flag (boolean)
**Default:** `False`

### --set

Set a configuration value

**Type:** Flag (boolean)
**Default:** `False`



## Examples

```bash
bengal project config                    # Show current config
bengal project config site.title         # Get specific value
bengal project config site.title "My Blog" --set  # Set value
bengal project config --list             # List all options
```



## Help

```bash
bengal project config --help
```