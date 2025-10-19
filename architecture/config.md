# Configuration System

Bengal's configuration system provides flexible, format-agnostic loading of site configuration.

## Config Loader (`bengal/config/loader.py`)

### Purpose
Load and manage site configuration from TOML or YAML files

### Features
- Supports TOML and YAML formats
- Auto-detects config files
- Provides sensible defaults
- Flattens nested configuration for easy access
- **Uses Utilities**: Delegates to `bengal.utils.file_io` for robust file loading with error handling

### Auto-Detection Order
1. `bengal.toml`
2. `bengal.yaml` / `bengal.yml`
3. `config.toml`
4. `config.yaml` / `config.yml`

### Configuration Structure

```toml
# bengal.toml

# Site metadata
title = "My Site"
description = "A Bengal SSG site"
base_url = "https://example.com"
language = "en"

# Build settings
[build]
output_dir = "public"
markdown_engine = "mistune"  # or "python-markdown"
parallel = true
incremental = false

# Theme
theme = "default"

# Taxonomies
[taxonomies]
tags = "tags"
categories = "categories"

# Menus
[[menus.main]]
name = "Home"
url = "/"
weight = 1

[[menus.main]]
name = "Blog"
url = "/blog/"
weight = 2

# Fonts
[fonts]
primary = "Inter:400,600,700"
heading = "Playfair Display:700,900"

# Health checks
[health_check]
validate_build = true

[health_check.validators]
configuration = true
output = true
links = true
```

### Default Configuration

If no config file found, Bengal provides sensible defaults:

```python
{
    'title': 'My Site',
    'base_url': '',
    'output_dir': 'public',
    'content_dir': 'content',
    'assets_dir': 'assets',
    'templates_dir': 'templates',
    'theme': 'default',
    'build': {
        'parallel': True,
        'incremental': False,
        'markdown_engine': 'mistune',
    },
    'taxonomies': {
        'tags': 'tags',
        'categories': 'categories',
    },
}
```

### Usage

```python
from bengal.config import load_config

# Auto-detect and load
config = load_config()

# Load from specific path
config = load_config(Path('my-config.toml'))

# Access values
title = config['title']
parallel = config['build']['parallel']
```

### Configuration Validation

The ConfigValidator (part of health check system) validates:
- Required fields present
- Valid values for enums
- Path existence
- Type correctness
- Common misconfigurations
