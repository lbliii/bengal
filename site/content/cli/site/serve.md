
---
title: "serve"
type: doc
description: "🚀 Start development server with hot reload.  Watches for changes in content, assets, and templates, automatically rebuilding the site when files are modified."
source_file: "bengal/bengal/cli/commands/serve.py"
source_line: 17
---

🚀 Start development server with hot reload.

Watches for changes in content, assets, and templates,
automatically rebuilding the site when files are modified.


## Usage

```bash
bengal site serve [ARGUMENTS] [OPTIONS]
```

## Arguments

### source

**Type:** `path`
**Required:** No
**Default:** `.`


## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--auto-port` |Flag |`True` |Find available port if specified port is taken (default: enabled) |
| `--config` |`path` |- |Path to config file (default: bengal.toml) |
| `--debug` |Flag |`False` |Show debug output and full tracebacks (port checks, PID files, observer setup) |
| `--host` |`text` |`localhost` |Server host address |
| `--open`, `-o` |Flag |`False` |Open browser automatically after server starts |
| `--port`, `-p` |`integer` |`5173` |Server port number |
| `--verbose`, `-v` |Flag |`False` |Show detailed server activity (file watches, rebuilds, HTTP details) |
| `--watch` |Flag |`True` |Watch for file changes and rebuild (default: enabled) |




## Help

```bash
bengal site serve --help
```
