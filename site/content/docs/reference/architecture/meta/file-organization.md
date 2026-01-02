---
title: File Organization
nav_title: Files
description: Directory structure and organization of generated files, cache, and development
  artifacts
weight: 30
category: meta
tags:
- meta
- file-organization
- directory-structure
- paths
- cache
- build-outputs
keywords:
- file organization
- directory structure
- paths
- cache
- build outputs
- development files
---

# File Organization

Bengal maintains a clean and organized directory structure for generated files, separating build outputs, cache data, and development artifacts.

## Directory Structure

```
mysite/
├── content/              # Source content (user-managed)
├── templates/            # Custom templates (user-managed)
├── assets/               # Static assets (user-managed)
├── bengal.toml           # Configuration (user-managed)
│
├── public/               # Build outputs (generated, .gitignored)
│   ├── index.html
│   ├── assets/
│   └── asset-manifest.json
│
└── .bengal/              # All Bengal state (generated, .gitignored)
    ├── cache.json.zst           # Main build cache (Zstandard compressed)
    ├── page_metadata.json.zst   # Page discovery cache (compressed)
    ├── asset_deps.json.zst      # Asset dependency map (compressed)
    ├── taxonomy_index.json.zst  # Taxonomy index (compressed)
    ├── build_history.json       # Build history for delta analysis
    ├── server.pid               # Dev server PID
    ├── asset-manifest.json      # Asset manifest
    ├── indexes/                 # Query indexes (section, author, etc.)
    ├── templates/               # Jinja2 bytecode cache
    ├── content_cache/           # Remote content cache
    ├── generated/               # Generated content (auto-pages, etc.)
    ├── logs/                    # Build/serve logs
    │   ├── build.log
    │   └── serve.log
    ├── metrics/                 # Performance metrics
    ├── profiles/                # Profiling output
    │   └── build_profile.stats
    ├── themes/                  # Theme state (swizzle registry)
    │   └── sources.json
    ├── js_bundle/               # JS bundle temporary files
    └── pipeline_out/            # Asset pipeline temporary output
```

## File Categories

Bengal organizes generated files into two categories:

1. **Build Outputs** (`public/`)
   - Deployable website files
   - Should be .gitignored
   - Example: `public/index.html`, `public/assets/`

2. **Bengal State** (`.bengal/`)
   - All Bengal-managed state in one place
   - Cache files, logs, metrics, and development artifacts
   - Should be .gitignored
   - Key files:
     - `.bengal/cache.json.zst` - Main build cache (Zstandard compressed, 92-93% smaller)
     - `.bengal/templates/` - Jinja2 bytecode cache
     - `.bengal/logs/build.log` - Build logs
     - `.bengal/profiles/` - Performance profiling data
     - `.bengal/metrics/` - Performance metrics for trend analysis

## Usage in Code

The `BengalPaths` class (`bengal/cache/paths.py`) provides consistent path management:

```python
from bengal.cache.paths import BengalPaths

# Create paths accessor from project root
paths = BengalPaths(site.root_path)

# Access specific paths
cache_path = paths.build_cache       # .bengal/cache.json
logs_dir = paths.logs_dir            # .bengal/logs/
build_log = paths.build_log          # .bengal/logs/build.log
profiles_dir = paths.profiles_dir    # .bengal/profiles/
templates_dir = paths.templates_dir  # .bengal/templates/
metrics_dir = paths.metrics_dir      # .bengal/metrics/

# Create all directories
paths.ensure_dirs()

# Also accessible via Site object
cache_path = site.paths.build_cache
```

## CLI Integration

The CLI automatically uses organized paths:

```bash
# Default: saves to .bengal/profiles/profile.stats
bengal build --perf-profile

# Custom path
bengal build --perf-profile my-profile.stats

# Build log: defaults to .bengal/logs/build.log
bengal build --log-file custom.log
```

## Design Rationale

1. **Centralized State**:
   - All Bengal state in `.bengal/` directory
   - Easy `.gitignore` management (just ignore `.bengal/`)
   - Centralized debugging info (logs, metrics, profiles in one place)
   - Safe cache clearing (`rm -rf .bengal/` to reset state)

2. **Easy Cleanup**:
   - `rm -rf public/` removes all build outputs
   - `rm -rf .bengal/` removes all Bengal state and cache
   - Source files remain untouched

3. **Zstandard Compression**:
   - Main build cache compressed with Zstd (92-93% smaller)
   - Faster CI/CD cache upload/download
   - Automatic migration from old uncompressed caches

4. **Git-Friendly**:
   - All generated files properly ignored via `.gitignore`
   - Clear separation between tracked and generated files
