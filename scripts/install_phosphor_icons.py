#!/usr/bin/env python3
"""
Download Phosphor Icons and replace Bengal's custom icons.

Phosphor Icons: https://phosphoricons.com/
GitHub: https://github.com/phosphor-icons/core
"""

import json
import re
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

# Base URL for Phosphor icons (regular weight)
PHOSPHOR_BASE_URL = "https://raw.githubusercontent.com/phosphor-icons/core/main/assets/regular"

# Map Bengal icon names to Phosphor icon names
ICON_MAPPING = {
    # Navigation
    "menu": "list",
    "search": "magnifying-glass",
    "close": "x",
    "chevron-up": "caret-up",
    "chevron-down": "caret-down",
    "chevron-left": "caret-left",
    "chevron-right": "caret-right",
    "link": "link",
    "external": "arrow-square-out",
    
    # Status
    "check": "check",
    "info": "info",
    "warning": "warning",
    "error": "x-circle",
    
    # Files & Content
    "file": "file",
    "folder": "folder",
    "code": "code",
    "copy": "copy",
    "edit": "pencil",
    "download": "download",
    "upload": "upload",
    "trash": "trash",
    
    # UI Elements
    "settings": "gear",
    "star": "star",
    "heart": "heart",
    "bookmark": "bookmark",
    "tag": "tag",
    "calendar": "calendar",
    "clock": "clock",
    "pin": "map-pin",
    
    # Theme
    "sun": "sun",
    "moon": "moon",
    "palette": "palette",
    
    # Bengal-specific (keep custom or find closest match)
    "terminal": "terminal",
    "docs": "file-text",  # or "book" or "files"
    "notepad": "note",
    
    # Mid-century modern (keep custom or find closest)
    "atomic": "atom",  # Phosphor has atom icon
    "starburst": "star-four",  # or "sparkle"
    "boomerang": "arrow-arc-left",  # closest match
    
    # Bengal rosette - keep custom
    "bengal-rosette": None,  # Keep custom
}

ICONS_DIR = Path(__file__).parent.parent / "bengal" / "themes" / "default" / "assets" / "icons"


def download_phosphor_icon(icon_name: str) -> str | None:
    """
    Download a Phosphor icon SVG.
    
    Args:
        icon_name: Phosphor icon name (e.g., "magnifying-glass")
        
    Returns:
        SVG content as string, or None if download fails
    """
    url = f"{PHOSPHOR_BASE_URL}/{icon_name}.svg"
    
    try:
        req = Request(url, headers={"User-Agent": "Bengal/1.0"})
        with urlopen(req, timeout=10) as response:
            svg_content = response.read().decode("utf-8")
            return svg_content
    except URLError as e:
        print(f"  ❌ Failed to download {icon_name}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  ❌ Error downloading {icon_name}: {e}", file=sys.stderr)
        return None


def normalize_phosphor_svg(svg_content: str, icon_name: str) -> str:
    """
    Normalize Phosphor SVG to match Bengal's format.
    
    - Keeps Phosphor's 256x256 viewBox (SVG scales via width/height)
    - Adds title if missing
    - Ensures fill="none" on root and currentColor for paths
    - Removes any hardcoded colors
    
    Args:
        svg_content: Raw Phosphor SVG content
        icon_name: Icon name for title
        
    Returns:
        Normalized SVG content
    """
    # Remove XML declaration if present
    svg_content = re.sub(r'<\?xml[^>]*\?>', '', svg_content).strip()
    
    # Remove width/height attributes (Bengal's renderer adds these)
    svg_content = re.sub(r'\s+(width|height)="[^"]*"', '', svg_content)
    
    # Remove all fill attributes from SVG tag
    svg_content = re.sub(r'\s+fill="[^"]*"', '', svg_content)
    
    # Ensure fill="none" on root SVG (for proper theme support)
    svg_content = re.sub(
        r'<svg\s+([^>]*)>',
        r'<svg \1 fill="none">',
        svg_content,
        count=1
    )
    
    # Replace any hardcoded fill colors in paths with currentColor
    svg_content = re.sub(r'fill="#[0-9a-fA-F]{6}"', 'fill="currentColor"', svg_content)
    svg_content = re.sub(r'fill="#[0-9a-fA-F]{3}"', 'fill="currentColor"', svg_content)
    
    # Ensure stroke uses currentColor if present
    svg_content = re.sub(r'stroke="#[^"]*"', 'stroke="currentColor"', svg_content)
    
    # Phosphor icons use fill by default - ensure paths have fill="currentColor"
    # Add fill="currentColor" to paths that don't have fill attribute
    svg_content = re.sub(
        r'<path\s+((?!fill=)[^>]*?)d="',
        r'<path \1fill="currentColor" d="',
        svg_content
    )
    
    # Add title if missing (right after <svg> tag)
    if '<title>' not in svg_content:
        title = icon_name.replace("-", " ").title()
        svg_content = re.sub(
            r'(<svg[^>]*>)',
            f'\\1\\n  <title>{title}</title>',
            svg_content,
            count=1
        )
    
    return svg_content.strip()


def backup_existing_icons():
    """Backup existing icons to a backup directory."""
    backup_dir = ICONS_DIR.parent / "icons_backup"
    backup_dir.mkdir(exist_ok=True)
    
    print(f"📦 Backing up existing icons to {backup_dir.name}/...")
    for icon_file in ICONS_DIR.glob("*.svg"):
        backup_file = backup_dir / icon_file.name
        backup_file.write_text(icon_file.read_text())
    
    print(f"✅ Backed up {len(list(ICONS_DIR.glob('*.svg')))} icons")


def install_phosphor_icons():
    """Download and install Phosphor icons."""
    print("🚀 Installing Phosphor Icons...")
    print(f"📁 Target directory: {ICONS_DIR}")
    
    if not ICONS_DIR.exists():
        ICONS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Backup existing icons
    backup_existing_icons()
    
    # Download icons
    downloaded = 0
    skipped = 0
    failed = 0
    
    for bengal_name, phosphor_name in ICON_MAPPING.items():
        if phosphor_name is None:
            print(f"⏭️  Skipping {bengal_name} (keeping custom)")
            skipped += 1
            continue
        
        print(f"📥 Downloading {bengal_name} → {phosphor_name}...", end=" ")
        
        svg_content = download_phosphor_icon(phosphor_name)
        if svg_content is None:
            print("❌")
            failed += 1
            continue
        
        # Normalize SVG
        normalized = normalize_phosphor_svg(svg_content, bengal_name)
        
        # Write to file
        icon_file = ICONS_DIR / f"{bengal_name}.svg"
        icon_file.write_text(normalized, encoding="utf-8")
        
        print("✅")
        downloaded += 1
    
    print("\n" + "="*60)
    print(f"✅ Downloaded: {downloaded}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"❌ Failed: {failed}")
    print("="*60)
    
    if failed > 0:
        print("\n⚠️  Some icons failed to download. Check errors above.")
        return 1
    
    print("\n🎉 Phosphor Icons installed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(install_phosphor_icons())

