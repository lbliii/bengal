---
title: Build Profiles
nav_title: Profiles
description: Configure Bengal for different workflows with built-in profiles
weight: 10
type: doc
icon: user
tags:
- profiles
- configuration
- build
- workflow
keywords:
- build profile
- writer
- theme-dev
- developer
- configuration
- workflow
category: how-to
---
# Build Profiles

Bengal includes three built-in profiles optimized for different workflows:

| Profile | For | Focus |
|---------|-----|-------|
| **writer** | Content authors | Fast, clean builds |
| **theme-dev** | Theme builders | Template debugging |
| **dev** | Framework contributors | Full observability |

## Quick Start

```bash
# Content writing (default)
bengal build

# Theme development
bengal build --theme-dev

# Full debugging
bengal build --dev
```

---

## Profile Comparison

### Writer Profile (Default)

**Best for**: Content authors who want fast, clean builds without technical noise.

```bash
bengal build
# or explicitly:
bengal build --profile writer
```

**Features:**
- ✅ Fast builds with minimal output
- ✅ Content-focused health checks (links, directives)
- ✅ Live progress display
- ❌ No phase timing
- ❌ No memory tracking
- ❌ No debug output

**Health Checks Enabled:**
- `config` — Configuration validation
- `output` — Output file checks
- `links` — Link validation
- `directives` — MyST directive syntax

### Theme Developer Profile

**Best for**: Theme builders who need template debugging and rendering insights.

```bash
bengal build --theme-dev
# or:
bengal build --profile theme-dev
```

**Features:**
- ✅ Phase timing displayed
- ✅ Template-focused health checks
- ✅ Live progress with recent items (3 shown)
- ✅ Build metrics collected
- ✅ Verbose build stats
- ❌ No memory tracking

**Health Checks Enabled:**
- `config`, `output`, `links`, `directives`
- `rendering` — Template rendering errors
- `navigation` — Navigation structure
- `menu` — Menu validation

### Developer Profile

**Best for**: Framework contributors who need full observability.

```bash
bengal build --dev
# or:
bengal build --profile dev
# or:
bengal build --debug
```

**Features:**
- ✅ Phase timing displayed
- ✅ Memory tracking enabled
- ✅ Debug output enabled
- ✅ All metrics collected
- ✅ All health checks enabled
- ✅ Recent items shown (5)

**Health Checks Enabled:**
- All validators (config, output, links, directives, rendering, navigation, menu, performance, cache, taxonomy)

---

## Profile Settings Comparison

| Setting | Writer | Theme-Dev | Developer |
|---------|--------|-----------|-----------|
| Phase timing | ❌ | ✅ | ✅ |
| Memory tracking | ❌ | ❌ | ✅ |
| Debug output | ❌ | ❌ | ✅ |
| Metrics collection | ❌ | ✅ | ✅ |
| Verbose build stats | ❌ | ✅ | ✅ |
| Live progress | ✅ | ✅ | ✅ |
| Recent items shown | 0 | 3 | 5 |

---

## Command Reference

### Profile Flags

```bash
# Explicit profile selection
bengal build --profile writer
bengal build --profile theme-dev
bengal build --profile dev

# Shorthand flags
bengal build --theme-dev    # Same as --profile theme-dev
bengal build --dev          # Same as --profile dev
bengal build --debug        # Maps to --profile dev
```

### Profile Precedence

When multiple flags are provided, precedence (highest to lowest):
1. `--dev` flag
2. `--theme-dev` flag
3. `--profile` option
4. `--debug` flag
5. Default (writer)

### Profile + Other Options

Profiles can be combined with other build options:

```bash
# Theme development with verbose output
bengal build --theme-dev --verbose

# Developer mode with incremental builds
bengal build --dev --incremental

# Theme dev with template profiling
bengal build --theme-dev --profile-templates

# Fast mode overrides profile settings
bengal build --fast
```

### Verbose vs Profile

`--verbose` and profiles are independent:

| Flag | What It Does |
|------|--------------|
| `--verbose` | Controls output verbosity (show/hide details) |
| `--quiet` | Minimal output (errors and summary only) |
| `--profile` | Controls feature enablement (metrics, health checks) |

```bash
# Writer profile with verbose output (shows stats)
bengal build --verbose

# Dev profile with quiet output (hides stats)
bengal build --dev --quiet
```

---

## Use Cases

### Writing Content

```bash
# Fast, clean builds - default profile
bengal serve
```

The writer profile gives you:
- Minimal terminal noise
- Only content-related warnings
- Fast feedback loop

### Building a Theme

```bash
# Template-focused debugging
bengal serve --theme-dev
```

The theme-dev profile gives you:
- Template rendering errors highlighted
- Phase timing to identify slow templates
- Component preview with live reload

### Debugging a Problem

```bash
# Full observability
bengal build --dev --verbose
```

The dev profile gives you:
- All health checks running
- Memory tracking for leak detection
- Full debug output
- Metrics saved to `.bengal/metrics/`

---

## Profile Metrics

When metrics collection is enabled (theme-dev and dev profiles):

```
.bengal/
└── metrics/
    ├── build-2024-01-15-10-30-00.json
    ├── build-2024-01-15-10-35-00.json
    └── latest.json
```

**Metrics include:**
- Build duration per phase
- Pages rendered
- Assets processed
- Template render times
- Memory usage (dev profile only)

---

## Quick Reference

```bash
# Profiles
bengal build                     # Writer (default)
bengal build --theme-dev         # Theme developer
bengal build --dev               # Full developer

# Profile + options
bengal build --dev --verbose     # Dev with verbose output
bengal build --theme-dev --fast  # Theme dev with fast mode

# Override config
bengal build --profile writer    # Force writer profile
```

---

:::{seealso}
- [[docs/building/commands|Build Commands]]
- [[docs/building/configuration|Configuration Reference]]
- [[docs/content/validation|Validation and Health Checks]]
:::
