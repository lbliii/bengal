---
title: Fonts System
description: Automatic Google Fonts downloading and self-hosting
weight: 40
category: subsystems
tags: [subsystems, fonts, google-fonts, self-hosting, performance, privacy, css-generation]
keywords: [fonts, Google Fonts, self-hosting, performance, privacy, CSS generation, font management]
---

# Fonts System (`bengal/fonts/`)

Bengal includes a built-in font management system that automatically downloads and hosts Google Fonts locally, improving performance and privacy.

## Overview

The fonts system provides:
- **Automatic font downloading** from Google Fonts (no external dependencies)
- **Self-hosting** for better performance and GDPR compliance
- **CSS generation** with @font-face rules and CSS custom properties
- **Zero configuration** - just specify fonts in bengal.toml

**Benefits**:
- No external requests to Google Fonts CDN at runtime
- Faster page loads (fonts served from same domain)
- GDPR/privacy compliance (no third-party tracking)
- Offline builds
- Cache control

## Font Downloader (`bengal/fonts/downloader.py`)

### Purpose
Downloads font files from Google Fonts using the public CSS API.

### Key Classes

| Class | Description |
|-------|-------------|
| `GoogleFontsDownloader` | Downloads fonts from Google Fonts API |
| `FontVariant` | Represents a specific font variant (family + weight + style) |

### Features
- No API key required
- Uses stdlib only (urllib)
- Automatic WOFF2 format selection (modern, smaller files)
- Supports multiple weights and styles
- SSL/TLS support
- Robust error handling

### Usage

```python
from bengal.fonts import GoogleFontsDownloader

downloader = GoogleFontsDownloader()
variants = downloader.download_font(
    family="Inter",
    weights=[400, 600, 700],
    styles=["normal", "italic"],
    output_dir=Path("public/assets/fonts")
)

# Returns list of FontVariant objects with file info
```

## Font CSS Generator (`bengal/fonts/generator.py`)

### Purpose
Generates @font-face CSS rules for self-hosted fonts.

### Key Classes

| Class | Description |
|-------|-------------|
| `FontCSSGenerator` | Generates CSS with @font-face rules and custom properties |

### Generated CSS includes
- @font-face declarations for each variant
- font-display: swap for performance
- CSS custom properties for easy reference

### Example output

```css
/* Inter */
@font-face {
  font-family: 'Inter';
  font-weight: 400;
  font-style: normal;
  font-display: swap;
  src: url('/fonts/inter-400.woff2') format('woff2');
}

@font-face {
  font-family: 'Inter';
  font-weight: 700;
  font-style: normal;
  font-display: swap;
  src: url('/fonts/inter-700.woff2') format('woff2');
}

/* CSS Custom Properties */
:root {
  --font-primary: 'Inter';
  --font-heading: 'Playfair Display';
}
```

## Font Helper (`bengal/fonts/__init__.py`)

### Purpose
Main interface that orchestrates downloading and CSS generation.

### Key Classes

| Class | Description |
|-------|-------------|
| `FontHelper` | Coordinates font downloading and CSS generation |

### Usage

```python
from bengal.fonts import FontHelper

helper = FontHelper(config['fonts'])
css_path = helper.process(assets_dir)
```

## Configuration

Configure fonts in `bengal.toml`:

### Simple format (family:weights)

```toml
[fonts]
primary = "Inter:400,600,700"
heading = "Playfair Display:700,900"
mono = "Fira Code:400,500"
```

### Detailed format (with styles)

```toml
[fonts.primary]
family = "Inter"
weights = [400, 600, 700]
styles = ["normal", "italic"]

[fonts.heading]
family = "Playfair Display"
weights = [700, 900]
styles = ["normal"]
```

## Build Integration

Fonts are automatically processed during builds:

1. **Font Helper runs** early in build process
2. **Downloads fonts** to `public/assets/fonts/`
3. **Generates fonts.css** in `public/assets/`
4. **Theme can reference** fonts via CSS custom properties

### In theme CSS

```css
body {
  font-family: var(--font-primary), sans-serif;
}

h1, h2, h3 {
  font-family: var(--font-heading), serif;
}

code {
  font-family: var(--font-mono), monospace;
}
```

## Health Validation

The FontValidator checks:
- Font files downloaded successfully
- fonts.css generated correctly
- File sizes reasonable (< 500KB per variant)
- All configured fonts present

```bash
# Font health check runs automatically
bengal site build

# Example output:
# 🔤 Fonts:
#    Inter...
#    Playfair Display...
#    └─ Generated: fonts.css (5 variants)
```

## Performance Characteristics

**File sizes**: WOFF2 format typically 15-100KB per variant

**Build overhead**: Minimal - fonts cached locally after first download

**Runtime performance**: Eliminates external CDN requests

**Comparison to Google Fonts CDN**:

| Aspect | CDN | Self-hosted |
|--------|-----|-------------|
| Initial page load | External request | Same domain |
| Caching | Shared cache | Local cache |
| Privacy | Third-party | No tracking |
| Offline | Requires connection | Works offline |
