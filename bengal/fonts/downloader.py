"""
Font downloader using Google Fonts API.

No external dependencies - uses only Python stdlib.
"""

import urllib.request
import urllib.error
import re
import ssl
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class FontVariant:
    """A specific font variant (weight + style)."""
    family: str
    weight: int
    style: str  # 'normal' or 'italic'
    url: str    # Direct URL to font file (.woff2 or .ttf)
    
    @property
    def filename(self) -> str:
        """Generate filename for this variant."""
        style_suffix = "-italic" if self.style == "italic" else ""
        safe_name = self.family.lower().replace(" ", "-")
        # Preserve original file extension from URL
        ext = '.woff2' if '.woff2' in self.url else '.ttf' if '.ttf' in self.url else '.woff2'
        return f"{safe_name}-{self.weight}{style_suffix}{ext}"


class GoogleFontsDownloader:
    """
    Downloads fonts from Google Fonts.
    
    Uses the Google Fonts CSS API to get font URLs, then downloads
    the actual .woff2 files. No API key required.
    """
    
    BASE_URL = "https://fonts.googleapis.com/css2"
    # User-Agent that gets WOFF2 files (modern browser)
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    def download_font(
        self,
        family: str,
        weights: List[int],
        styles: Optional[List[str]] = None,
        output_dir: Optional[Path] = None,
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
        
        try:
            # Fetch the CSS to get font URLs
            font_urls = self._extract_font_urls(css_url)
            
            if not font_urls:
                print(f"⚠️  Warning: No fonts found for {family}")
                return []
            
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
                            print(f"     ✓ Downloaded: {variant.filename}")
                        else:
                            print(f"     ✓ Cached: {variant.filename}")
                        
                        variants.append(variant)
            
            return variants
            
        except Exception as e:
            print(f"⚠️  Error downloading {family}: {e}")
            print(f"   Continuing build without this font...")
            return []
    
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
        
        # Try with standard SSL verification first, fall back to unverified on macOS
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                css_content = response.read().decode('utf-8')
        except (ssl.SSLError, urllib.error.URLError) as e:
            # macOS certificate issue - retry with unverified context
            if 'certificate verify failed' in str(e) or 'SSL' in str(e):
                ssl_context = ssl._create_unverified_context()
                with urllib.request.urlopen(req, timeout=10, context=ssl_context) as response:
                    css_content = response.read().decode('utf-8')
            else:
                raise
        
        # Parse CSS to extract URLs
        # Google Fonts CSS has structure like:
        # /* latin */
        # @font-face {
        #   font-family: 'Inter';
        #   font-style: normal;
        #   font-weight: 400;
        #   src: url(https://fonts.gstatic.com/...woff2);
        # }
        
        font_urls = {}
        
        # Find all @font-face blocks
        font_face_pattern = r'@font-face\s*{([^}]+)}'
        for match in re.finditer(font_face_pattern, css_content):
            block = match.group(1)
            
            # Extract weight, style, and URL (support both woff2 and ttf)
            weight_match = re.search(r'font-weight:\s*(\d+)', block)
            style_match = re.search(r'font-style:\s*(\w+)', block)
            url_match = re.search(r'url\(([^)]+\.(woff2|ttf))', block)
            
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
        
        # Try with standard SSL verification first, fall back to unverified on macOS
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read()
        except (ssl.SSLError, urllib.error.URLError) as e:
            # macOS certificate issue - retry with unverified context
            if 'certificate verify failed' in str(e) or 'SSL' in str(e):
                ssl_context = ssl._create_unverified_context()
                with urllib.request.urlopen(req, timeout=30, context=ssl_context) as response:
                    data = response.read()
            else:
                raise
        
        # Atomic write for safety
        tmp_path = output_path.with_suffix('.tmp')
        try:
            tmp_path.write_bytes(data)
            tmp_path.replace(output_path)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise
    

