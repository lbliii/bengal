
---
title: "config"
type: doc
description: "⚙️  Manage Bengal configuration."
source_file: "bengal/bengal/cli/commands/project.py"
source_line: 343
---

⚙️  Manage Bengal configuration.


## Usage

```bash
bengal project config [ARGUMENTS] [OPTIONS]
```

## Arguments

### key

**Type:** `text`
**Required:** No

### value

**Type:** `text`
**Required:** No


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
