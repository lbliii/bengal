# Versioned Documentation: Technical Implementation Plan

**Status**: Design Specification  
**Target**: v0.3.0 (alongside autodoc) or v0.4.0  
**Effort**: 1-2 weeks  
**Priority**: P1 - HIGH (Essential for library maintainers)

---

## Executive Summary

Multi-version documentation support with version selector UI, canonical URLs, search scoping, and "viewing old docs" warnings. Essential for library maintainers shipping breaking changes.

**Key Feature**: One command builds all versions with proper SEO and UX.

---

## Problem Statement

### Why This Matters

Library maintainers need to:
1. **Support multiple versions**: Users on v1.0 need v1.0 docs
2. **SEO-friendly**: Search engines index correct version
3. **User warnings**: "You're viewing old docs" banner
4. **Easy switching**: Version selector in navigation
5. **Maintenance**: Update all versions without manual work

### Current Pain (Sphinx/Others)

```bash
# Sphinx approach (manual, brittle)
$ git checkout v1.0
$ sphinx-build docs docs/_build/1.0
$ git checkout v2.0
$ sphinx-build docs docs/_build/2.0
# Manually setup nginx redirects
# Manually add version selector
# Manually set canonical URLs
```

**Bengal Approach**: One config, one command, automatic everything.

---

## Architecture

### Directory Structure

```
public/
├── index.html              # Redirect to latest
├── versions.json           # Version metadata
├── latest/                 # Symlink to current version
│   └── ...
├── v2.0/                   # Version 2.0 docs
│   ├── index.html
│   ├── api/
│   └── ...
├── v1.5/                   # Version 1.5 docs
│   ├── index.html
│   ├── api/
│   └── ...
└── v1.0/                   # Version 1.0 docs (archived)
    ├── index.html
    ├── api/
    └── ...
```

### URL Structure

```
https://docs.example.com/                    → /latest/ (redirect)
https://docs.example.com/latest/             → v2.0 docs
https://docs.example.com/v2.0/               → v2.0 docs
https://docs.example.com/v1.5/               → v1.5 docs
https://docs.example.com/v1.0/               → v1.0 docs (with warning)
```

---

## Configuration

```toml
# bengal.toml

[versioning]
# Enable versioning
enabled = true

# Current version being built
current = "2.0"

# All versions to build/maintain
versions = ["2.0", "1.5", "1.0"]

# Default version (usually same as current)
default_version = "2.0"

# Version aliases
[versioning.aliases]
latest = "2.0"
stable = "2.0"
dev = "main"

# Warning banner for old versions
[versioning.banner]
enabled = true
message = "⚠️ You're viewing documentation for v{version}. The current version is v{current}."
show_on = ["1.5", "1.0"]  # Which versions show warning
style = "warning"  # "warning", "info", "danger"

# Source control integration
[versioning.git]
enabled = true
branch_pattern = "v{version}"  # Git branch naming
tag_pattern = "v{version}"     # Git tag naming

# SEO
[versioning.seo]
canonical_to_latest = true     # Canonicalize old versions to latest
sitemap_per_version = true     # Generate sitemap per version
robots_noindex_old = false     # Don't noindex old versions (users may need them)
```

---

## Core Implementation

### Version Manager

```python
# bengal/versioning/manager.py

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Any
import json
import shutil
import subprocess

@dataclass
class Version:
    """Represents a documentation version."""
    name: str              # "2.0", "1.5", etc.
    label: str             # "2.0 (Latest)", "1.5 (Stable)"
    url: str               # "/v2.0/"
    is_current: bool       # Is this the current version?
    git_ref: Optional[str] # Git branch/tag
    released: Optional[str] # Release date
    deprecated: bool       # Show deprecation warning?


class VersionManager:
    """
    Manage multi-version documentation builds.
    
    Responsibilities:
    - Build each version from git ref
    - Generate version selector data
    - Create version redirects
    - Set canonical URLs
    - Generate unified sitemap
    """
    
    def __init__(self, config: Dict[str, Any], site_root: Path):
        self.config = config.get('versioning', {})
        self.site_root = site_root
        self.output_dir = site_root / 'public'
        self.versions = self._load_versions()
    
    def _load_versions(self) -> List[Version]:
        """Load version configurations."""
        versions = []
        current = self.config['current']
        
        for version_name in self.config['versions']:
            is_current = version_name == current
            label = version_name
            if is_current:
                label += " (Latest)"
            
            version = Version(
                name=version_name,
                label=label,
                url=f"/v{version_name}/",
                is_current=is_current,
                git_ref=self._get_git_ref(version_name),
                released=None,  # Could extract from git tag date
                deprecated=version_name not in self.config.get('banner', {}).get('show_on', [])
            )
            versions.append(version)
        
        return versions
    
    def _get_git_ref(self, version: str) -> str:
        """Get git ref for version."""
        git_config = self.config.get('git', {})
        if not git_config.get('enabled'):
            return None
        
        # Try branch pattern first
        branch = git_config.get('branch_pattern', 'v{version}').format(version=version)
        if self._git_ref_exists(branch):
            return branch
        
        # Try tag pattern
        tag = git_config.get('tag_pattern', 'v{version}').format(version=version)
        if self._git_ref_exists(tag):
            return tag
        
        return None
    
    def _git_ref_exists(self, ref: str) -> bool:
        """Check if git ref exists."""
        try:
            subprocess.run(
                ['git', 'rev-parse', '--verify', ref],
                capture_output=True,
                check=True,
                cwd=self.site_root
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    def build_all_versions(self, force: bool = False) -> bool:
        """
        Build documentation for all versions.
        
        Args:
            force: Rebuild even if output exists
            
        Returns:
            True if all versions built successfully
        """
        print(f"\n📚 Building {len(self.versions)} documentation versions...")
        
        for version in self.versions:
            success = self.build_version(version, force=force)
            if not success:
                print(f"   ❌ Failed to build version {version.name}")
                return False
        
        # Generate version metadata
        self._generate_version_metadata()
        
        # Setup redirects
        self._setup_redirects()
        
        # Generate unified sitemap
        self._generate_unified_sitemap()
        
        print(f"\n✅ All versions built successfully")
        return True
    
    def build_version(self, version: Version, force: bool = False) -> bool:
        """
        Build documentation for a specific version.
        
        Strategy:
        1. Stash current changes (if git enabled)
        2. Checkout version's git ref
        3. Run bengal build with version context
        4. Output to public/v{version}/
        5. Return to original ref
        """
        output_path = self.output_dir / f"v{version.name}"
        
        # Skip if already built
        if output_path.exists() and not force:
            print(f"   ⏭️  v{version.name} (already built)")
            return True
        
        print(f"   🔨 Building v{version.name}...")
        
        if version.git_ref and self.config.get('git', {}).get('enabled'):
            # Build from git ref
            return self._build_from_git(version, output_path)
        else:
            # Build from current working directory
            return self._build_current(version, output_path)
    
    def _build_from_git(self, version: Version, output_path: Path) -> bool:
        """Build version from git ref."""
        # Save current ref
        current_ref = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            cwd=self.site_root
        ).stdout.strip()
        
        # Stash changes
        subprocess.run(['git', 'stash'], cwd=self.site_root, capture_output=True)
        
        try:
            # Checkout version
            subprocess.run(
                ['git', 'checkout', version.git_ref],
                capture_output=True,
                check=True,
                cwd=self.site_root
            )
            
            # Build site
            success = self._run_build(version, output_path)
            
        finally:
            # Return to original ref
            subprocess.run(['git', 'checkout', current_ref], cwd=self.site_root, capture_output=True)
            subprocess.run(['git', 'stash', 'pop'], cwd=self.site_root, capture_output=True)
        
        return success
    
    def _build_current(self, version: Version, output_path: Path) -> bool:
        """Build version from current working directory."""
        return self._run_build(version, output_path)
    
    def _run_build(self, version: Version, output_path: Path) -> bool:
        """Run Bengal build with version context."""
        from bengal.core.site import Site
        
        # Create site with version context
        site = Site.from_config(self.site_root)
        
        # Inject version context
        site.config['version'] = {
            'current': version.name,
            'is_latest': version.is_current,
            'all_versions': [v.name for v in self.versions],
            'url_prefix': f"/v{version.name}"
        }
        
        # Override output directory
        site.output_dir = output_path
        
        # Build
        try:
            site.build()
            return True
        except Exception as e:
            print(f"   Error building v{version.name}: {e}")
            return False
    
    def _generate_version_metadata(self):
        """Generate versions.json for version selector."""
        metadata = {
            'versions': [
                {
                    'name': v.name,
                    'label': v.label,
                    'url': v.url,
                    'is_current': v.is_current,
                    'released': v.released
                }
                for v in self.versions
            ],
            'aliases': self.config.get('aliases', {}),
            'default': self.config['default_version']
        }
        
        versions_file = self.output_dir / 'versions.json'
        versions_file.write_text(json.dumps(metadata, indent=2))
        print(f"   ✓ Generated versions.json")
    
    def _setup_redirects(self):
        """Setup version redirects."""
        # Create root index.html that redirects to latest
        default_version = self.config['default_version']
        index_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="0; url=/v{default_version}/">
    <link rel="canonical" href="/v{default_version}/" />
</head>
<body>
    <p>Redirecting to <a href="/v{default_version}/">v{default_version} documentation</a>...</p>
</body>
</html>"""
        
        (self.output_dir / 'index.html').write_text(index_html)
        
        # Create 'latest' symlink
        latest_link = self.output_dir / 'latest'
        latest_target = f"v{default_version}"
        
        if latest_link.exists():
            latest_link.unlink()
        
        latest_link.symlink_to(latest_target, target_is_directory=True)
        print(f"   ✓ Created /latest/ → /v{default_version}/")
    
    def _generate_unified_sitemap(self):
        """Generate sitemap index covering all versions."""
        sitemaps = []
        
        for version in self.versions:
            version_sitemap = f"/v{version.name}/sitemap.xml"
            sitemaps.append(version_sitemap)
        
        # Generate sitemap index
        sitemap_index = '<?xml version="1.0" encoding="UTF-8"?>\n'
        sitemap_index += '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        for sitemap_url in sitemaps:
            sitemap_index += f'  <sitemap>\n'
            sitemap_index += f'    <loc>https://docs.example.com{sitemap_url}</loc>\n'
            sitemap_index += f'  </sitemap>\n'
        
        sitemap_index += '</sitemapindex>'
        
        (self.output_dir / 'sitemap.xml').write_text(sitemap_index)
        print(f"   ✓ Generated unified sitemap")
```

---

## Version Selector UI

### Template Integration

```html
<!-- themes/default/templates/partials/version-selector.html -->

<div class="version-selector">
    <button class="version-current" onclick="toggleVersionDropdown()">
        <span class="version-label">{{ site.config.version.current }}</span>
        {% if site.config.version.is_latest %}
        <span class="badge-latest">Latest</span>
        {% endif %}
        <span class="dropdown-arrow">▼</span>
    </button>
    
    <div class="version-dropdown" id="version-dropdown" style="display: none;">
        <div class="version-dropdown-header">Select Version</div>
        {% for version in site.config.version.all_versions %}
        <a href="/v{{ version }}{{ page.url }}" class="version-option {% if version == site.config.version.current %}active{% endif %}">
            <span class="version-name">{{ version }}</span>
            {% if version == site.config.version.all_versions[0] %}
            <span class="badge">Latest</span>
            {% endif %}
        </a>
        {% endfor %}
    </div>
</div>

<script>
function toggleVersionDropdown() {
    const dropdown = document.getElementById('version-dropdown');
    dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
}

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    const selector = document.querySelector('.version-selector');
    if (!selector.contains(event.target)) {
        document.getElementById('version-dropdown').style.display = 'none';
    }
});

// Preserve current page path when switching versions
document.querySelectorAll('.version-option').forEach(link => {
    link.addEventListener('click', function(e) {
        // Current path: /v2.0/api/core/site/
        // Switch to v1.5: /v1.5/api/core/site/
        // Already handled in href generation
    });
});
</script>

<style>
.version-selector {
    position: relative;
    display: inline-block;
}

.version-current {
    padding: 8px 16px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 4px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
}

.badge-latest {
    background: var(--color-success);
    color: white;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 11px;
}

.version-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    margin-top: 4px;
    background: white;
    border: 1px solid var(--border);
    border-radius: 4px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    min-width: 200px;
    z-index: 1000;
}

.version-option {
    display: flex;
    justify-content: space-between;
    padding: 10px 16px;
    border-bottom: 1px solid var(--border);
    text-decoration: none;
    color: var(--text);
}

.version-option:hover {
    background: var(--bg-hover);
}

.version-option.active {
    background: var(--bg-active);
    font-weight: 600;
}
</style>
```

### Warning Banner

```html
<!-- themes/default/templates/partials/version-warning.html -->

{% if not site.config.version.is_latest %}
<div class="version-warning-banner">
    <div class="container">
        <span class="warning-icon">⚠️</span>
        <span class="warning-message">
            You're viewing documentation for <strong>v{{ site.config.version.current }}</strong>. 
            The current version is <strong>v{{ site.config.version.all_versions[0] }}</strong>.
        </span>
        <a href="/v{{ site.config.version.all_versions[0] }}{{ page.url }}" class="btn-upgrade">
            View Latest Docs →
        </a>
    </div>
</div>

<style>
.version-warning-banner {
    background: #fff3cd;
    border-bottom: 2px solid #ffc107;
    padding: 12px 0;
}

.version-warning-banner .container {
    display: flex;
    align-items: center;
    gap: 16px;
}

.warning-icon {
    font-size: 20px;
}

.warning-message {
    flex: 1;
    font-size: 14px;
}

.btn-upgrade {
    background: #ffc107;
    color: #000;
    padding: 8px 16px;
    border-radius: 4px;
    text-decoration: none;
    font-weight: 600;
}

.btn-upgrade:hover {
    background: #ffb300;
}
</style>
{% endif %}
```

---

## SEO & Canonical URLs

```python
# bengal/versioning/seo.py

class VersionSEOManager:
    """Manage SEO for versioned documentation."""
    
    def __init__(self, config: Dict[str, Any], base_url: str):
        self.config = config.get('versioning', {}).get('seo', {})
        self.base_url = base_url
        self.current_version = config.get('versioning', {}).get('current')
    
    def get_canonical_url(self, page_url: str, page_version: str) -> str:
        """
        Get canonical URL for page.
        
        Strategy:
        - Latest version: canonical to self
        - Old versions: canonical to latest (if configured)
        """
        if page_version == self.current_version:
            # Latest version - canonical to self
            return f"{self.base_url}/v{page_version}{page_url}"
        
        if self.config.get('canonical_to_latest', True):
            # Old version - canonical to latest
            return f"{self.base_url}/v{self.current_version}{page_url}"
        else:
            # Old version - canonical to self
            return f"{self.base_url}/v{page_version}{page_url}"
    
    def should_noindex(self, version: str) -> bool:
        """Check if version should be noindexed."""
        return self.config.get('robots_noindex_old', False) and version != self.current_version
    
    def inject_meta_tags(self, page_html: str, page_url: str, page_version: str) -> str:
        """Inject SEO meta tags into page HTML."""
        canonical_url = self.get_canonical_url(page_url, page_version)
        noindex = self.should_noindex(page_version)
        
        meta_tags = f'<link rel="canonical" href="{canonical_url}" />\n'
        
        if noindex:
            meta_tags += '<meta name="robots" content="noindex, follow" />\n'
        
        # Inject before </head>
        return page_html.replace('</head>', f'{meta_tags}</head>')
```

---

## CLI Integration

```bash
# Build all versions
$ bengal build --versioned

📚 Building 3 documentation versions...
   🔨 Building v2.0...
      ✓ 127 pages rendered
   🔨 Building v1.5...
      ✓ 124 pages rendered
   🔨 Building v1.0...
      ✓ 98 pages rendered
   ✓ Generated versions.json
   ✓ Created /latest/ → /v2.0/
   ✓ Generated unified sitemap

✅ All versions built successfully


# Build specific version
$ bengal build --version 1.5

# Force rebuild all
$ bengal build --versioned --force

# List available versions
$ bengal versions list

Available versions:
  v2.0 (Latest) - current
  v1.5          - from git tag v1.5
  v1.0          - from git tag v1.0
```

---

## Testing Strategy

```python
# tests/unit/versioning/test_version_manager.py

def test_build_all_versions(tmp_site):
    """Test building multiple versions."""
    config = {
        'versioning': {
            'enabled': True,
            'current': '2.0',
            'versions': ['2.0', '1.5', '1.0'],
            'git': {'enabled': False}  # Test without git
        }
    }
    
    manager = VersionManager(config, tmp_site)
    success = manager.build_all_versions()
    
    assert success
    assert (tmp_site / 'public' / 'v2.0' / 'index.html').exists()
    assert (tmp_site / 'public' / 'v1.5' / 'index.html').exists()
    assert (tmp_site / 'public' / 'v1.0' / 'index.html').exists()
    assert (tmp_site / 'public' / 'latest').is_symlink()
    assert (tmp_site / 'public' / 'versions.json').exists()


def test_version_selector_data(tmp_site):
    """Test version selector metadata generation."""
    manager = VersionManager(config, tmp_site)
    manager._generate_version_metadata()
    
    versions_file = tmp_site / 'public' / 'versions.json'
    data = json.loads(versions_file.read_text())
    
    assert len(data['versions']) == 3
    assert data['default'] == '2.0'
    assert data['versions'][0]['is_current'] == True


def test_canonical_urls():
    """Test canonical URL generation."""
    seo = VersionSEOManager(config, 'https://docs.example.com')
    
    # Latest version - canonical to self
    assert seo.get_canonical_url('/api/core/', '2.0') == 'https://docs.example.com/v2.0/api/core/'
    
    # Old version - canonical to latest
    assert seo.get_canonical_url('/api/core/', '1.5') == 'https://docs.example.com/v2.0/api/core/'
```

---

## Migration from Sphinx

Sphinx uses awkward manual versioning. Migrating is simple:

```python
# bengal/versioning/sphinx_migration.py

def migrate_sphinx_versions(sphinx_dir: Path, bengal_dir: Path):
    """
    Migrate Sphinx multi-version setup to Bengal.
    
    Sphinx typically uses:
    - Multiple git branches (v1.0, v2.0)
    - Manual nginx configs
    - Custom version switcher JS
    
    Bengal replaces all of this with config.
    """
    # Detect versions from git branches/tags
    versions = detect_versions_from_git()
    
    # Generate bengal.toml config
    config = {
        'versioning': {
            'enabled': True,
            'current': versions[0],
            'versions': versions,
            'git': {
                'enabled': True,
                'tag_pattern': 'v{version}'
            }
        }
    }
    
    # Write config
    write_bengal_config(bengal_dir / 'bengal.toml', config)
    
    print(f"✅ Migrated {len(versions)} versions to Bengal")
    print("Run: bengal build --versioned")
```

---

## Future Enhancements

### Version Diffs
Show what changed between versions:

```bash
$ bengal versions diff 1.5 2.0

Changes from v1.5 to v2.0:
  + Added: 12 new API methods
  ~ Modified: 8 existing methods
  - Removed: 3 deprecated methods
  ! Breaking: Site.build() signature changed
```

### Version-Specific Search
Scope search to specific version:

```html
<search-box version="2.0" />
```

### Changelog Integration
Link version to changelog:

```toml
[versioning.changelog]
enabled = true
file = "CHANGELOG.md"
link_sections = true  # Link v2.0 to ## [2.0] section
```

---

## Timeline

### Week 1: Core System (5 days)
- Day 1-2: VersionManager implementation
- Day 3: Git integration (checkout, build, restore)
- Day 4: Version metadata generation
- Day 5: Testing

### Week 2: UI & SEO (3 days)
- Day 1: Version selector UI
- Day 2: Warning banner + SEO meta tags
- Day 3: Testing + documentation

**Total**: 8 days (1-2 weeks)

---

## Success Metrics

- ✅ Build 3+ versions in < 30 seconds
- ✅ Beautiful version selector UI
- ✅ Proper canonical URLs (SEO-friendly)
- ✅ Warning banners on old versions
- ✅ Unified sitemap covering all versions
- ✅ One-command builds (`bengal build --versioned`)

---

## Conclusion

Versioned documentation is **table stakes** for library maintainers. Sphinx makes it painful and manual. Bengal makes it automatic and beautiful.

**Ship this with autodoc in v0.3.0** and Bengal becomes the obvious choice for Python library documentation.

---

*Next: Ship v0.3.0 with autodoc + versioning + migration tools*

