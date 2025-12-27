# RFC: Hugo-Inspired Features for Bengal

**Status**: Draft  
**Created**: 2025-12-26  
**Updated**: 2025-12-26  
**Priority**: Medium-High  
**Effort**: ~4-5 weeks total  
**Impact**: High - Completes the "Hugo for Python" vision  
**Category**: Core / Assets / Templates / DX  
**Scope**: Multiple packages

---

## Executive Summary

Bengal was inspired by Hugo's pragmatic philosophy: speed matters, batteries included, content first. While Bengal has successfully brought many Hugo concepts to Python—and improved on several (scoping, slots, pattern matching)—some key Hugo features remain missing.

This RFC identifies the remaining gaps and proposes implementations that fit Bengal's architecture while delivering the developer experience Hugo users love.

---

## The Hugo DNA Already in Bengal

| Hugo Concept | Bengal Implementation | Status |
|:-------------|:----------------------|:------:|
| Unified `end` | `{% end %}` for all blocks | ✅ |
| Live reload | SSE-based hot reload | ✅ |
| Content-first | Markdown + frontmatter | ✅ |
| Taxonomies | Tags, categories, custom | ✅ |
| Asset fingerprinting | AssetManifest | ✅ |
| CSS/JS minification | Asset pipeline | ✅ |
| SCSS compilation | Node pipeline (optional) | ✅ |
| Themes via packages | Entry point discovery | ✅ |
| Shortcodes | Directive system | ✅ |
| `with` block (Jinja-style) | `{% with var=expr %}` | ✅ |
| Nil resilience | Planned (RFC exists) | 🔄 |

---

## What's Still Missing

### Feature Priority Matrix

| Feature | Hugo Equivalent | Impact | Effort | Priority |
|:--------|:----------------|:------:|:------:|:--------:|
| **Image Processing Pipeline** | `resources.Fill/Fit/Resize` | ⭐⭐⭐ | 2 weeks | P0 |
| **Page Resources** | Page bundles | ⭐⭐⭐ | 4-5 days | P1 |
| **Hugo-style `with`** | `{{ with .Author }}` (falsy skip) | ⭐⭐ | 1 day | P1 |
| **Bengal Modules** | `go.mod` for themes | ⭐⭐ | 1 week | P2 |
| **Scratch Pad** | `$.Scratch.Set/Get` | ⭐ | N/A | P3 |

---

## Dependencies

This RFC requires the following Python packages:

```toml
# pyproject.toml additions
[project.optional-dependencies]
images = [
    "Pillow>=10.0",
]
smartcrop = [
    "Pillow>=10.0",
    "smartcrop-py>=0.3",
]
avif = [
    "Pillow>=10.0",
    "pillow-avif-plugin>=1.3",
]
fast-images = [
    "pyvips>=2.2",
]
```

**Installation tiers**:
- `pip install bengal` — No image processing (URL-only, current behavior)
- `pip install bengal[images]` — Pillow-based processing (recommended)
- `pip install bengal[images,avif]` — Add AVIF format support
- `pip install bengal[fast-images]` — libvips acceleration (advanced)

**Note**: AVIF encoding requires `pillow-avif-plugin` because Pillow doesn't natively support AVIF output. WebP is supported natively in Pillow 10+.

---

## Feature 1: Image Processing Pipeline (P0)

### The Hugo Way

Hugo's image processing is one of its killer features:

```go
{{ $image := resources.Get "images/hero.jpg" }}
{{ $resized := $image.Fill "800x600 webp q80" }}
{{ $thumbnail := $image.Fit "200x200" }}

<img src="{{ $resized.RelPermalink }}"
     srcset="{{ $resized.RelPermalink }} 800w, {{ $thumbnail.RelPermalink }} 200w"
     width="{{ $resized.Width }}"
     height="{{ $resized.Height }}">
```

Key features:
- **On-demand processing**: Images resized at build time
- **Caching**: Processed images cached across builds
- **Multiple formats**: WebP, AVIF conversion
- **Smart cropping**: Center, smart (face detection), anchor points
- **Responsive generation**: Multiple sizes in one call

### Current Bengal State

```jinja2
{# Bengal today - URL generation only, no actual processing #}
{{ image_url('hero.jpg', width=800) }}
{# → /assets/hero.jpg?w=800 (but the image isn't actually resized!) #}

{{ image_srcset('hero.jpg', [400, 800, 1200]) }}
{# → hero.jpg?w=400 400w, hero.jpg?w=800 800w... (no actual resizing) #}
```

**Problem**: Bengal generates URLs with size parameters but doesn't actually process images. This means:
- No actual file size reduction
- CDN or browser must do the work
- No format conversion (WebP, AVIF)
- No intelligent cropping

### Proposed Solution

#### 1. Image Resource Model

```python
# bengal/core/resources/image.py

@dataclass
class ImageResource:
    """Processed image resource with caching and lazy processing.

    Inspired by Hugo's resources.Get + processing methods.
    """
    source_path: Path
    site: Site

    # Cached properties
    _width: int | None = None
    _height: int | None = None
    _hash: str | None = None

    @property
    def width(self) -> int:
        """Get image width (loads image if needed)."""
        if self._width is None:
            self._load_dimensions()
        return self._width

    @property
    def height(self) -> int:
        """Get image height (loads image if needed)."""
        if self._height is None:
            self._load_dimensions()
        return self._height

    def fill(self, spec: str) -> ProcessedImage | None:
        """Resize and crop to exact dimensions.

        Args:
            spec: "WIDTHxHEIGHT [format] [quality] [anchor]"
                  e.g., "800x600", "800x600 webp q80", "800x600 smart"

        Returns:
            ProcessedImage with output path and metadata, or None on error

        Example:
            {{ image.fill("800x600 webp q80 center") }}

        Note:
            Returns None (not raises) for graceful template handling.
            See: rfc-kida-resilient-error-handling.md
        """
        return self._process("fill", spec)

    def fit(self, spec: str) -> ProcessedImage | None:
        """Resize to fit within dimensions, preserving aspect ratio.

        The image is scaled down to fit within the box, but won't be
        upscaled or cropped.

        Args:
            spec: "WIDTHxHEIGHT [format] [quality]"

        Example:
            {{ image.fit("400x400 webp") }}
        """
        return self._process("fit", spec)

    def resize(self, spec: str) -> ProcessedImage | None:
        """Resize to width or height, preserving aspect ratio.

        Args:
            spec: "WIDTHx" or "xHEIGHT" or "WIDTHxHEIGHT"

        Example:
            {{ image.resize("800x") }}  # 800px wide, height auto
            {{ image.resize("x600") }}  # 600px tall, width auto
        """
        return self._process("resize", spec)

    def filter(self, *filters: str) -> ProcessedImage | None:
        """Apply image filters.

        Args:
            filters: Filter names with optional args
                     "grayscale", "blur 5", "brightness 1.2"

        Example:
            {{ image.filter("grayscale", "blur 2") }}
        """
        return self._process("filter", " ".join(filters))


@dataclass
class ProcessedImage:
    """Result of image processing operation."""
    source: ImageResource
    output_path: Path
    rel_permalink: str  # URL to use in templates
    width: int
    height: int
    format: str  # jpeg, png, webp, avif
    file_size: int

    def __str__(self) -> str:
        """Return URL for easy template usage."""
        return self.rel_permalink
```

#### 2. Template Functions

```python
# bengal/rendering/template_functions/resources.py

def register(env: Environment, site: Site) -> None:
    """Register Hugo-style resource functions."""

    def resources_get(path: str) -> ImageResource | None:
        """Get an image resource by path.

        Example:
            {% let hero = resources.get("images/hero.jpg") %}
            {{ hero.fill("800x600 webp") }}

        Returns:
            ImageResource or None if file doesn't exist.
        """
        full_path = site.root_path / "assets" / path
        if not full_path.exists():
            logger.warning(
                "resource_not_found",
                path=path,
                searched=str(full_path),
            )
            return None
        return ImageResource(source_path=full_path, site=site)

    def resources_match(pattern: str) -> list[ImageResource]:
        """Get all resources matching a glob pattern.

        Example:
            {% for img in resources.match("gallery/*.jpg") %}
                {{ img.fit("400x300") }}
            {% end %}
        """
        assets_dir = site.root_path / "assets"
        matches = assets_dir.glob(pattern)
        return [ImageResource(p, site) for p in matches if p.is_file()]

    env.globals.update({
        "resources": {
            "get": resources_get,
            "match": resources_match,
        }
    })
```

#### 3. Processing Backend

```python
# bengal/core/resources/processor.py

# Cache schema version - bump when cache format changes
CACHE_SCHEMA_VERSION = 1

@dataclass
class ProcessParams:
    """Parsed image processing parameters."""
    width: int | None = None
    height: int | None = None
    format: str | None = None
    quality: int = 85
    anchor: str = "center"


class ImageProcessor:
    """Image processing with caching.

    Uses Pillow for processing, with optional libvips for performance.
    Caches processed images in .bengal/image-cache/.

    Thread Safety:
        Uses atomic file writes to prevent corruption during parallel builds.
        Cache reads are lock-free; writes use tempfile + rename pattern.

    Memory Management:
        For images >10MP, uses chunked processing via PIL.Image.draft()
        to reduce peak memory usage.
    """

    CACHE_DIR = ".bengal/image-cache"
    LARGE_IMAGE_THRESHOLD = 10_000_000  # 10 megapixels

    def __init__(self, site: Site):
        self.site = site
        self.cache_dir = site.root_path / self.CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()

    def process(
        self,
        source: Path,
        operation: str,
        spec: str,
    ) -> ProcessedImage | None:
        """Process image with caching.

        Cache key includes:
        - Schema version (for cache invalidation on format changes)
        - Source path + mtime
        - Operation + spec
        - Bengal version (optional, for safety)

        Returns:
            ProcessedImage on success, None on error (logged).
        """
        try:
            cache_key = self._cache_key(source, operation, spec)
            cached = self._get_cached(cache_key)
            if cached:
                return cached

            # Parse spec with validation
            params = self._parse_spec(spec)
            if params is None:
                return None

            # Process image
            result = self._do_process(source, operation, params)

            # Cache result atomically
            self._cache_result_atomic(cache_key, result)

            return result

        except FileNotFoundError:
            logger.error("image_not_found", source=str(source))
            return None
        except PIL.UnidentifiedImageError as e:
            logger.error("image_corrupt", source=str(source), error=str(e))
            return None
        except OSError as e:
            logger.error("image_io_error", source=str(source), error=str(e))
            return None

    def _cache_key(self, source: Path, operation: str, spec: str) -> str:
        """Generate cache key with schema version.

        Format: v{schema}_{source_hash}_{op}_{spec_hash}
        """
        source_stat = source.stat()
        source_id = f"{source}:{source_stat.st_mtime_ns}"

        components = [
            f"v{CACHE_SCHEMA_VERSION}",
            hashlib.md5(source_id.encode()).hexdigest()[:12],
            operation,
            hashlib.md5(spec.encode()).hexdigest()[:8],
        ]
        return "_".join(components)

    def _cache_result_atomic(self, cache_key: str, result: ProcessedImage) -> None:
        """Write cache entry atomically using tempfile + rename.

        This prevents corruption during parallel builds where multiple
        workers might process the same image simultaneously.
        """
        import tempfile

        final_path = self.cache_dir / f"{cache_key}.json"

        # Write to temp file first
        fd, temp_path = tempfile.mkstemp(
            dir=self.cache_dir,
            prefix=f".{cache_key}_",
            suffix=".tmp"
        )
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(result.to_dict(), f)
            # Atomic rename (POSIX guarantees atomicity)
            os.replace(temp_path, final_path)
        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    def _parse_spec(self, spec: str) -> ProcessParams | None:
        """Parse Hugo-style spec string with validation.

        "800x600 webp q80 center" →
        ProcessParams(width=800, height=600, format="webp", quality=80, anchor="center")

        Returns None and logs error for invalid specs.
        """
        parts = spec.split()
        params = ProcessParams()

        for part in parts:
            if "x" in part.lower():
                try:
                    w, h = part.lower().split("x")
                    params.width = int(w) if w else None
                    params.height = int(h) if h else None
                except ValueError:
                    logger.error("invalid_dimension_spec", spec=part)
                    return None
            elif part.lower() in ("webp", "avif", "jpeg", "jpg", "png"):
                params.format = "jpeg" if part.lower() == "jpg" else part.lower()
            elif part.lower().startswith("q") and part[1:].isdigit():
                params.quality = int(part[1:])
            elif part.lower() in ("center", "smart", "top", "bottom", "left", "right",
                                   "topleft", "topright", "bottomleft", "bottomright"):
                params.anchor = part.lower()
            else:
                logger.warning("unknown_spec_part", part=part, full_spec=spec)

        return params

    def _do_process(
        self,
        source: Path,
        operation: str,
        params: ProcessParams,
    ) -> ProcessedImage:
        """Actually process the image using Pillow.

        For large images (>10MP), uses draft mode to reduce memory usage.
        """
        from PIL import Image

        img = Image.open(source)

        # Memory optimization for large images
        if img.width * img.height > self.LARGE_IMAGE_THRESHOLD:
            # Use draft mode to load at reduced resolution
            if params.width and params.height:
                img.draft(img.mode, (params.width * 2, params.height * 2))
                img.load()

        if operation == "fill":
            img = self._fill(img, params)
        elif operation == "fit":
            img = self._fit(img, params)
        elif operation == "resize":
            img = self._resize(img, params)
        elif operation == "filter":
            img = self._apply_filters(img, params)

        # Convert format if needed
        if params.format:
            img = self._convert_format(img, params.format)

        # Save to cache
        output_path = self._save_processed(img, source, params)

        return ProcessedImage(
            source=ImageResource(source, self.site),
            output_path=output_path,
            rel_permalink=self._to_url(output_path),
            width=img.width,
            height=img.height,
            format=params.format or source.suffix[1:],
            file_size=output_path.stat().st_size,
        )

    def _fill(self, img: Image.Image, params: ProcessParams) -> Image.Image:
        """Resize and crop to exact dimensions."""
        from PIL import ImageOps

        target = (params.width, params.height)

        if params.anchor == "smart":
            # Smart cropping (face detection) - use smartcrop library if available
            return self._smart_crop(img, target)
        else:
            # Standard crop with anchor
            centering = self._anchor_to_centering(params.anchor)
            return ImageOps.fit(img, target, method=Image.LANCZOS, centering=centering)

    def _fit(self, img: Image.Image, params: ProcessParams) -> Image.Image:
        """Resize to fit within dimensions."""
        img.thumbnail((params.width, params.height), Image.LANCZOS)
        return img

    def _resize(self, img: Image.Image, params: ProcessParams) -> Image.Image:
        """Resize with aspect ratio preservation."""
        if params.width and not params.height:
            # Width specified, calculate height
            ratio = params.width / img.width
            new_height = int(img.height * ratio)
            return img.resize((params.width, new_height), Image.LANCZOS)
        elif params.height and not params.width:
            # Height specified, calculate width
            ratio = params.height / img.height
            new_width = int(img.width * ratio)
            return img.resize((new_width, params.height), Image.LANCZOS)
        else:
            # Both specified
            return img.resize((params.width, params.height), Image.LANCZOS)

    def _smart_crop(self, img: Image.Image, target: tuple[int, int]) -> Image.Image:
        """Smart cropping with face/feature detection.

        Falls back to center crop if smartcrop-py is not installed.
        """
        try:
            import smartcrop
            sc = smartcrop.SmartCrop()
            result = sc.crop(img, target[0], target[1])
            box = (
                result['top_crop']['x'],
                result['top_crop']['y'],
                result['top_crop']['x'] + result['top_crop']['width'],
                result['top_crop']['y'] + result['top_crop']['height'],
            )
            return img.crop(box).resize(target, Image.LANCZOS)
        except ImportError:
            logger.info(
                "smartcrop_not_available",
                message="Install with: pip install bengal[smartcrop]",
                fallback="center crop",
            )
            from PIL import ImageOps
            return ImageOps.fit(img, target, method=Image.LANCZOS)

    def _anchor_to_centering(self, anchor: str) -> tuple[float, float]:
        """Convert anchor name to PIL centering tuple."""
        anchors = {
            "center": (0.5, 0.5),
            "top": (0.5, 0.0),
            "bottom": (0.5, 1.0),
            "left": (0.0, 0.5),
            "right": (1.0, 0.5),
            "topleft": (0.0, 0.0),
            "topright": (1.0, 0.0),
            "bottomleft": (0.0, 1.0),
            "bottomright": (1.0, 1.0),
        }
        return anchors.get(anchor, (0.5, 0.5))
```

#### 4. Template Usage

```jinja2
{# Get a single image resource #}
{% let hero = resources.get("images/hero.jpg") %}

{# Fill: resize and crop to exact dimensions #}
{% if hero %}
<img src="{{ hero.fill('1200x630 webp q85') }}"
     width="1200" height="630"
     alt="Hero image">
{% end %}

{# Fit: resize to fit within box, preserve aspect ratio #}
{% let thumb = hero.fit('400x400 webp') %}
{% if thumb %}
<img src="{{ thumb }}"
     width="{{ thumb.width }}"
     height="{{ thumb.height }}">
{% end %}

{# Resize: specify one dimension, other is calculated #}
{{ hero.resize('800x') }}  {# 800px wide, height auto #}

{# Responsive images with srcset #}
{% let sizes = [400, 800, 1200, 1600] %}
<img src="{{ hero.fill('800x600 webp') }}"
     srcset="{% for w in sizes %}{{ hero.fill(w ~ 'x webp') }} {{ w }}w{% if not loop.last %}, {% end %}{% end %}"
     sizes="(max-width: 600px) 100vw, 800px"
     alt="Responsive hero">

{# Gallery with processed images #}
{% for img in resources.match("gallery/*.jpg") %}
<figure>
  <a href="{{ img.fill('1600x1200') }}">
    <img src="{{ img.fit('300x200 webp q80') }}"
         loading="lazy"
         alt="{{ img.source_path.stem | title }}">
  </a>
</figure>
{% end %}

{# With filters #}
{{ hero.filter("grayscale", "contrast 1.2").resize("400x") }}
```

#### 5. CLI Integration

```bash
# Rebuild image cache
bengal images rebuild

# Show cache stats
bengal images stats
# → Cache version: 1
# → Cached images: 156
# → Cache size: 45.2 MB
# → Cache hits: 1,245 (build), 0 (miss)

# Clear cache
bengal images clear

# Prune unused cached images
bengal images prune

# Validate cache integrity
bengal images validate
```

---

## Feature 2: Page Resources / Page Bundles (P1)

### The Hugo Way

Hugo's page bundles keep content and assets together:

```
content/
  posts/
    my-post/
      index.md           # Leaf bundle (page content)
      hero.jpg           # Page-specific images
      diagram.svg
      data.json          # Page-specific data
    _index.md            # Branch bundle (section index)
```

```go
{{ $hero := .Resources.GetMatch "hero.*" }}
{{ with $hero }}
  <img src="{{ .RelPermalink }}">
{{ end }}
```

### Proposed Bengal Implementation

#### Bundle Detection

Bengal needs to distinguish between:
- **Leaf bundles**: `posts/my-post/index.md` — a single page with co-located resources
- **Branch bundles**: `posts/_index.md` — a section index (no resources)
- **Regular pages**: `posts/my-post.md` — standalone file (no bundle resources)

```python
# bengal/core/page/bundle.py

class BundleType(Enum):
    """Type of content bundle."""
    NONE = "none"        # Regular page (my-post.md)
    LEAF = "leaf"        # Leaf bundle (my-post/index.md)
    BRANCH = "branch"    # Branch bundle (_index.md)


class PageBundleMixin:
    """Mixin providing bundle detection and resource access."""

    @cached_property
    def bundle_type(self) -> BundleType:
        """Determine bundle type from file structure.

        - index.md in directory → LEAF (has resources)
        - _index.md in directory → BRANCH (section, no resources)
        - standalone .md file → NONE
        """
        if self._path.name == "index.md":
            return BundleType.LEAF
        elif self._path.name == "_index.md":
            return BundleType.BRANCH
        else:
            return BundleType.NONE

    @property
    def is_bundle(self) -> bool:
        """True if this page is a leaf bundle with resources."""
        return self.bundle_type == BundleType.LEAF

    @cached_property
    def resources(self) -> PageResources:
        """Get resources co-located with this page.

        For leaf bundles (index.md in directory), returns all
        non-markdown files in the same directory.

        Returns empty PageResources for non-bundles (not an error).
        """
        if not self.is_bundle:
            return PageResources([])

        bundle_dir = self._path.parent
        resources = []

        for path in bundle_dir.iterdir():
            if path.is_file() and path.suffix.lower() not in (".md", ".markdown"):
                resources.append(PageResource(path, self))

        return PageResources(resources)


class PageResources:
    """Collection of resources co-located with a page bundle."""

    def __init__(self, resources: list[PageResource]):
        self._resources = resources
        self._by_name: dict[str, PageResource] = {r.name: r for r in resources}

    def get(self, name: str) -> PageResource | None:
        """Get resource by exact filename."""
        return self._by_name.get(name)

    def get_match(self, pattern: str) -> PageResource | None:
        """Get first resource matching glob pattern.

        Example:
            page.resources.get_match("hero.*")  # hero.jpg, hero.png, etc.
        """
        import fnmatch
        for r in self._resources:
            if fnmatch.fnmatch(r.name, pattern):
                return r
        return None

    def match(self, pattern: str) -> list[PageResource]:
        """Get all resources matching glob pattern."""
        import fnmatch
        return [r for r in self._resources if fnmatch.fnmatch(r.name, pattern)]

    def by_type(self, resource_type: str) -> list[PageResource]:
        """Get resources by MIME type category.

        Args:
            resource_type: "image", "video", "audio", "document", "data"
        """
        type_map = {
            "image": {".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".avif"},
            "video": {".mp4", ".webm", ".mov", ".avi"},
            "audio": {".mp3", ".wav", ".ogg", ".flac"},
            "document": {".pdf", ".doc", ".docx"},
            "data": {".json", ".yaml", ".yml", ".csv", ".xml"},
        }
        extensions = type_map.get(resource_type, set())
        return [r for r in self._resources if r.path.suffix.lower() in extensions]

    def __iter__(self):
        return iter(self._resources)

    def __len__(self):
        return len(self._resources)

    def __bool__(self):
        return len(self._resources) > 0


class PageResource:
    """Single resource co-located with a page."""

    def __init__(self, path: Path, page: Page):
        self.path = path
        self.page = page

    @property
    def name(self) -> str:
        """Filename with extension."""
        return self.path.name

    @property
    def rel_permalink(self) -> str:
        """URL relative to site root."""
        # Resources are served alongside the page
        return f"{self.page.url}{self.name}"

    def as_image(self) -> ImageResource | None:
        """Convert to ImageResource for processing.

        Returns None if not an image file.
        """
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}
        if self.path.suffix.lower() in image_extensions:
            return ImageResource(self.path, self.page._site)
        return None
```

#### Template Usage

```jinja2
{# In a page template #}
{% let hero = page.resources.get_match("hero.*") %}
{% if hero %}
  {# Convert to ImageResource for processing #}
  {% let img = hero.as_image() %}
  <img src="{{ img.fill('1200x630 webp') }}" alt="{{ page.title }}">
{% end %}

{# All images in the bundle #}
{% for resource in page.resources.by_type("image") %}
  {% let img = resource.as_image() %}
  <img src="{{ img.fit('400x300') }}" loading="lazy">
{% end %}

{# Check for specific resource #}
{% if page.resources.get("data.json") %}
  {% let data = page.resources.get("data.json").read_json() %}
  {# Use the data... #}
{% end %}
```

---

## Feature 3: Hugo-style `with` Block (P1)

### Current State

Kida **already has** a `{% with %}` block for temporary variable bindings:

```jinja2
{# Existing Kida syntax (Jinja2-compatible) #}
{% with author = page.metadata.author, site_name = site.title %}
  <span>{{ author.name }} on {{ site_name }}</span>
{% end %}
```

This works well for creating temporary bindings, but differs from Hugo's `with`:

### The Hugo Way

Hugo's `with` has two special behaviors:
1. **Rebinds context**: The expression becomes `.` inside the block
2. **Skips if falsy**: Block doesn't render if expression is falsy

```go
{{ with .Params.author }}
  <div class="author">
    <img src="{{ .avatar }}">
    <span>{{ .name }}</span>
  </div>
{{ end }}
```

### Proposed Extension

Extend Kida's `with` to support Hugo-style `as` binding with implicit nil-check:

```jinja2
{# New Hugo-style syntax: implicit nil-check + binding #}
{% with page.metadata.author as author %}
  <div class="author">
    <img src="{{ author.avatar }}">
    <span>{{ author.name }}</span>
  </div>
{% end %}

{# Even simpler: bind to 'it' by default #}
{% with page.metadata.author %}
  <div class="author">
    <img src="{{ it.avatar }}">
    <span>{{ it.name }}</span>
  </div>
{% end %}

{# Existing Jinja2-style still works #}
{% with x = expr1, y = expr2 %}
  {{ x }} {{ y }}
{% end %}
```

**Key difference from existing `with`**:
- `{% with expr as name %}` — renders only if `expr` is truthy
- `{% with name = expr %}` — always renders (existing behavior)

### Implementation

```python
# bengal/rendering/kida/parser/blocks/special_blocks.py

def _parse_with(self) -> Node:
    """Parse {% with %} in two forms:

    1. Hugo-style: {% with expr %} or {% with expr as name %}
       - Binds expr to 'it' or 'name'
       - Skips body if expr is falsy

    2. Jinja2-style: {% with name = expr, ... %}
       - Creates variable bindings
       - Always renders body
    """
    start = self._advance()  # consume 'with'
    self._push_block("with", start)

    # Peek ahead to determine style
    # Hugo-style: expression followed by 'as' or '%}'
    # Jinja2-style: name followed by '='

    if self._is_hugo_style_with():
        return self._parse_hugo_style_with(start)
    else:
        return self._parse_jinja_style_with(start)

def _is_hugo_style_with(self) -> bool:
    """Detect Hugo-style: {% with expr %} vs Jinja2: {% with x = expr %}."""
    # Save position
    saved = self._save_state()

    # Try to parse as expression
    try:
        self._parse_expression()
        # If next token is 'as' or BLOCK_END, it's Hugo-style
        result = self._current.value == "as" or self._current.type == TokenType.BLOCK_END
    except:
        result = False

    # Restore position
    self._restore_state(saved)
    return result

def _parse_hugo_style_with(self, start: Token) -> WithHugo:
    """Parse {% with expr %} or {% with expr as name %}."""
    expr = self._parse_expression()

    if self._current.value == "as":
        self._advance()  # consume 'as'
        if self._current.type != TokenType.NAME:
            raise self._error("Expected variable name after 'as'")
        name = self._advance().value
    else:
        name = "it"  # Default binding

    self._expect(TokenType.BLOCK_END)
    body = self._parse_body()
    self._consume_end_tag("with")

    return WithHugo(
        lineno=start.lineno,
        col_offset=start.col_offset,
        expr=expr,
        name=name,
        body=tuple(body),
    )
```

**Note**: This requires a new AST node `WithHugo` or modifying the existing `With` node to handle both cases. The compiler generates code that checks truthiness before rendering.

---

## Feature 4: Bengal Modules (P2)

### The Hugo Way

Hugo Modules provide versioned, composable theme/component packages:

```toml
# hugo.toml
[module]
[[module.imports]]
  path = "github.com/theNewDynamic/gohugo-theme-ananke"

[[module.imports]]
  path = "github.com/foo/hugo-shortcode-gallery"
```

Features:
- **Version pinning**: Semantic version constraints
- **Component packages**: Not just themes—shortcodes, partials, assets
- **Mounting**: Mount remote content/assets to local paths
- **Vendoring**: Offline-capable with `hugo mod vendor`

### Current Bengal State

Bengal has entry point discovery for themes:

```toml
# In theme's pyproject.toml
[project.entry-points."bengal.themes"]
acme = "bengal_theme_acme"
```

But:
- No version constraints
- No component packages (just themes)
- No mounting/composition
- No offline vendoring

### Proposed Solution

#### Phase 1: Version Constraints

```yaml
# bengal.yaml
theme: acme>=2.0,<3.0

dependencies:
  - bengal-shortcodes-gallery>=1.0
  - bengal-components-hero~=2.1
```

#### Phase 2: Component Packages

New entry point group for components:

```toml
# pyproject.toml for a component package
[project.entry-points."bengal.components"]
gallery = "bengal_components_gallery"

[project.entry-points."bengal.directives"]
lightbox = "bengal_directives_lightbox:LightboxDirective"
```

```yaml
# bengal.yaml
components:
  - bengal-components-gallery

# In templates, use immediately
{% from "components/gallery" import image_gallery %}
{{ image_gallery(images) }}
```

#### Phase 3: Mounting

```yaml
# bengal.yaml
mounts:
  # Local path mounting only (Phase 3)
  - source: bengal-theme-acme/assets/css/reset.css
    target: assets/css/vendor/reset.css
```

**Note**: Remote mounting (`github:` URLs) deferred to Phase 4 due to security implications.

---

## Feature 5: Scratch Pad (P3)

### The Hugo Way

Hugo's Scratch provides a key-value store for accumulating state:

```go
{{ $.Scratch.Set "total" 0 }}
{{ range .Pages }}
  {{ $.Scratch.Add "total" .WordCount }}
{{ end }}
Total words: {{ $.Scratch.Get "total" }}
```

### Bengal Alternative

Kida's `{% let %}` + `{% export %}` already solves this more elegantly:

```jinja2
{% let total = 0 %}
{% for page in pages %}
  {% export total = total + page.word_count %}
{% end %}
Total words: {{ total }}
```

**Verdict**: Not needed. Kida's scoping is superior to Hugo's Scratch.

---

## Implementation Timeline

### Phase 1: Foundation (1 week)

| Feature | Effort | Deliverable |
|:--------|:------:|:------------|
| Hugo-style `with` | 1 day | `{% with expr as name %}` syntax |
| Bundle detection | 2 days | `page.bundle_type`, `page.is_bundle` |
| PageResources basic | 2 days | `page.resources.get_match()` |

### Phase 2: Image Processing (2 weeks)

| Feature | Effort | Deliverable |
|:--------|:------:|:------------|
| ImageResource model | 2 days | `resources.get()`, `resources.match()` |
| ProcessParams parsing | 1 day | Spec string parser with validation |
| Processing backend | 3 days | `fill`, `fit`, `resize` operations |
| Caching layer | 3 days | Versioned cache with atomic writes |
| Format conversion | 1 day | WebP output (AVIF via plugin) |
| Error handling | 1 day | Graceful failures, nil resilience |
| Tests | 2 days | Unit + integration tests |

### Phase 3: Modules (1 week)

| Feature | Effort | Deliverable |
|:--------|:------:|:------------|
| Version constraints | 2 days | `theme: acme>=2.0` |
| Component packages | 3 days | `bengal.components` entry point |
| Mounting (local) | 2 days | Local path mounting |

---

## Test Plan

### Unit Tests

```python
# tests/test_image_processing.py

class TestSpecParsing:
    """Test Hugo-style spec string parsing."""

    def test_dimensions_only(self):
        params = parse_spec("800x600")
        assert params.width == 800
        assert params.height == 600

    def test_width_only(self):
        params = parse_spec("800x")
        assert params.width == 800
        assert params.height is None

    def test_full_spec(self):
        params = parse_spec("800x600 webp q80 center")
        assert params.width == 800
        assert params.height == 600
        assert params.format == "webp"
        assert params.quality == 80
        assert params.anchor == "center"

    def test_invalid_dimension_returns_none(self):
        params = parse_spec("notanumber")
        assert params is None

    def test_unknown_parts_logged_but_tolerated(self):
        params = parse_spec("800x600 unknownarg")
        assert params.width == 800  # Still works


class TestImageProcessor:
    """Test image processing operations."""

    def test_fill_exact_dimensions(self, tmp_path, sample_image):
        processor = ImageProcessor(mock_site(tmp_path))
        result = processor.process(sample_image, "fill", "100x100")
        assert result.width == 100
        assert result.height == 100

    def test_fit_preserves_aspect_ratio(self, tmp_path, sample_image):
        # sample_image is 200x100
        processor = ImageProcessor(mock_site(tmp_path))
        result = processor.process(sample_image, "fit", "50x50")
        assert result.width == 50
        assert result.height == 25  # Aspect ratio preserved

    def test_cache_hit(self, tmp_path, sample_image):
        processor = ImageProcessor(mock_site(tmp_path))
        result1 = processor.process(sample_image, "fill", "100x100")
        result2 = processor.process(sample_image, "fill", "100x100")
        # Should return same cached result
        assert result1.output_path == result2.output_path

    def test_corrupt_image_returns_none(self, tmp_path):
        corrupt = tmp_path / "corrupt.jpg"
        corrupt.write_bytes(b"not an image")
        processor = ImageProcessor(mock_site(tmp_path))
        result = processor.process(corrupt, "fill", "100x100")
        assert result is None

    def test_atomic_cache_write(self, tmp_path, sample_image):
        """Verify cache writes are atomic (no partial files on crash)."""
        # This is tested by checking no .tmp files remain after processing
        processor = ImageProcessor(mock_site(tmp_path))
        processor.process(sample_image, "fill", "100x100")
        tmp_files = list((tmp_path / ".bengal/image-cache").glob("*.tmp"))
        assert len(tmp_files) == 0


class TestPageResources:
    """Test page bundle resource handling."""

    def test_leaf_bundle_detection(self, tmp_path):
        (tmp_path / "posts/my-post").mkdir(parents=True)
        (tmp_path / "posts/my-post/index.md").write_text("# Hello")
        page = create_page(tmp_path / "posts/my-post/index.md")
        assert page.bundle_type == BundleType.LEAF
        assert page.is_bundle is True

    def test_branch_bundle_detection(self, tmp_path):
        (tmp_path / "posts").mkdir(parents=True)
        (tmp_path / "posts/_index.md").write_text("# Posts")
        page = create_page(tmp_path / "posts/_index.md")
        assert page.bundle_type == BundleType.BRANCH
        assert page.is_bundle is False

    def test_regular_page_detection(self, tmp_path):
        (tmp_path / "posts").mkdir(parents=True)
        (tmp_path / "posts/my-post.md").write_text("# Hello")
        page = create_page(tmp_path / "posts/my-post.md")
        assert page.bundle_type == BundleType.NONE
        assert page.is_bundle is False

    def test_get_match_glob(self, tmp_path):
        (tmp_path / "posts/my-post").mkdir(parents=True)
        (tmp_path / "posts/my-post/index.md").write_text("# Hello")
        (tmp_path / "posts/my-post/hero.jpg").write_bytes(SAMPLE_JPEG)
        (tmp_path / "posts/my-post/hero.png").write_bytes(SAMPLE_PNG)

        page = create_page(tmp_path / "posts/my-post/index.md")
        hero = page.resources.get_match("hero.*")
        assert hero is not None
        assert hero.name in ("hero.jpg", "hero.png")
```

### Integration Tests

```python
# tests/integration/test_image_pipeline.py

def test_full_image_pipeline(bengal_site):
    """End-to-end test of image processing in templates."""
    # Create test image
    (bengal_site / "assets/images/test.jpg").write_bytes(SAMPLE_JPEG)

    # Create template that processes images
    (bengal_site / "templates/test.html").write_text("""
        {% let img = resources.get("images/test.jpg") %}
        {% if img %}
        <img src="{{ img.fill('100x100 webp') }}">
        {% end %}
    """)

    # Build site
    result = bengal_build(bengal_site)

    # Verify output
    assert result.success
    output_html = (bengal_site / "_site/test/index.html").read_text()
    assert 'src="' in output_html
    assert '.webp' in output_html

    # Verify processed image exists
    webp_files = list((bengal_site / "_site").rglob("*.webp"))
    assert len(webp_files) == 1


def test_parallel_image_processing(bengal_site):
    """Verify image processing is thread-safe during parallel builds."""
    # Create many images
    for i in range(20):
        (bengal_site / f"assets/images/img{i}.jpg").write_bytes(SAMPLE_JPEG)

    # Template that processes all images
    (bengal_site / "templates/gallery.html").write_text("""
        {% for img in resources.match("images/*.jpg") %}
        <img src="{{ img.fill('100x100') }}">
        {% end %}
    """)

    # Build with parallelism
    result = bengal_build(bengal_site, jobs=4)

    assert result.success
    # All 20 images should be processed
    processed = list((bengal_site / ".bengal/image-cache").glob("*.jpg"))
    assert len(processed) == 20
```

### Performance Benchmarks

```python
# benchmarks/bench_image_processing.py

def bench_resize_1200px(benchmark, sample_4k_image):
    """Benchmark: Resize 4K image to 1200px wide."""
    processor = ImageProcessor(mock_site())
    benchmark(lambda: processor.process(sample_4k_image, "resize", "1200x"))


def bench_cache_hit(benchmark, sample_image, warm_cache):
    """Benchmark: Cache hit performance."""
    processor = ImageProcessor(mock_site())
    # Warm the cache
    processor.process(sample_image, "fill", "800x600")
    # Benchmark cache hits
    benchmark(lambda: processor.process(sample_image, "fill", "800x600"))


# Target: <100ms for 1200px resize of typical 4K image
# Target: <1ms for cache hit
```

---

## Success Criteria

| Feature | Metric |
|:--------|:-------|
| Image processing | 100% Pillow-based, AVIF via optional plugin |
| Image caching | Cache hit rate >95% on incremental builds |
| Image performance | <100ms for 1200px resize, <1ms cache hit |
| Page resources | Bundle detection with zero page queries |
| Hugo-style `with` | Both syntaxes work, falsy check for `as` form |
| Error handling | All operations return None on error (no exceptions in templates) |
| Parallel safety | No cache corruption under parallel builds |
| Component packages | At least 2 example packages published |

---

## Migration Path

All features are **additive**:
- Existing templates continue working
- Image processing is opt-in (use `resources.get()` when ready)
- Existing `{% with x = expr %}` syntax unchanged
- Theme version constraints are optional
- No breaking changes

---

## Error Handling & Nil Resilience

This RFC integrates with `rfc-kida-resilient-error-handling.md` for graceful degradation:

### Template-Level Resilience

```jinja2
{# resources.get() returns None if file missing #}
{% let img = resources.get("missing.jpg") %}
{% if img %}
  <img src="{{ img.fill('800x600') }}">
{% else %}
  <img src="/placeholder.svg" alt="Image not found">
{% end %}

{# Hugo-style with automatically handles nil #}
{% with resources.get("hero.jpg") as hero %}
  {# Only renders if hero exists #}
  <img src="{{ hero.fill('800x600') }}">
{% end %}

{# Processing methods return None on error #}
{% let result = img.fill('800x600') %}
{{ result ?? '/fallback.jpg' }}
```

### Error Logging

All errors are logged with structured context but don't crash builds:

```python
# Example log output for missing image
{
    "event": "resource_not_found",
    "level": "warning",
    "path": "images/missing.jpg",
    "searched": "/site/assets/images/missing.jpg",
    "template": "pages/index.html",
    "line": 15,
}
```

---

## Open Questions

1. **Smart cropping**: Include face detection in core, or as optional extra?
   - **Decision**: Optional (`pip install bengal[smartcrop]`)

2. **libvips vs Pillow**: Make libvips the default when available?
   - **Decision**: Pillow default, libvips in separate install tier for advanced users
   - **Rationale**: pyvips has complex system dependencies; Pillow works everywhere

3. **Image CDN integration**: Support external image services?
   - **Defer**: Can be added later via URL rewriting hook

4. **Remote mounting**: Support `github:` URLs directly?
   - **Defer** to Phase 4: Security implications need more thought

5. **AVIF support**: Include in base images extra?
   - **Decision**: Separate extra due to plugin dependency

---

## References

### Hugo Documentation
- [Image Processing](https://gohugo.io/content-management/image-processing/)
- [Page Resources](https://gohugo.io/content-management/page-resources/)
- [Hugo Modules](https://gohugo.io/hugo-modules/)
- [Context (The Dot)](https://gohugo.io/templates/introduction/#the-dot)

### Bengal Current State
- `bengal/rendering/template_functions/images.py` - Current image functions
- `bengal/rendering/kida/parser/blocks/special_blocks.py` - Existing `with` implementation
- `bengal/core/theme/registry.py` - Theme entry point discovery
- `bengal/assets/pipeline.py` - Asset pipeline
- `bengal/core/asset/asset_core.py` - Asset processing

### Related RFCs
- `rfc-kida-resilient-error-handling.md` - None resilience (Hugo-style)
- `rfc-kida-modern-syntax-features.md` - Optional chaining (`?.`)
- `rfc-engine-agnostic-context-layer.md` - Context standardization

---

## Appendix: Hugo Feature Parity Checklist

### Completed ✅

- [x] Fast builds with parallelization
- [x] Live reload with CSS-only refresh
- [x] Content-first with frontmatter
- [x] Taxonomies and terms
- [x] Template inheritance
- [x] Asset fingerprinting
- [x] Minification (CSS/JS)
- [x] Shortcodes (directives)
- [x] Theme packages
- [x] i18n (via sections)
- [x] RSS/Atom feeds
- [x] Sitemaps
- [x] 404 pages
- [x] `with` block (Jinja2-style variable bindings)

### In Progress 🔄

- [ ] Nil resilience (RFC exists)
- [ ] Pattern matching (RFC exists)
- [ ] Pipeline operator (RFC exists)

### Proposed in This RFC 📋

- [ ] Image processing pipeline
- [ ] Page bundles / resources
- [ ] Hugo-style `with` (falsy skip + context rebinding)
- [ ] Module version constraints
- [ ] Component packages

### Not Planned ❌

- [ ] Scratch (Kida's scoping is better)
- [ ] Data files (Bengal has this differently)
- [ ] Raw Git info (different architecture)

---

## Changelog

| Date | Change |
|:-----|:-------|
| 2025-12-26 | Initial draft |
| 2025-12-26 | Added: Dependencies section, Test Plan, Error Handling |
| 2025-12-26 | Fixed: `with` block already exists (Jinja-style), clarified Hugo-style extension |
| 2025-12-26 | Added: Cache versioning, atomic writes, memory management |
| 2025-12-26 | Updated: Effort estimates (+1 week for robustness) |
| 2025-12-26 | Added: Bundle detection details (leaf vs branch) |
| 2025-12-26 | Connected: Nil resilience RFC for error handling patterns |
