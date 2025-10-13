
---
title: "cleanup"
type: cli-command
css_class: api-content
description: "🔧 Clean up stale Bengal server processes.  Finds and terminates any stale 'bengal serve' processes that may be holding ports or preventing new servers from starting.  This is us..."
---

# cleanup

🔧 Clean up stale Bengal server processes.

Finds and terminates any stale 'bengal serve' processes that may be
holding ports or preventing new servers from starting.

This is useful if a previous server didn't shut down cleanly.


## Usage

```bash
bengal cleanup [ARGUMENTS] [OPTIONS]
```

## Arguments

### source

**Type:** `path`
**Required:** No
**Default:** `.`


## Options

### --force, -f

Kill process without confirmation

**Type:** Flag (boolean)
**Default:** `False`

### --port, -p

Also check if process is using this port

**Type:** `integer`
**Default:** `Sentinel.UNSET`





## Help

```bash
bengal cleanup --help
```

---

*Source: /Users/llane/Documents/github/python/bengal/bengal/cli/commands/clean.py:79*
