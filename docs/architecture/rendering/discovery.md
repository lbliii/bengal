---
title: Discovery System
nav_title: Discovery
description: How Bengal finds and catalogs content, sections, and assets
weight: 20
category: rendering
tags:
- rendering
- discovery
- content-discovery
- asset-discovery
- file-scanning
keywords:
- discovery
- content discovery
- asset discovery
- file scanning
- content organization
---

# Discovery System

The discovery system is responsible for finding and cataloging all content, sections, and assets in a Bengal site.

## Content Discovery (`bengal/content/discovery/content_discovery.py`)

### Purpose
Walks the content directory recursively to create Page and Section objects

### Responsibilities
- Walks content directory recursively
- Creates Page and Section objects
- Parses frontmatter
- Organizes content into hierarchy
- **Includes autodoc-generated markdown files**
- **Uses Utilities**: Delegates to `bengal.utils.io.file_io.read_text_file()` for robust file reading with encoding fallback

### Process Flow
1. Start at content root directory
2. Recursively traverse directories
3. For each directory:
   - Create Section object
   - Look for `_index.md` (section index page)
   - Find all markdown files
4. For each markdown file:
   - Read file content
   - Parse frontmatter (YAML/TOML)
   - Extract metadata
   - Create Page object
   - Associate with parent Section
5. Build section hierarchy
6. Return organized Pages and Sections

### Features
- Encoding fallback (UTF-8 → latin-1)
- UTF-8 BOM stripping during read to avoid confusing frontmatter parsing
- Error handling for malformed files (frontmatter syntax errors fall back to content-only)
- Automatic section creation
- Hierarchical organization
- Cross-reference index building

## Asset Discovery (`bengal/content/discovery/asset_discovery.py`)

### Purpose
Finds all static assets and creates Asset objects

### Responsibilities
- Finds all static assets
- Preserves directory structure
- Creates Asset objects with metadata
- Tracks asset types (CSS, JS, images, fonts, etc.)

### Process Flow
1. Walk assets directory
2. For each file:
   - Determine asset type (by extension)
   - Create Asset object
   - Preserve relative path
   - Track for processing
3. Also discover theme assets
4. Return organized Asset list

### Asset Types
- **Images**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.svg`
- **Stylesheets**: `.css`, `.scss`, `.sass`, `.less`
- **Scripts**: `.js`, `.mjs`, `.ts`
- **Fonts**: `.woff`, `.woff2`, `.ttf`, `.otf`, `.eot`
- **Data**: `.json`, `.yaml`, `.yml`, `.toml`, `.xml`
- **Documents**: `.pdf`, `.doc`, `.docx`
- **Other**: Any other files

### Features
- Type detection by extension
- Path preservation
- Metadata extraction
- Theme asset integration
- Optimization hints

## Content Versioning (`bengal/content/versioning/`)

The versioning subpackage handles multi-version documentation builds.

### Git Version Adapter (`bengal/content/versioning/git_adapter.py`)

Discovers documentation versions from Git branches and tags:

- **GitVersionAdapter**: Discovers versions from Git refs
- **GitRef**: Represents a Git branch or tag
- **GitWorktree**: Manages Git worktrees for parallel builds

```python
from bengal.content.versioning import GitVersionAdapter
from bengal.core.version import GitVersionConfig

config = GitVersionConfig(branches=[...])
adapter = GitVersionAdapter(repo_path, config)
versions = adapter.discover_versions()
```

### Version Resolver (`bengal/content/versioning/resolver.py`)

Resolves versioned content paths and manages shared content:

- Determine which version a content path belongs to
- Get logical paths (without version prefix)
- Resolve cross-version links (`[[v2:path/to/page]]`)
- Manage shared content across versions

```python
from bengal.content.versioning import VersionResolver

resolver = VersionResolver(version_config, root_path)
version = resolver.get_version_for_path("_versions/v2/docs/guide.md")
```
