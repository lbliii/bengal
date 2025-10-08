# Font Helper - Lightweight Design

## Overview

A simple, self-contained font helper that downloads Google Fonts at build time, integrates with Bengal's asset pipeline, and generates the necessary CSS. No external dependencies beyond what we already have.

## User Experience

### Simple Configuration

```toml
# bengal.toml
[fonts]
# Simple string syntax for single weight
primary = "Inter:400,600,700"
heading = "Playfair Display:700"
code = "Fira Code:400"

# Or detailed syntax for more control
[fonts.body]
family = "Inter"
weights = [400, 600, 700]
styles = ["normal", "italic"]  # Optional, defaults to ["normal"]
subsets = ["latin", "latin-ext"]  # Optional, defaults to ["latin"]

# Control where fonts are downloaded to
[fonts.config]
output_dir = "assets/fonts"  # Where to put downloaded fonts
self_host = true  # Download fonts vs CDN links (default: true)
preload = ["primary"]  # Which fonts to preload (default: none)
```

### Minimal API Usage

User adds fonts to their config, and Bengal:
1. Downloads the font files at build time (cached)
2. Copies them through the asset pipeline
3. Generates `fonts.css` with `@font-face` declarations
4. Makes font variables available in templates

### Template Usage

```html
<!-- Generated fonts.css is automatically included -->
<link rel="stylesheet" href="{{ 'fonts.css' | asset_url }}">

<!-- Use CSS custom properties -->
<style>
  body {
    font-family: var(--font-primary, sans-serif);
  }
  h1, h2, h3 {
    font-family: var(--font-heading, serif);
  }
  code {
    font-family: var(--font-code, monospace);
  }
</style>
```

## Architecture

### Module Structure

```
bengal/
  fonts/
    __init__.py           # Public API
    downloader.py         # Google Fonts API interaction
    generator.py          # CSS generation
    cache.py              # Font file caching
```

### Integration Points

1. **Config Loading** (`bengal/config/loader.py`)
   - Add `'fonts'` to `KNOWN_SECTIONS`
   - Parse font configuration

2. **Build Process** (`bengal/orchestration/build.py`)
   - Add font processing phase before asset discovery
   - Generate fonts.css and download files

3. **Asset Pipeline** (`bengal/core/asset.py`)
   - Downloaded fonts go through normal asset processing
   - fonts.css goes through CSS bundling/minification

## Implementation

### Phase 1: Core Functionality (MVP)

**File: `bengal/fonts/downloader.py`**

```python
"""
Font downloader using Google Fonts API.
"""

import urllib.request
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class FontVariant:
    """A specific font variant (weight + style)."""
    family: str
    weight: int
    style: str  # 'normal' or 'italic'
    url: str    # Direct URL to .woff2 file
    
    @property
    def filename(self) -> str:
        """Generate filename for this variant."""
        style_suffix = "-italic" if self.style == "italic" else ""
        safe_name = self.family.lower().replace(" ", "-")
        return f"{safe_name}-{self.weight}{style_suffix}.woff2"


class GoogleFontsDownloader:
    """
    Downloads fonts from Google Fonts.
    
    Uses the Google Fonts CSS API to get font URLs, then downloads
    the actual .woff2 files. No API key required.
    """
    
    BASE_URL = "https://fonts.googleapis.com/css2"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    def download_font(
        self,
        family: str,
        weights: List[int],
        styles: List[str] = None,
        output_dir: Path = None,
    ) -> List[FontVariant]:
        """
        Download a font family with specified weights.
        
        Args:
            family: Font family name (e.g., "Inter", "Roboto")
            weights: List of weights (e.g., [400, 700])
            styles: List of styles (e.g., ["normal", "italic"])
            output_dir: Directory to save font files
            
        Returns:
            List of downloaded FontVariant objects
        """
        styles = styles or ["normal"]
        output_dir = output_dir or Path.cwd()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Build Google Fonts CSS URL
        css_url = self._build_css_url(family, weights, styles)
        
        # Fetch the CSS to get font URLs
        font_urls = self._extract_font_urls(css_url)
        
        # Download each font file
        variants = []
        for weight in weights:
            for style in styles:
                key = f"{weight}-{style}"
                if key in font_urls:
                    url = font_urls[key]
                    variant = FontVariant(family, weight, style, url)
                    
                    # Download the font file
                    output_path = output_dir / variant.filename
                    if not output_path.exists():
                        self._download_file(url, output_path)
                        print(f"  ✓ Downloaded: {variant.filename}")
                    else:
                        print(f"  ✓ Cached: {variant.filename}")
                    
                    variants.append(variant)
        
        return variants
    
    def _build_css_url(self, family: str, weights: List[int], styles: List[str]) -> str:
        """Build Google Fonts CSS API URL."""
        # Format: family:wght@400;700 or family:ital,wght@0,400;1,400;0,700;1,700
        family_encoded = family.replace(" ", "+")
        
        if len(styles) == 1 and styles[0] == "normal":
            # Simple format for normal style only
            weights_str = ";".join(str(w) for w in sorted(weights))
            url = f"{self.BASE_URL}?family={family_encoded}:wght@{weights_str}&display=swap"
        else:
            # Full format with italic support
            specs = []
            for weight in sorted(weights):
                for style in styles:
                    ital = "1" if style == "italic" else "0"
                    specs.append(f"{ital},{weight}")
            specs_str = ";".join(specs)
            url = f"{self.BASE_URL}?family={family_encoded}:ital,wght@{specs_str}&display=swap"
        
        return url
    
    def _extract_font_urls(self, css_url: str) -> Dict[str, str]:
        """
        Fetch CSS from Google Fonts and extract .woff2 URLs.
        
        Returns:
            Dict mapping weight-style to URL (e.g., "400-normal" -> "https://...")
        """
        req = urllib.request.Request(css_url, headers={"User-Agent": self.USER_AGENT})
        
        with urllib.request.urlopen(req) as response:
            css_content = response.read().decode('utf-8')
        
        # Parse CSS to extract URLs
        # Google Fonts CSS has structure like:
        # /* latin */
        # @font-face {
        #   font-family: 'Inter';
        #   font-style: normal;
        #   font-weight: 400;
        #   src: url(https://fonts.gstatic.com/...woff2);
        # }
        
        import re
        font_urls = {}
        
        # Find all @font-face blocks
        font_face_pattern = r'@font-face\s*{([^}]+)}'
        for match in re.finditer(font_face_pattern, css_content):
            block = match.group(1)
            
            # Extract weight, style, and URL
            weight_match = re.search(r'font-weight:\s*(\d+)', block)
            style_match = re.search(r'font-style:\s*(\w+)', block)
            url_match = re.search(r'url\(([^)]+\.woff2)', block)
            
            if weight_match and style_match and url_match:
                weight = weight_match.group(1)
                style = style_match.group(1)
                url = url_match.group(1)
                
                key = f"{weight}-{style}"
                font_urls[key] = url
        
        return font_urls
    
    def _download_file(self, url: str, output_path: Path) -> None:
        """Download a file from URL to output path."""
        req = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})
        
        with urllib.request.urlopen(req) as response:
            data = response.read()
        
        output_path.write_bytes(data)
```

**File: `bengal/fonts/generator.py`**

```python
"""
Generate CSS for self-hosted fonts.
"""

from pathlib import Path
from typing import List, Dict
from bengal.fonts.downloader import FontVariant


class FontCSSGenerator:
    """
    Generates @font-face CSS for downloaded fonts.
    """
    
    def generate(
        self,
        font_mapping: Dict[str, List[FontVariant]],
        font_path_prefix: str = "/fonts",
    ) -> str:
        """
        Generate fonts.css content.
        
        Args:
            font_mapping: Dict of font name -> list of variants
            font_path_prefix: URL prefix for font files
            
        Returns:
            Complete CSS content as string
        """
        css_parts = [
            "/* Auto-generated by Bengal Font Helper */",
            "/* See bengal.toml [fonts] section */",
            "",
        ]
        
        # Generate @font-face rules for each variant
        for font_name, variants in font_mapping.items():
            family = variants[0].family  # All variants share same family
            
            css_parts.append(f"/* {family} */")
            
            for variant in variants:
                url = f"{font_path_prefix}/{variant.filename}"
                
                css_parts.append("@font-face {")
                css_parts.append(f"  font-family: '{variant.family}';")
                css_parts.append(f"  font-weight: {variant.weight};")
                css_parts.append(f"  font-style: {variant.style};")
                css_parts.append(f"  font-display: swap;")
                css_parts.append(f"  src: url('{url}') format('woff2');")
                css_parts.append("}")
                css_parts.append("")
        
        # Generate CSS custom properties
        css_parts.append("/* CSS Custom Properties */")
        css_parts.append(":root {")
        
        for font_name, variants in font_mapping.items():
            family = variants[0].family
            css_parts.append(f"  --font-{font_name}: '{family}';")
        
        css_parts.append("}")
        css_parts.append("")
        
        return "\n".join(css_parts)
```

**File: `bengal/fonts/__init__.py`**

```python
"""
Font helper for Bengal SSG.

Provides simple font downloading and CSS generation.
"""

from pathlib import Path
from typing import Dict, List, Any
from bengal.fonts.downloader import GoogleFontsDownloader, FontVariant
from bengal.fonts.generator import FontCSSGenerator


class FontHelper:
    """
    Main font helper interface.
    
    Usage:
        helper = FontHelper(config)
        helper.process(output_dir)
    """
    
    def __init__(self, font_config: Dict[str, Any]):
        """
        Initialize font helper with configuration.
        
        Args:
            font_config: [fonts] section from bengal.toml
        """
        self.config = font_config
        self.downloader = GoogleFontsDownloader()
        self.generator = FontCSSGenerator()
    
    def process(self, assets_dir: Path) -> Path:
        """
        Process fonts: download files and generate CSS.
        
        Args:
            assets_dir: Assets directory (fonts go in assets/fonts/)
            
        Returns:
            Path to generated fonts.css
        """
        if not self.config:
            return None
        
        # Parse config
        fonts_to_download = self._parse_config()
        
        if not fonts_to_download:
            return None
        
        print("\n🔤 Fonts:")
        
        # Download fonts
        fonts_dir = assets_dir / "fonts"
        fonts_dir.mkdir(parents=True, exist_ok=True)
        
        all_variants = {}
        for font_name, font_spec in fonts_to_download.items():
            print(f"   {font_spec['family']}...")
            variants = self.downloader.download_font(
                family=font_spec['family'],
                weights=font_spec['weights'],
                styles=font_spec.get('styles', ['normal']),
                output_dir=fonts_dir,
            )
            all_variants[font_name] = variants
        
        # Generate CSS
        css_content = self.generator.generate(all_variants)
        css_path = assets_dir / "fonts.css"
        css_path.write_text(css_content, encoding='utf-8')
        
        total_fonts = sum(len(v) for v in all_variants.values())
        print(f"   └─ Generated: fonts.css ({total_fonts} variants)")
        
        return css_path
    
    def _parse_config(self) -> Dict[str, Dict[str, Any]]:
        """
        Parse [fonts] configuration into normalized format.
        
        Returns:
            Dict mapping font name to font specification
        """
        fonts = {}
        
        for key, value in self.config.items():
            # Skip config keys
            if key == "config":
                continue
            
            # Parse different config formats
            if isinstance(value, str):
                # Simple string: "Inter:400,600,700"
                if ":" in value:
                    family, weights_str = value.split(":", 1)
                    weights = [int(w.strip()) for w in weights_str.split(",")]
                else:
                    family = value
                    weights = [400]  # Default weight
                
                fonts[key] = {
                    'family': family,
                    'weights': weights,
                    'styles': ['normal'],
                }
            
            elif isinstance(value, dict):
                # Detailed dict format
                fonts[key] = {
                    'family': value['family'],
                    'weights': value.get('weights', [400]),
                    'styles': value.get('styles', ['normal']),
                    'subsets': value.get('subsets', ['latin']),
                }
        
        return fonts


__all__ = ['FontHelper', 'GoogleFontsDownloader', 'FontCSSGenerator']
```

### Phase 2: Integration with Build Process

**File: `bengal/orchestration/build.py` (modifications)**

```python
# Add to imports
from bengal.fonts import FontHelper

class BuildOrchestrator:
    def build(self, ...):
        # ... existing phases ...
        
        # NEW: Phase 2.5: Process Fonts (before asset discovery)
        if 'fonts' in self.site.config:
            with self.logger.phase("fonts"):
                fonts_start = time.time()
                assets_dir = self.site.root_path / "assets"
                assets_dir.mkdir(parents=True, exist_ok=True)
                
                font_helper = FontHelper(self.site.config['fonts'])
                fonts_css = font_helper.process(assets_dir)
                
                self.stats.fonts_time_ms = (time.time() - fonts_start) * 1000
                self.logger.info("fonts_complete")
        
        # Phase 3: Discover content and assets (will pick up fonts.css and font files)
        # ... continue with existing phases ...
```

**File: `bengal/config/loader.py` (modification)**

```python
class ConfigLoader:
    KNOWN_SECTIONS = {
        'site', 'build', 'markdown', 'features', 'taxonomies',
        'menu', 'params', 'assets', 'pagination', 'dev', 
        'output_formats', 'health_check', 'fonts'  # ADD THIS
    }
```

### Phase 3: Caching (Optional Performance Enhancement)

Downloaded fonts should be cached to avoid re-downloading on every build:

```python
# bengal/fonts/cache.py
"""
Font file caching to avoid re-downloading.
"""

from pathlib import Path
import hashlib
import json


class FontCache:
    """
    Cache downloaded font files.
    
    Cache structure:
        .bengal-cache/
          fonts/
            inter-400-normal.woff2
            inter-700-normal.woff2
            fonts.json  # Metadata
    """
    
    def __init__(self, cache_dir: Path = None):
        if cache_dir is None:
            cache_dir = Path.cwd() / ".bengal-cache" / "fonts"
        
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / "fonts.json"
        self.metadata = self._load_metadata()
    
    def get(self, font_key: str) -> Path:
        """Get cached font file path if it exists."""
        if font_key in self.metadata:
            path = self.cache_dir / self.metadata[font_key]['filename']
            if path.exists():
                return path
        return None
    
    def put(self, font_key: str, source_path: Path) -> None:
        """Add font file to cache."""
        # Implementation details...
        pass
```

## Benefits

### For Users

1. **Simple configuration** - Just list fonts in bengal.toml
2. **Self-hosted by default** - Better performance, privacy, reliability
3. **No manual downloads** - Fonts fetched automatically at build time
4. **Works offline** - After first download, fonts are cached
5. **CSS variables** - Clean, semantic font usage in templates

### For Bengal

1. **Zero external dependencies** - Uses only stdlib (urllib, re)
2. **Integrates naturally** - Fonts become regular assets
3. **Optional feature** - If no [fonts] config, nothing happens
4. **Extensible** - Easy to add subsetting, CDN mode, etc. later

## Future Enhancements (Phase 4+)

1. **Font subsetting** with FontTools
   ```toml
   [fonts.config]
   subset = true
   characters = "latin"  # or custom character set
   ```

2. **CDN mode** (skip download, generate link tags)
   ```toml
   [fonts.config]
   self_host = false  # Use Google CDN instead
   ```

3. **Preload hints** for critical fonts
   ```html
   <link rel="preload" href="/fonts/inter-400-normal.woff2" as="font" type="font/woff2" crossorigin>
   ```

4. **Font preview** in theme docs
   - Generate preview images showing each font
   - Useful for theme documentation

5. **Support other font sources**
   - Adobe Fonts
   - Custom font files from local directory
   - Font Awesome icons

## Testing Strategy

1. **Unit tests** for downloader, generator, parser
2. **Integration test** with minimal bengal.toml
3. **Cache tests** to ensure fonts aren't re-downloaded
4. **Error handling** for network issues, invalid fonts

## Example: Complete User Flow

```toml
# bengal.toml
[fonts]
primary = "Inter:400,600,700"
heading = "Playfair Display:700,900"
code = "JetBrains Mono:400"
```

**Build output:**
```
$ bengal build

🔤 Fonts:
   Inter...
     ✓ Downloaded: inter-400-normal.woff2
     ✓ Downloaded: inter-600-normal.woff2
     ✓ Downloaded: inter-700-normal.woff2
   Playfair Display...
     ✓ Downloaded: playfair-display-700-normal.woff2
     ✓ Downloaded: playfair-display-900-normal.woff2
   JetBrains Mono...
     ✓ Downloaded: jetbrains-mono-400-normal.woff2
   └─ Generated: fonts.css (6 variants)

📁 Discovering content from content/
   ...
```

**Generated fonts.css:**
```css
/* Auto-generated by Bengal Font Helper */

/* Inter */
@font-face {
  font-family: 'Inter';
  font-weight: 400;
  font-style: normal;
  font-display: swap;
  src: url('/fonts/inter-400-normal.woff2') format('woff2');
}

@font-face {
  font-family: 'Inter';
  font-weight: 600;
  font-style: normal;
  font-display: swap;
  src: url('/fonts/inter-600-normal.woff2') format('woff2');
}

/* ... more @font-face rules ... */

/* CSS Custom Properties */
:root {
  --font-primary: 'Inter';
  --font-heading: 'Playfair Display';
  --font-code: 'JetBrains Mono';
}
```

**In templates:**
```html
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="{{ 'fonts.css' | asset_url }}">
  <style>
    body { font-family: var(--font-primary, sans-serif); }
    h1 { font-family: var(--font-heading, serif); }
    code { font-family: var(--font-code, monospace); }
  </style>
</head>
...
```

## Implementation Effort

- **Phase 1 (MVP)**: ~4-6 hours
  - Downloader: 2 hours
  - Generator: 1 hour
  - Integration: 2 hours
  - Testing: 1 hour

- **Phase 2 (Polish)**: ~2-3 hours
  - Caching: 1 hour
  - Error handling: 1 hour
  - Documentation: 1 hour

**Total**: ~6-9 hours for a production-ready feature

## Decision: Should We Build This?

### ✅ Pros
- Clean, elegant solution
- Zero dependencies (stdlib only)
- Natural integration with existing asset pipeline
- Solves real problem (self-hosted fonts are better)
- Easy to maintain
- Users will love the DX

### ❌ Cons  
- Additional surface area to maintain
- Google Fonts API could change
- Some users won't need it
- Not critical to core SSG functionality

### 🎯 Recommendation

**Yes, build it!** Here's why:

1. **Lightweight** - Only ~300 lines of code total
2. **High value** - Self-hosted fonts are genuinely better
3. **Great DX** - Makes Bengal more complete/polished
4. **Zero deps** - No external packages needed
5. **Optional** - If you don't use it, it costs nothing
6. **Sets Bengal apart** - Not many SSGs have this built-in

This is the kind of thoughtful, integrated feature that makes a tool feel premium.

