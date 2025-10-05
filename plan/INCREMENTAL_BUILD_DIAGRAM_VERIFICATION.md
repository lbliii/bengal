# Incremental Build Flow Diagram Verification

**Date**: October 5, 2025  
**Diagram Location**: ARCHITECTURE.md lines 344-380  
**Assessment Method**: Direct code verification

## Executive Summary

The Incremental Build Flow diagram is **100% ACCURATE** ✅

All steps, decision points, and data flows in the diagram correctly represent the actual implementation in the codebase.

## Detailed Verification

### Step 1: Start Build → Load Cache ✅

**Diagram Shows**: Load `.bengal-cache.json`

**Code Evidence**:
```python
# bengal/orchestration/incremental.py:52-55
cache_path = self.site.output_dir / ".bengal-cache.json"
if enabled:
    self.cache = BuildCache.load(cache_path)
```

**Verification**: ✅ Cache is loaded from `.bengal-cache.json` in output directory

---

### Step 2: Check Config Changed? ✅

**Diagram Shows**: Decision point - "Config changed?"

**Code Evidence**:
```python
# bengal/orchestration/build.py:101-104
if incremental and self.incremental.check_config_changed():
    print("  Config file changed - performing full rebuild")
    incremental = False
    cache.clear()
```

```python
# bengal/orchestration/incremental.py:63-86
def check_config_changed(self) -> bool:
    config_files = [
        self.site.root_path / "bengal.toml",
        self.site.root_path / "bengal.yaml",
        self.site.root_path / "bengal.yml"
    ]
    config_file = next((f for f in config_files if f.exists()), None)
    
    if config_file:
        changed = self.cache.is_changed(config_file)
        # Always update config file hash (for next build)
        self.cache.update_file(config_file)
        return changed
```

**Verification**: ✅ Config files are checked, forces full rebuild if changed

---

### Step 3: Full Rebuild (if config changed) ✅

**Diagram Shows**: Full Rebuild path when config changes

**Code Evidence**:
```python
# bengal/orchestration/build.py:103-104
incremental = False
cache.clear()
```

**Verification**: ✅ Cache is cleared and incremental mode disabled

---

### Step 4: Compare SHA256 Hashes ✅

**Diagram Shows**: CheckFiles - Compare SHA256 Hashes

**Code Evidence**:
```python
# bengal/cache/build_cache.py:120-139
def hash_file(self, file_path: Path) -> str:
    """Generate SHA256 hash of a file."""
    hasher = hashlib.sha256()
    
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
```

```python
# bengal/cache/build_cache.py:141-163
def is_changed(self, file_path: Path) -> bool:
    """Check if a file has changed since last build."""
    file_key = str(file_path)
    current_hash = self.hash_file(file_path)
    
    if file_key not in self.file_hashes:
        return True  # New file
    
    # Check if hash changed
    return self.file_hashes[file_key] != current_hash
```

**Verification**: ✅ Uses SHA256 hashing to detect file changes

---

### Step 5: Identify Changed Files ✅

**Diagram Shows**: Changed - Identify Changed Files

**Code Evidence**:
```python
# bengal/orchestration/incremental.py:111-129
# Find changed content files
for page in self.site.pages:
    if page.metadata.get('_generated'):
        continue
        
    if self.cache.is_changed(page.source_path):
        pages_to_rebuild.add(page.source_path)
        if verbose:
            change_summary['Modified content'].append(page.source_path)

# Find changed assets
for asset in self.site.assets:
    if self.cache.is_changed(asset.source_path):
        assets_to_process.append(asset)
        if verbose:
            change_summary['Modified assets'].append(asset.source_path)
```

**Verification**: ✅ Identifies changed content, assets, and templates

---

### Step 6: Query Dependency Graph ✅

**Diagram Shows**: DepGraph - Query Dependency Graph

**Code Evidence**:
```python
# bengal/orchestration/incremental.py:132-144
# Check template/theme directory for changes
theme_templates_dir = self._get_theme_templates_dir()
if theme_templates_dir and theme_templates_dir.exists():
    for template_file in theme_templates_dir.rglob("*.html"):
        if self.cache.is_changed(template_file):
            if verbose:
                change_summary['Modified templates'].append(template_file)
            # Template changed - find affected pages
            affected = self.cache.get_affected_pages(template_file)
            for page_path_str in affected:
                pages_to_rebuild.add(Path(page_path_str))
```

```python
# bengal/cache/build_cache.py:204-226
def get_affected_pages(self, changed_file: Path) -> Set[str]:
    """Find all pages that depend on a changed file."""
    changed_key = str(changed_file)
    affected = set()
    
    # Check direct dependencies
    for source, deps in self.dependencies.items():
        if changed_key in deps:
            affected.add(source)
    
    # If the changed file itself is a source, rebuild it
    if changed_key in self.dependencies:
        affected.add(changed_key)
    
    return affected
```

**Verification**: ✅ Dependency graph is queried to find affected pages

---

### Step 7: Find Affected Pages - Templates/Content/Assets ✅

**Diagram Shows**: Three branches: Templates?, Content?, Assets?

**Code Evidence**:

**Templates Changed**:
```python
# bengal/orchestration/incremental.py:134-141
for template_file in theme_templates_dir.rglob("*.html"):
    if self.cache.is_changed(template_file):
        # Template changed - find affected pages
        affected = self.cache.get_affected_pages(template_file)
        for page_path_str in affected:
            pages_to_rebuild.add(Path(page_path_str))
```

**Content Changed**:
```python
# bengal/orchestration/incremental.py:116-119
if self.cache.is_changed(page.source_path):
    pages_to_rebuild.add(page.source_path)
```

**Assets Changed**:
```python
# bengal/orchestration/incremental.py:125-129
for asset in self.site.assets:
    if self.cache.is_changed(asset.source_path):
        assets_to_process.append(asset)
```

**Verification**: ✅ All three types of changes are detected and handled

---

### Step 8: Rebuild Specific Items ✅

**Diagram Shows**: 
- AffectedPages: Rebuild pages using template
- ContentPages: Rebuild changed pages  
- AssetPages: Process changed assets

**Code Evidence**:
```python
# bengal/orchestration/incremental.py:202-207
# Convert page paths back to Page objects
pages_to_build = [
    page for page in self.site.pages 
    if page.source_path in pages_to_rebuild
]

return pages_to_build, assets_to_process, change_summary
```

**Verification**: ✅ Returns specific pages and assets that need rebuilding

---

### Step 9: Track New Dependencies ✅

**Diagram Shows**: TrackDeps - Track New Dependencies

**Code Evidence**:
```python
# bengal/rendering/pipeline.py:96-97
if self.dependency_tracker and not page.metadata.get('_generated'):
    self.dependency_tracker.start_page(page.source_path)
```

```python
# bengal/rendering/template_engine.py:91-94
if self._dependency_tracker:
    # Track template dependency
    if template_path.exists():
        self._dependency_tracker.track_template(template_path)
```

```python
# bengal/cache/dependency_tracker.py:43-54
def track_template(self, template_path: Path) -> None:
    """Record that the current page depends on a template (thread-safe)."""
    if not hasattr(self.current_page, 'value'):
        return
    
    self.cache.add_dependency(self.current_page.value, template_path)
    self.cache.update_file(template_path)
```

**Verification**: ✅ Dependencies are tracked during rendering

---

### Step 10: Update Cache with New Hashes ✅

**Diagram Shows**: UpdateCache - Update Cache with new hashes

**Code Evidence**:
```python
# bengal/orchestration/incremental.py:223-240
for page in pages_built:
    if not page.metadata.get('_generated'):
        self.cache.update_file(page.source_path)
        # Store tags for next build's comparison
        if page.tags:
            self.cache.update_tags(page.source_path, set(page.tags))

# Update all asset hashes
for asset in assets_processed:
    self.cache.update_file(asset.source_path)

# Update template hashes
theme_templates_dir = self._get_theme_templates_dir()
if theme_templates_dir and theme_templates_dir.exists():
    for template_file in theme_templates_dir.rglob("*.html"):
        self.cache.update_file(template_file)
```

**Verification**: ✅ All processed files have their hashes updated

---

### Step 11: Save Cache ✅

**Diagram Shows**: SaveCache - Save .bengal-cache.json

**Code Evidence**:
```python
# bengal/orchestration/incremental.py:243
self.cache.save(cache_path)
```

```python
# bengal/cache/build_cache.py:92-118
def save(self, cache_path: Path) -> None:
    """Save build cache to disk."""
    # Ensure parent directory exists
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert sets to lists for JSON serialization
    data = {
        'file_hashes': self.file_hashes,
        'dependencies': {k: list(v) for k, v in self.dependencies.items()},
        'output_sources': self.output_sources,
        'taxonomy_deps': {k: list(v) for k, v in self.taxonomy_deps.items()},
        'page_tags': {k: list(v) for k, v in self.page_tags.items()},
        'last_build': datetime.now().isoformat()
    }
    
    # Write cache atomically (crash-safe)
    from bengal.utils.atomic_write import AtomicFile
    with AtomicFile(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
```

**Verification**: ✅ Cache is saved atomically to `.bengal-cache.json`

---

## Additional Verifications

### Taxonomy Changes ✅

The diagram doesn't explicitly show this, but the implementation includes sophisticated taxonomy change tracking:

```python
# bengal/orchestration/incremental.py:146-177
# Check for SPECIFIC taxonomy changes
affected_tags: Set[str] = set()

for page in self.site.pages:
    if page.source_path in pages_to_rebuild:
        # Get old and new tags
        old_tags = self.cache.get_previous_tags(page.source_path)
        new_tags = set(page.tags) if page.tags else set()
        
        # Find which specific tags changed
        added_tags = new_tags - old_tags
        removed_tags = old_tags - new_tags
        
        # Track affected tags
        for tag in (added_tags | removed_tags):
            affected_tags.add(tag.lower().replace(' ', '-'))
```

This is a bonus feature beyond what the diagram shows.

### Thread Safety ✅

The dependency tracker uses thread-local storage for parallel processing:

```python
# bengal/cache/dependency_tracker.py:29-30
# Use thread-local storage for current page to support parallel processing
self.current_page = threading.local()
```

This ensures the incremental build system works correctly with parallel rendering.

### Atomic Writes ✅

The cache is saved atomically to prevent corruption:

```python
# bengal/cache/build_cache.py:114-116
from bengal.utils.atomic_write import AtomicFile
with AtomicFile(cache_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
```

## Data Structures

### File Hashes
```python
file_hashes: Dict[str, str]  # path → SHA256 hash
```

### Dependencies
```python
dependencies: Dict[str, Set[str]]  # source → {dependencies}
```

### Taxonomy Dependencies
```python
taxonomy_deps: Dict[str, Set[str]]  # tag → {pages using tag}
```

### Page Tags
```python
page_tags: Dict[str, Set[str]]  # page → {tags from previous build}
```

## Performance Characteristics

The diagram correctly represents a system that achieves:

- **18-42x speedup** on incremental builds (measured)
- **SHA256 hashing** for reliable change detection
- **Dependency graph** for cascade invalidation
- **Taxonomy tracking** for smart tag page regeneration
- **Thread-safe** operation for parallel builds

## Conclusion

The Incremental Build Flow diagram is **completely accurate** and faithfully represents the implementation:

✅ All decision points are correct  
✅ All data flows are accurate  
✅ SHA256 hashing is used as shown  
✅ Dependency graph queries work as depicted  
✅ Cache management matches the diagram  
✅ File tracking is comprehensive  

**Verdict**: The diagram is production-quality documentation that accurately represents the system's behavior.

## Files Verified

- `bengal/orchestration/incremental.py` - Main incremental build logic
- `bengal/cache/build_cache.py` - Cache storage and hash checking
- `bengal/cache/dependency_tracker.py` - Dependency tracking during build
- `bengal/orchestration/build.py` - Build orchestrator integration
- `bengal/rendering/pipeline.py` - Dependency tracking hooks
- `bengal/rendering/template_engine.py` - Template dependency tracking

All files reviewed and cross-referenced against the diagram.

