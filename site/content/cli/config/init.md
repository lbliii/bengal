
---
title: "init"
type: doc
description: "✨ Initialize configuration structure.  Creates config directory with examples, or a single config file."
source_file: "bengal/bengal/cli/commands/config.py"
source_line: 444
---

✨ Initialize configuration structure.

Creates config directory with examples, or a single config file.


## Usage

```bash
bengal config init [ARGUMENTS] [OPTIONS]
```

## Arguments

### source

**Type:** `path`
**Required:** No
**Default:** `.`


## Options

### --force

Overwrite existing config files

**Type:** Flag (boolean)
**Default:** `False`

### --type

Config structure type (default: directory)

**Type:** `choice`
**Default:** `directory`

### --template

Config template (default: docs)

**Type:** `choice`
**Default:** `docs`



## Examples

```bash
bengal config init
bengal config init --type file
bengal config init --template blog
```



## Help

```bash
bengal config init --help
```
