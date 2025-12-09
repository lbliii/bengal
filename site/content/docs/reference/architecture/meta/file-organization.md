---
title: File Organization
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
│   ├── .bengal-cache.json           # Build cache (metadata)
│   └── .bengal-cache/
│       └── templates/                # Jinja2 bytecode cache
│
└── .bengal/              # Development files (generated, .gitignored)
    ├── profiles/         # Performance profiling data
    │   ├── profile.stats
    │   └── build_profile.stats
    └── logs/             # Build logs (future)
        └── build.log
```

## File Categories

Bengal organizes generated files into three categories:

1. **Build Outputs** (`public/`)
   - Deployable website files
   - Should be .gitignored
   - Example: `public/index.html`, `public/assets/`

2. **Build Metadata** (`public/.bengal-cache*`)
   - Cache files that improve rebuild performance
   - Stored alongside outputs for atomic cleanup
   - Should be .gitignored
   - Examples:
     - `.bengal-cache.json` - Incremental build cache
     - `.bengal-cache/templates/` - Jinja2 bytecode cache

3. **Development Files** (`.bengal/`)
   - Performance profiles, logs, and debugging data
   - Separate from source and outputs
   - Should be .gitignored
   - Examples:
     - `.bengal/profiles/profile.stats` - Performance profiling data
     - `.bengal-build.log` - Build logs (currently at root for backward compatibility)

## Usage in Code

The `BengalPaths` utility class (`bengal/utils/paths.py`) provides consistent path management:

```python
from bengal.utils.paths import BengalPaths

# Get profile directory (creates if needed)
profile_dir = BengalPaths.get_profile_dir(source_dir)

# Get profile file path with custom or default name
profile_path = BengalPaths.get_profile_path(
    source_dir,
    custom_path=None,  # or Path("custom.stats")
    filename='build_profile.stats'
)

# Get cache paths
cache_path = BengalPaths.get_cache_path(output_dir)
template_cache = BengalPaths.get_template_cache_dir(output_dir)

# Get log path
log_path = BengalPaths.get_build_log_path(source_dir)
```

## CLI Integration

The CLI automatically uses organized paths:

```bash
# Default: saves to .bengal/profiles/profile.stats
bengal site build --perf-profile

# Custom path
bengal site build --perf-profile my-profile.stats

# Build log: defaults to .bengal-build.log
bengal site build --log-file custom.log
```

## Design Rationale

1. **Separation of Concerns**:
   - Source files (content/) - version controlled
   - Build outputs (public/) - deployable, .gitignored
   - Build cache (public/.bengal-cache*) - improves performance, .gitignored
   - Dev tools (.bengal/) - profiling/debugging, .gitignored

2. **Easy Cleanup**:
   - `rm -rf public/` removes all build outputs including cache
   - `rm -rf .bengal/` removes all development artifacts
   - Source files remain untouched

3. **Backward Compatibility**:
   - `.bengal-build.log` stays at root for now (may move to `.bengal/logs/` in future)
   - Cache files in `public/` ensure they're cleaned up with outputs

4. **Git-Friendly**:
   - All generated files are properly ignored via `.gitignore`
   - Clear separation between tracked and generated files

## Extension Points
