
---
title: "diff"
type: doc
description: "🔍 Compare configurations.  Shows differences between two configurations (environments, profiles, or files)."
source_file: "bengal/bengal/cli/commands/config.py"
source_line: 333
---

🔍 Compare configurations.

Shows differences between two configurations (environments, profiles, or files).


## Usage

```bash
bengal config diff [ARGUMENTS] [OPTIONS]
```

## Arguments

### source

**Type:** `path`
**Required:** No
**Default:** `.`


## Options

### --against

Environment or file to compare against

**Type:** `text`
**Required:** Yes

### --environment, -e

Environment to compare (default: local)

**Type:** `text`



## Examples

```bash
bengal config diff --against production
bengal config diff --environment local --against production
```



## Help

```bash
bengal config diff --help
```
