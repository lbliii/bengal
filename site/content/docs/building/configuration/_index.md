---
title: Configuration
description: Configuring Bengal with bengal.toml
weight: 10
draft: false
lang: en
tags: [configuration, settings]
keywords: [configuration, bengal.toml, settings, options]
category: guide
---

# Configuration

Configure Bengal using the `bengal.toml` configuration file.

## Overview

Bengal uses TOML for configuration, with support for:

- **Single file** — `bengal.toml` in project root
- **Directory-based** — `config/` with modular files
- **Environment overrides** — Different settings per environment

## Basic Configuration

```toml
# bengal.toml
[site]
title = "My Site"
base_url = "https://example.com"
language = "en"
description = "A Bengal-powered site"

[build]
output_dir = "public"
clean = true

[theme]
name = "default"
```

## Directory-Based Configuration

For larger sites, split configuration:

```
config/
├── _default/
│   ├── site.yaml
│   ├── build.yaml
│   └── theme.yaml
└── environments/
    ├── production.yaml
    └── staging.yaml
```

## Environment-Specific Settings

```toml
# config/environments/production.yaml
site:
  base_url: "https://example.com"

build:
  minify: true
  fingerprint: true
```

Run with:

```bash
bengal build --environment production
```

## In This Section

- **[Options Reference](/docs/building/configuration/options/)** — All configuration options
- **[Environments](/docs/building/configuration/environments/)** — Environment-specific configuration


