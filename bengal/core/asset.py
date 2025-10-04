"""
Asset Object - Handles images, CSS, JS, and other static files.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import hashlib
import shutil


@dataclass
class Asset:
    """
    Represents a static asset file (image, CSS, JS, etc.).
    
    Attributes:
        source_path: Path to the source asset file
        output_path: Path where the asset will be copied
        asset_type: Type of asset (css, js, image, font, etc.)
        fingerprint: Hash-based fingerprint for cache busting
        minified: Whether the asset has been minified
        optimized: Whether the asset has been optimized
    """
    
    source_path: Path
    output_path: Optional[Path] = None
    asset_type: Optional[str] = None
    fingerprint: Optional[str] = None
    minified: bool = False
    optimized: bool = False
    
    def __post_init__(self) -> None:
        """Determine asset type from file extension."""
        if not self.asset_type:
            self.asset_type = self._determine_type()
    
    def _determine_type(self) -> str:
        """
        Determine the asset type from the file extension.
        
        Returns:
            Asset type string
        """
        ext = self.source_path.suffix.lower()
        
        type_map = {
            '.css': 'css',
            '.js': 'javascript',
            '.jpg': 'image',
            '.jpeg': 'image',
            '.png': 'image',
            '.gif': 'image',
            '.svg': 'image',
            '.webp': 'image',
            '.woff': 'font',
            '.woff2': 'font',
            '.ttf': 'font',
            '.eot': 'font',
            '.mp4': 'video',
            '.webm': 'video',
            '.pdf': 'document',
        }
        
        return type_map.get(ext, 'other')
    
    def minify(self) -> 'Asset':
        """
        Minify the asset (for CSS and JS).
        
        Returns:
            Self for method chaining
        """
        if self.asset_type == 'css':
            self._minify_css()
        elif self.asset_type == 'javascript':
            self._minify_js()
        
        self.minified = True
        return self
    
    def _minify_css(self) -> None:
        """Minify CSS content."""
        try:
            import csscompressor
            
            with open(self.source_path, 'r', encoding='utf-8') as f:
                css_content = f.read()
            
            minified_content = csscompressor.compress(css_content)
            
            # Write to a temporary location or update in-memory
            # This would be written during copy_to_output()
            self._minified_content = minified_content
        except ImportError:
            print("Warning: csscompressor not available, skipping CSS minification")
    
    def _minify_js(self) -> None:
        """Minify JavaScript content."""
        try:
            from jsmin import jsmin
            
            with open(self.source_path, 'r', encoding='utf-8') as f:
                js_content = f.read()
            
            minified_content = jsmin(js_content)
            self._minified_content = minified_content
        except ImportError:
            print("Warning: jsmin not available, skipping JS minification")
    
    def hash(self) -> str:
        """
        Generate a hash-based fingerprint for the asset.
        
        Returns:
            Hash string (first 8 characters of SHA256)
        """
        hasher = hashlib.sha256()
        
        with open(self.source_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        
        self.fingerprint = hasher.hexdigest()[:8]
        return self.fingerprint
    
    def optimize(self) -> 'Asset':
        """
        Optimize the asset (especially for images).
        
        Returns:
            Self for method chaining
        """
        if self.asset_type == 'image':
            self._optimize_image()
        
        self.optimized = True
        return self
    
    def _optimize_image(self) -> None:
        """Optimize image assets."""
        try:
            from PIL import Image
            
            img = Image.open(self.source_path)
            
            # Basic optimization - could be expanded
            if img.mode in ('RGBA', 'LA'):
                # Keep alpha channel
                pass
            else:
                # Convert to RGB if needed
                img = img.convert('RGB')
            
            # Store optimized image (would be saved during copy_to_output)
            self._optimized_image = img
        except ImportError:
            print("Warning: Pillow not available, skipping image optimization")
        except Exception as e:
            print(f"Warning: Could not optimize image {self.source_path}: {e}")
    
    def copy_to_output(self, output_dir: Path, use_fingerprint: bool = True) -> Path:
        """
        Copy the asset to the output directory.
        
        Args:
            output_dir: Output directory path
            use_fingerprint: Whether to include fingerprint in filename
            
        Returns:
            Path where the asset was copied
        """
        # Generate fingerprint if requested and not already done
        if use_fingerprint and not self.fingerprint:
            self.hash()
        
        # Determine output filename
        if use_fingerprint and self.fingerprint:
            filename = f"{self.source_path.stem}.{self.fingerprint}{self.source_path.suffix}"
        else:
            filename = self.source_path.name
        
        # Determine output path maintaining directory structure
        if self.output_path:
            output_path = output_dir / self.output_path
        else:
            output_path = output_dir / filename
        
        # Create parent directories
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy or write optimized/minified content atomically
        if hasattr(self, '_minified_content'):
            # Write minified content atomically (crash-safe)
            from bengal.utils.atomic_write import atomic_write_text
            atomic_write_text(output_path, self._minified_content, encoding='utf-8')
        elif hasattr(self, '_optimized_image'):
            # Save optimized image atomically
            tmp_path = output_path.with_suffix(output_path.suffix + '.tmp')
            try:
                self._optimized_image.save(tmp_path, optimize=True, quality=85)
                tmp_path.replace(output_path)
            except Exception:
                tmp_path.unlink(missing_ok=True)
                raise
        else:
            # Simple copy (shutil.copy2 is already safe for most cases)
            shutil.copy2(self.source_path, output_path)
        
        self.output_path = output_path
        return output_path
    
    def __repr__(self) -> str:
        return f"Asset(type='{self.asset_type}', source='{self.source_path.name}')"

