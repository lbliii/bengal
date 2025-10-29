
---
title: "doctor"
type: doc
description: "🩺 Validate and lint configuration.  Checks for: - Valid YAML syntax - Type errors (bool, int, str) - Unknown keys (typo detection) - Required fields - Value ranges - Deprecated keys"
source_file: "bengal/bengal/cli/commands/config.py"
source_line: 154
---

🩺 Validate and lint configuration.

Checks for:
- Valid YAML syntax
- Type errors (bool, int, str)
- Unknown keys (typo detection)
- Required fields
- Value ranges
- Deprecated keys


## Usage

```bash
bengal config doctor [ARGUMENTS] [OPTIONS]
```

## Arguments

### source

**Type:** `path`
**Required:** No
**Default:** `.`


## Options

### --environment, -e

Environment to validate (default: all)

**Type:** `text`



## Examples

```bash
bengal config doctor
bengal config doctor --environment production
```



## Help

```bash
bengal config doctor --help
```