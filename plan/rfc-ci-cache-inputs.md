# RFC: CI Cache Inputs Command

> **TL;DR**: Add `bengal cache inputs` and `bengal cache hash` commands for correct CI cache keys, plus self-validating autodoc cache as defense-in-depth. Users get correct caching with minimal effort; Bengal catches mistakes automatically.

## Problem

Warm builds require CI cache keys that include **all** build inputs. Currently users must manually construct these, which is error-prone:

```yaml
# Easy to miss autodoc sources, external refs, themes, etc.
key: bengal-${{ hashFiles('uv.lock', 'site/content/**', 'site/config/**') }}
```

**Sharp edge**: If autodoc.yaml points to `../bengal/**/*.py` but the cache key doesn't include it, CI cache hits produce stale autodoc → 404s.

Bengal **already knows** all its inputs from configuration:
- `autodoc.python.source_dirs`
- `autodoc.cli.app_module`
- `autodoc.openapi.spec_file`
- `external_refs.indexes[*].url` (local paths)
- Theme paths
- Content/config directories
- Templates and static assets

## Solution

Add `bengal cache inputs` command that outputs all input globs for cache key construction.

### Usage

```bash
$ cd site && bengal cache inputs
```

**Output** (stdout, one glob per line):
```
content/**
config/**
../bengal/**/*.py
api/openapi.yaml
templates/**
static/**
```

**With verbose mode** (shows source of each input):
```bash
$ bengal cache inputs --verbose
content/**              # built-in
config/**               # built-in
../bengal/**/*.py       # autodoc.python.source_dirs
api/openapi.yaml        # autodoc.openapi.spec_file
templates/**            # custom templates
```

**For CI** (GitHub Actions):
```yaml
- name: Get cache inputs
  id: inputs
  run: |
    cd site
    inputs=$(uv run bengal cache inputs | tr '\n' ' ')
    echo "globs=$inputs" >> $GITHUB_OUTPUT

- name: Cache Bengal build state  
  uses: actions/cache@v4
  with:
    path: site/.bengal
    key: bengal-${{ runner.os }}-${{ hashFiles(steps.inputs.outputs.globs) }}
```

**Or simpler** - generate a hash directly:
```bash
$ bengal cache hash
a1b2c3d4e5f6g7h8
```

```yaml
- name: Get inputs hash
  id: cache
  run: echo "hash=$(cd site && uv run bengal cache hash)" >> $GITHUB_OUTPUT

- name: Cache Bengal build state
  uses: actions/cache@v4
  with:
    path: site/.bengal
    key: bengal-${{ runner.os }}-${{ steps.cache.outputs.hash }}
```

## Implementation

### Phase 1: `bengal cache inputs` (immediate)

```python
# bengal/cli/commands/cache.py
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from bengal.config import SiteConfig


def get_input_globs(config: SiteConfig, site_root: Path) -> list[tuple[str, str]]:
    """
    Return list of (glob_pattern, source_description) tuples.

    Patterns are relative to site_root or use ../ for external paths.
    """
    inputs: list[tuple[str, str]] = []

    # Always include content and config
    inputs.append(("content/**", "built-in"))
    inputs.append(("config/**", "built-in"))

    # Templates (if custom templates directory exists)
    templates_dir = site_root / "templates"
    if templates_dir.exists():
        inputs.append(("templates/**", "custom templates"))

    # Static assets
    static_dir = site_root / "static"
    if static_dir.exists():
        inputs.append(("static/**", "static assets"))

    # Autodoc Python sources
    if config.autodoc.python.enabled:
        for source_dir in config.autodoc.python.source_dirs:
            inputs.append((f"{source_dir}/**/*.py", "autodoc.python.source_dirs"))

    # Autodoc CLI (derive package from app_module)
    if config.autodoc.cli.enabled:
        app_module = config.autodoc.cli.app_module  # e.g., "bengal.cli:main"
        package = app_module.split(":")[0].split(".")[0]
        inputs.append((f"../{package}/**/*.py", "autodoc.cli.app_module"))

    # Autodoc OpenAPI
    if config.autodoc.openapi.enabled:
        inputs.append((config.autodoc.openapi.spec_file, "autodoc.openapi.spec_file"))

    # External refs (local index paths only)
    if config.external_refs.enabled:
        for idx in config.external_refs.indexes:
            if not idx.url.startswith(("http://", "https://")):
                inputs.append((idx.url, "external_refs.indexes"))

    # Theme (if external path)
    if config.theme.path:
        inputs.append((f"{config.theme.path}/**", "theme.path"))

    return inputs


@click.group("cache", cls=BengalGroup)
def cache_cli() -> None:
    """Cache management commands."""
    pass


@cache_cli.command("inputs")
@click.option("--format", "output_format", type=click.Choice(["lines", "json"]), default="lines")
@click.option("--verbose", "-v", is_flag=True, help="Show source of each input pattern")
def inputs(output_format: str, verbose: bool) -> None:
    """
    List all input paths/globs that affect the build.

    Use this to construct CI cache keys that properly invalidate
    when any build input changes.

    Examples:
        bengal cache inputs
        bengal cache inputs --verbose
        bengal cache inputs --format json
    """
    site = load_site_from_cli(...)
    input_globs = get_input_globs(site.config, site.root_path)

    if output_format == "json":
        if verbose:
            click.echo(json.dumps([{"pattern": p, "source": s} for p, s in input_globs], indent=2))
        else:
            click.echo(json.dumps([p for p, _ in input_globs], indent=2))
    else:
        for pattern, source in input_globs:
            if verbose:
                click.echo(f"{pattern:<30} # {source}")
            else:
                click.echo(pattern)
```

### Phase 2: `bengal cache hash` (follow-up)

Computes a single deterministic hash from all input files:

```python
import bengal

@cache_cli.command("hash")
@click.option("--include-version/--no-include-version", default=True,
              help="Include Bengal version in hash (recommended)")
def cache_hash(include_version: bool) -> None:
    """
    Compute deterministic hash of all build inputs.

    Use this as a CI cache key for accurate invalidation.
    The hash includes:
    - All input file contents
    - Relative file paths (for determinism)
    - Bengal version (by default)

    Examples:
        bengal cache hash
        bengal cache hash --no-include-version
    """
    site = load_site_from_cli(...)
    input_globs = get_input_globs(site.config, site.root_path)

    hasher = hashlib.sha256()

    # Include Bengal version for cache invalidation on upgrades
    if include_version:
        hasher.update(f"bengal:{bengal.__version__}".encode())

    # Resolve and hash all matching files
    for glob_pattern, source in input_globs:
        # Validate pattern - reject deeply nested parent paths
        if glob_pattern.count("../") > 1:
            click.echo(f"Warning: Skipping unsupported pattern '{glob_pattern}' (nested ../ not supported)", err=True)
            continue

        # Handle ../ patterns by resolving from site root
        if glob_pattern.startswith("../"):
            base_path = site.root_path.parent
            resolved_pattern = glob_pattern[3:]  # Strip ../
        else:
            base_path = site.root_path
            resolved_pattern = glob_pattern

        matched_files = sorted(base_path.glob(resolved_pattern))

        for file_path in matched_files:
            if not file_path.is_file():
                continue

            # Resolve symlinks for consistent hashing
            file_path = file_path.resolve()

            # Hash relative path for determinism across machines
            try:
                rel_path = file_path.relative_to(site.root_path.resolve())
            except ValueError:
                # File is outside site root (e.g., ../bengal/)
                try:
                    rel_path = file_path.relative_to(site.root_path.parent.resolve())
                except ValueError:
                    # Fallback: use absolute path (rare edge case)
                    rel_path = file_path

            try:
                hasher.update(rel_path.as_posix().encode())
            hasher.update(file_path.read_bytes())
            except (OSError, IOError) as e:
                raise click.ClickException(f"Cannot read file '{file_path}': {e}")

    click.echo(hasher.hexdigest()[:16])
```

### Phase 3: Write manifest after build (optional)

Generate `.bengal/inputs.manifest` during build:

```json
{
  "version": 1,
  "bengal_version": "0.1.8",
  "generated": "2026-01-12T10:30:00Z",
  "inputs": {
    "content": ["content/**"],
    "config": ["config/**"],
    "autodoc_python": ["../bengal/**/*.py"],
    "autodoc_openapi": ["api/openapi.yaml"],
    "templates": ["templates/**"],
    "static": ["static/**"]
  },
  "hash": "a1b2c3d4e5f6g7h8"
}
```

CI can use this for subsequent builds (chicken-and-egg for first build).

### Phase 4: Self-Validating Cache (defense in depth)

Make the cache self-validating like Sphinx, so warm builds are robust even with incorrect CI cache keys.

**How Sphinx Does It**: When Sphinx encounters an autodoc directive, it imports the Python module and records the dependency. On subsequent builds, it checks if the source file changed and invalidates affected pages.

**Bengal Equivalent**: During autodoc extraction, store source file hashes in the cache. During incremental build, validate those hashes match current files.

```python
# bengal/cache/build_cache/autodoc_tracking.py
from __future__ import annotations

from dataclasses import field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.site import Site


class AutodocTrackingMixin:
    """Track autodoc source file to page dependencies WITH hash validation."""

    # Existing: source_file → set of autodoc page paths
    autodoc_dependencies: dict[str, set[str]] = field(default_factory=dict)

    # NEW: source_file → (content_hash, mtime) for self-validation
    # Using tuple allows mtime-first optimization (skip hash if mtime unchanged)
    autodoc_source_metadata: dict[str, tuple[str, float]] = field(default_factory=dict)

    def _normalize_source_path(self, source_file: Path | str, site_root: Path) -> str:
        """
        Normalize source path for consistent cache keys.

        Converts absolute paths to relative (from site parent) when possible.
        This ensures cache hits across different checkout locations.
        """
        path = Path(source_file)
        if path.is_absolute():
            try:
                return str(path.relative_to(site_root.parent))
            except ValueError:
                # External path outside repo - keep absolute
                return str(path)
        return str(path)

    def add_autodoc_dependency(
        self,
        source_file: Path | str,
        autodoc_page: Path | str,
        site_root: Path,
        source_hash: str | None = None,
        source_mtime: float | None = None,
    ) -> None:
        """
        Register that source_file produces autodoc_page.

        Args:
            source_file: Path to the Python/OpenAPI source file
            autodoc_page: Path to the generated autodoc page
            site_root: Site root path for normalization
            source_hash: Content hash for validation
            source_mtime: File mtime for fast staleness check
        """
        source_key = self._normalize_source_path(source_file, site_root)
        page_key = str(autodoc_page)

        if source_key not in self.autodoc_dependencies:
            self.autodoc_dependencies[source_key] = set()
        self.autodoc_dependencies[source_key].add(page_key)

        # Store metadata for self-validation
        if source_hash is not None and source_mtime is not None:
            self.autodoc_source_metadata[source_key] = (source_hash, source_mtime)

    def get_affected_autodoc_pages(self, source_file: str) -> set[str]:
        """
        Get all autodoc pages generated from a source file.

        Args:
            source_file: Normalized source file path

        Returns:
            Set of autodoc page paths that depend on this source
        """
        return self.autodoc_dependencies.get(source_file, set())

    def get_stale_autodoc_sources(self, site_root: Path) -> set[str]:
        """
        Validate autodoc sources and return paths that have changed.

        Uses mtime-first optimization: only computes hash if mtime changed.
        This enables cache self-validation independent of CI cache keys.

        Args:
            site_root: Site root path for resolving relative paths

        Returns:
            Set of source file paths whose content has changed since caching
        """
        from bengal.utils.hashing import hash_file

        # Handle cache migration: old caches have dependencies but no metadata
        if not self.autodoc_source_metadata and self.autodoc_dependencies:
            logger.info(
                "autodoc_cache_migration",
                msg="No source metadata found (pre-v0.1.8 cache), marking all autodoc stale",
                source_count=len(self.autodoc_dependencies),
            )
            return set(self.autodoc_dependencies.keys())

        stale_sources: set[str] = set()

        for source_key, (stored_hash, stored_mtime) in self.autodoc_source_metadata.items():
            # Resolve path relative to site parent (where ../ paths live)
            if source_key.startswith("../") or not Path(source_key).is_absolute():
                source = site_root.parent / source_key
            else:
                source = Path(source_key)

            if not source.exists():
                # Source deleted - mark as stale for cleanup
                stale_sources.add(source_key)
                continue

            # mtime-first optimization: skip hash if mtime unchanged
            current_mtime = source.stat().st_mtime
            if current_mtime == stored_mtime:
                continue  # Fast path: file unchanged

            # mtime changed - verify with hash (handles touch without content change)
            current_hash = hash_file(source)
            if current_hash != stored_hash:
                stale_sources.add(source_key)

        return stale_sources
```

**Usage in IncrementalOrchestrator**:

```python
# bengal/orchestration/incremental/orchestrator.py

def detect_changes(self) -> ChangeSet:
    """Detect what needs rebuilding, including autodoc self-validation."""

    # ... existing change detection ...

    # NEW: Self-validate autodoc sources
    stale_autodoc = self.cache.get_stale_autodoc_sources(self.site.root_path)
    if stale_autodoc:
        logger.info(
            "autodoc_sources_changed",
            count=len(stale_autodoc),
            sources=list(stale_autodoc)[:5],  # First 5 for brevity
        )

        # Get all pages affected by stale sources
        for source in stale_autodoc:
            affected_pages = self.cache.get_affected_autodoc_pages(source)
            changes.invalidated_pages.update(affected_pages)

    return changes
```

**Autodoc extraction integration**:

```python
# bengal/autodoc/python/extractor.py

def extract_module(self, module_path: Path) -> AutodocPage:
    """Extract documentation from a Python module."""
    page = self._do_extraction(module_path)

    # Register dependency with hash for self-validation
    from bengal.utils.hashing import hash_file

    self.cache.add_autodoc_dependency(
        source_file=module_path,
        autodoc_page=page.output_path,
        site_root=self.site.root_path,
        source_hash=hash_file(module_path),
        source_mtime=module_path.stat().st_mtime,
    )

    return page
```

**Benefits**:
- **Defense in depth**: Catches stale autodoc even if CI cache key is wrong
- **Correctness guarantee**: Autodoc pages always reflect current source
- **No user action required**: Works automatically without CLI commands
- **Graceful degradation**: If validation detects stale data, rebuilds affected pages only

**Shared hashing utility** (used by both CLI and self-validation):

```python
# bengal/utils/hashing.py
from __future__ import annotations

import hashlib
from pathlib import Path


def hash_file(path: Path) -> str:
    """
    Compute SHA-256 hash of file contents.

    Returns truncated 16-char hex string for compact storage.
    Used by both `bengal cache hash` and autodoc self-validation.
    """
    hasher = hashlib.sha256()
    hasher.update(path.read_bytes())
    return hasher.hexdigest()[:16]
```

**Tradeoffs**:
- Slightly more cache I/O (reading source metadata)
- Slightly larger cache file (storing hash + mtime per source)
- Requires hashing source files during autodoc extraction
- mtime-first optimization minimizes hash computation overhead

**Why Both CLI + Self-Validation?**

| Approach | Guarantees Correctness | User Effort | Performance |
|----------|----------------------|-------------|-------------|
| `bengal cache hash` (CLI) | ✅ Cache miss on change | Requires CI setup | Fastest (full cache hit) |
| Self-validating cache | ✅ Detects stale autodoc | Zero | Slight overhead |
| Both together | ✅✅ Defense in depth | Minimal | Optimal |

The CLI commands help users get cache keys right. Self-validation is a safety net that catches mistakes.

## CI Template

Provide a ready-to-use workflow in docs:

```yaml
# .github/workflows/pages.yml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          python-version: "3.14"

      - name: Install bengal
        run: uv sync

      # Key step: Get inputs hash for accurate cache invalidation
      - name: Get cache hash
        id: cache
        working-directory: site
        run: echo "hash=$(uv run bengal cache hash)" >> $GITHUB_OUTPUT

      - name: Cache Bengal build state
        uses: actions/cache@v4
        with:
          path: site/.bengal
          key: bengal-${{ runner.os }}-${{ steps.cache.outputs.hash }}
          # No restore-keys - we want exact match for correctness

      - name: Build site
        working-directory: site
        run: uv run bengal site build --environment production

      # ... deploy steps
```

## Input Sources (Complete List)

| Input | Glob Pattern | Source |
|-------|--------------|--------|
| Content files | `content/**` | Built-in |
| Config files | `config/**` | Built-in |
| Custom templates | `templates/**` | Directory presence |
| Static assets | `static/**` | Directory presence |
| Python sources | `{source_dir}/**/*.py` | `autodoc.python.source_dirs` |
| CLI package | `../{package}/**/*.py` | `autodoc.cli.app_module` |
| OpenAPI spec | `{spec_file}` | `autodoc.openapi.spec_file` |
| Local intersphinx | `{url}` | `external_refs.indexes[*].url` |
| External theme | `{path}/**` | `theme.path` |
| Bengal version | (in hash only) | `bengal.__version__` |

## Benefits

1. **Correctness**: Cache invalidates when any input changes
2. **Simplicity**: One command, users don't need to understand all inputs
3. **Discoverability**: `bengal cache inputs --verbose` shows what affects the build
4. **Flexibility**: Works with any CI system (GitHub Actions, GitLab CI, etc.)
5. **Determinism**: Hash includes paths and version for reproducibility

## How Other SSGs Handle This

| SSG | Approach | Notes |
|-----|----------|-------|
| **Hugo** | Cache `resources/_gen/` only | No autodoc, content is self-contained. No sharp edge. |
| **Jekyll** | Cache `.jekyll-cache/`, `vendor/bundle/` | No autodoc, content is self-contained. No sharp edge. |
| **Eleventy** | Cache `node_modules/` only | Pure content SSG. No sharp edge. |
| **Gatsby** | Cache `.cache/` and `public/` | Has same edge with source plugins. GraphQL sources must be explicit. |
| **Sphinx** | **Runtime import tracking** | Tracks Python imports during autodoc. If source changes, invalidates affected pages. Self-validating. |
| **MkDocs + mkdocstrings** | No incremental builds | Always full rebuild. Avoids issue by being slow. |
| **Docusaurus** | TypeDoc plugins rebuild every time | API doc plugins don't cache. Avoids issue by not caching. |

**Key Insight**: Most SSGs don't have this problem because they don't generate content from external sources. Bengal combines:
- Warm builds (like Hugo/Gatsby)
- Autodoc from external sources (like Sphinx)
- CI-friendly caching (like modern SSGs)

**Bengal's Approach** (this RFC):
1. **CLI commands** (`cache inputs`, `cache hash`) - Help users construct correct CI cache keys
2. **Self-validating cache** (Phase 4) - Sphinx-style runtime validation as defense in depth

## Alternatives Considered

### 1. Always invalidate on package version change

Include `pyproject.toml` or `uv.lock` in cache key. Downside: Invalidates on unrelated dependency changes.

### 2. Manual documentation only

Document the patterns users need. Downside: Error-prone, varies by project.

### 3. Disable warm builds by default

Force full rebuilds in CI. Downside: Loses performance benefits.

### 4. Runtime-only validation (Sphinx approach)

Don't provide CLI commands, only self-validate at runtime. Downside: Cache hits still occur, then invalidation happens during build. Less efficient than avoiding cache hit entirely. Also doesn't help users understand what affects their build.

### 5. No autodoc caching

Always regenerate autodoc pages (MkDocs approach). Downside: Loses warm build benefits for large codebases with many autodoc pages.

## Design Decisions

### Q: Include Bengal version in hash?

**Decision**: Yes, by default.

Cache should invalidate on upgrades since rendering behavior may change. Users can opt out with `--no-include-version` for testing.

### Q: Support `.bengalcacheignore`?

**Decision**: No (YAGNI).

Adds complexity without demonstrated need. Revisit if users request it.

### Q: Resolve globs or output patterns?

**Decision**: Both.

- `bengal cache inputs` outputs **patterns** (for CI tools that accept globs)
- `bengal cache hash` resolves **files** (for accurate hashing)

### Q: Validate all autodoc sources or only changed files?

**Decision**: Validate all tracked sources on every incremental build, with mtime-first optimization.

- Checking mtime is cheap (single stat call per source)
- Only computes hash when mtime differs
- Guarantees correctness: never serves stale autodoc
- Overhead is negligible for typical projects (<1000 source files)

## Migration

1. **Immediate**: Fix Bengal's own CI (done - added `bengal/**/*.py` to cache key)
2. **v0.1.8**: Ship `bengal cache inputs` and `bengal cache hash` (Phases 1-2)
3. **v0.1.8**: Ship self-validating autodoc cache (Phase 4) - defense in depth
4. **Docs**: Update CI/deployment docs with recommended patterns
5. **Example sites**: Update example-sites/ with correct cache keys

## Edge Cases

### Missing directories

If `content/` or `config/` don't exist, the command still outputs the patterns. The hash command gracefully handles non-matching globs (empty set).

### Nested parent paths

Patterns like `../../other` are not supported. If `autodoc.python.source_dirs` contains such paths, emit a warning and skip. This limitation is documented.

### Unreadable files

If a file can't be read (permissions, encoding), `cache hash` fails with a clear error message including the file path:

```
Error: Cannot read file '../bengal/binary.pyc': [Errno 13] Permission denied
```

### Symlinks

Symlinks are followed and resolved. The relative path in the hash is the symlink target's path, not the symlink itself. This ensures consistency across machines with different symlink configurations.

### Renamed autodoc source files

If a source file is renamed (e.g., `module.py` → `utils.py`):
- Old path marked stale (file doesn't exist)
- New path not tracked until next build extracts it
- Affected autodoc pages rebuild correctly from new location

This is correct behavior - stale detection triggers rebuild, which re-extracts from the renamed file and registers the new dependency.

## Test Plan

```python
# tests/cli/test_cache.py

def test_cache_inputs_includes_content_and_config(site_factory):
    """Always includes content/** and config/**."""
    site = site_factory()
    result = runner.invoke(cache_cli, ["inputs"], obj=site)
    assert "content/**" in result.output
    assert "config/**" in result.output


def test_cache_inputs_includes_autodoc_sources(site_factory):
    """Includes Python source dirs when autodoc enabled."""
    site = site_factory(autodoc_python={"enabled": True, "source_dirs": ["../src"]})
    result = runner.invoke(cache_cli, ["inputs"], obj=site)
    assert "../src/**/*.py" in result.output


def test_cache_inputs_verbose_shows_sources(site_factory):
    """--verbose shows source of each pattern."""
    site = site_factory()
    result = runner.invoke(cache_cli, ["inputs", "--verbose"], obj=site)
    assert "# built-in" in result.output


def test_cache_inputs_json_format(site_factory):
    """--format json outputs valid JSON."""
    site = site_factory()
    result = runner.invoke(cache_cli, ["inputs", "--format", "json"], obj=site)
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert "content/**" in data


def test_cache_inputs_handles_parent_paths(site_factory):
    """Correctly handles ../ patterns for CLI autodoc."""
    site = site_factory(autodoc_cli={"enabled": True, "app_module": "myapp.cli:main"})
    result = runner.invoke(cache_cli, ["inputs"], obj=site)
    assert "../myapp/**/*.py" in result.output


def test_cache_hash_deterministic(site_factory):
    """Same inputs produce same hash across runs."""
    site = site_factory()
    result1 = runner.invoke(cache_cli, ["hash"], obj=site)
    result2 = runner.invoke(cache_cli, ["hash"], obj=site)
    assert result1.output == result2.output


def test_cache_hash_changes_on_file_change(site_factory, tmp_path):
    """Hash changes when any input file changes."""
    site = site_factory()
    result1 = runner.invoke(cache_cli, ["hash"], obj=site)

    # Modify a content file
    (site.root_path / "content" / "index.md").write_text("changed")
    result2 = runner.invoke(cache_cli, ["hash"], obj=site)

    assert result1.output != result2.output


def test_cache_hash_includes_version(site_factory, monkeypatch):
    """Hash includes Bengal version by default."""
    site = site_factory()

    monkeypatch.setattr("bengal.__version__", "0.1.0")
    result1 = runner.invoke(cache_cli, ["hash"], obj=site)

    monkeypatch.setattr("bengal.__version__", "0.2.0")
    result2 = runner.invoke(cache_cli, ["hash"], obj=site)

    assert result1.output != result2.output


def test_cache_hash_no_version_flag(site_factory, monkeypatch):
    """--no-include-version excludes version from hash."""
    site = site_factory()

    monkeypatch.setattr("bengal.__version__", "0.1.0")
    result1 = runner.invoke(cache_cli, ["hash", "--no-include-version"], obj=site)

    monkeypatch.setattr("bengal.__version__", "0.2.0")
    result2 = runner.invoke(cache_cli, ["hash", "--no-include-version"], obj=site)

    assert result1.output == result2.output


def test_cache_hash_empty_glob_graceful(site_factory):
    """Hash handles non-matching globs gracefully."""
    site = site_factory(autodoc_python={"enabled": True, "source_dirs": ["../nonexistent"]})
    result = runner.invoke(cache_cli, ["hash"], obj=site)
    assert result.exit_code == 0  # Succeeds, just no files matched


# Phase 4: Self-validating cache tests

def test_autodoc_source_metadata_stored(cache_factory, tmp_path):
    """Autodoc extraction stores source file hash and mtime."""
    site_root = tmp_path / "site"
    site_root.mkdir()
    source_file = tmp_path / "src" / "module.py"
    source_file.parent.mkdir()
    source_file.write_text("def foo(): pass")

    cache = cache_factory()
    cache.add_autodoc_dependency(
        source_file,
        "api/module/index.md",
        site_root=site_root,
        source_hash=hash_file(source_file),
        source_mtime=source_file.stat().st_mtime,
    )

    # Path normalized relative to site parent
    normalized_key = str(source_file.relative_to(tmp_path))
    assert normalized_key in cache.autodoc_source_metadata


def test_stale_autodoc_detected(cache_factory, tmp_path):
    """Changed source files are detected as stale."""
    site_root = tmp_path / "site"
    site_root.mkdir()
    source_file = tmp_path / "src" / "module.py"
    source_file.parent.mkdir()
    source_file.write_text("def foo(): pass")

    cache = cache_factory()
    cache.add_autodoc_dependency(
        source_file,
        "api/module/index.md",
        site_root=site_root,
        source_hash=hash_file(source_file),
        source_mtime=source_file.stat().st_mtime,
    )

    # Modify source (changes both content and mtime)
    import time
    time.sleep(0.01)  # Ensure mtime changes
    source_file.write_text("def foo(): return 42")

    stale = cache.get_stale_autodoc_sources(site_root)
    normalized_key = str(source_file.relative_to(tmp_path))
    assert normalized_key in stale


def test_unchanged_autodoc_not_stale(cache_factory, tmp_path):
    """Unchanged source files are not marked stale."""
    site_root = tmp_path / "site"
    site_root.mkdir()
    source_file = tmp_path / "src" / "module.py"
    source_file.parent.mkdir()
    source_file.write_text("def foo(): pass")

    cache = cache_factory()
    cache.add_autodoc_dependency(
        source_file,
        "api/module/index.md",
        site_root=site_root,
        source_hash=hash_file(source_file),
        source_mtime=source_file.stat().st_mtime,
    )

    stale = cache.get_stale_autodoc_sources(site_root)
    normalized_key = str(source_file.relative_to(tmp_path))
    assert normalized_key not in stale


def test_deleted_autodoc_source_detected(cache_factory, tmp_path):
    """Deleted source files are detected as stale."""
    site_root = tmp_path / "site"
    site_root.mkdir()
    source_file = tmp_path / "src" / "module.py"
    source_file.parent.mkdir()
    source_file.write_text("def foo(): pass")

    cache = cache_factory()
    normalized_key = str(source_file.relative_to(tmp_path))
    cache.add_autodoc_dependency(
        source_file,
        "api/module/index.md",
        site_root=site_root,
        source_hash=hash_file(source_file),
        source_mtime=source_file.stat().st_mtime,
    )

    # Delete source
    source_file.unlink()

    stale = cache.get_stale_autodoc_sources(site_root)
    assert normalized_key in stale


def test_cache_migration_marks_all_stale(cache_factory, tmp_path):
    """Old cache without metadata triggers full autodoc rebuild."""
    site_root = tmp_path / "site"
    site_root.mkdir()
    source_file = tmp_path / "src" / "module.py"
    source_file.parent.mkdir()
    source_file.write_text("def foo(): pass")

    cache = cache_factory()
    normalized_key = str(source_file.relative_to(tmp_path))

    # Simulate old cache: has dependencies but no metadata (pre-v0.1.8)
    cache.autodoc_dependencies[normalized_key] = {"api/module/index.md"}
    # autodoc_source_metadata is empty

    stale = cache.get_stale_autodoc_sources(site_root)
    assert normalized_key in stale  # All marked stale for safety


def test_mtime_unchanged_skips_hash(cache_factory, tmp_path, mocker):
    """mtime-first optimization skips hash computation when mtime unchanged."""
    site_root = tmp_path / "site"
    site_root.mkdir()
    source_file = tmp_path / "src" / "module.py"
    source_file.parent.mkdir()
    source_file.write_text("def foo(): pass")

    cache = cache_factory()
    cache.add_autodoc_dependency(
        source_file,
        "api/module/index.md",
        site_root=site_root,
        source_hash=hash_file(source_file),
        source_mtime=source_file.stat().st_mtime,
    )

    # Mock hash_file to track if it's called
    mock_hash = mocker.patch("bengal.utils.hashing.hash_file")

    stale = cache.get_stale_autodoc_sources(site_root)

    # hash_file should NOT be called - mtime unchanged
    mock_hash.assert_not_called()
    assert len(stale) == 0
```

## Future Considerations

Deferred for now, may revisit based on user feedback:

| Feature | Rationale for Deferral |
|---------|----------------------|
| `.bengalcacheignore` | No demonstrated need yet |
| `--exclude` flag | Can add if users need one-off overrides |
| `cache clean` command | Separate concern, different RFC |
| Monorepo support (`--workspace`) | Wait for monorepo feature request |
| Hash algorithm choice | SHA-256 is sufficient; premature to add options |

---

**Status**: Proposed  
**Priority**: High (user-facing sharp edge)  
**Effort**: Medium (2-3 days)
  - Phase 1-2 (CLI commands): 1 day
  - Phase 4 (self-validating cache): 1 day
  - Tests + docs: 0.5-1 day
**Target**: v0.1.8
