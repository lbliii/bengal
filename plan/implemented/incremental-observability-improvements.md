# Incremental Build Observability Improvements

**Context:** After fixing the incremental non-determinism bug, identify improvements to prevent similar issues.

## Proposed Improvements

### 1. Enhanced Logging in Incremental Builds

**Current:** Basic "X pages cached" message  
**Proposed:** Add detailed logging phase showing Page vs PageProxy composition

```python
# In build.py after Phase 8 (rendering)
if incremental and logger.level <= DEBUG:
    page_types = {"Page": 0, "PageProxy": 0, "other": 0}
    for page in self.site.pages:
        page_type = type(page).__name__
        if page_type == "Page":
            page_types["Page"] += 1
        elif page_type == "PageProxy":
            page_types["PageProxy"] += 1
        else:
            page_types["other"] += 1
    
    logger.debug(
        "site_pages_composition_before_postprocess",
        total_pages=len(self.site.pages),
        fresh_pages=page_types["Page"],
        proxies=page_types["PageProxy"],
        other=page_types["other"]
    )
```

**Location:** `bengal/orchestration/build.py` after Phase 8.4 (after we update site.pages)

### 2. PageProxy Contract Validation

**Proposed:** Add a validator that checks PageProxy implements all critical Page properties

```python
# In bengal/core/page/proxy.py

def validate_proxy_contract(proxy: 'PageProxy', context: str = "") -> list[str]:
    """
    Validate that PageProxy implements all properties needed for transparency.
    
    This prevents bugs where templates or postprocessing access properties
    that don't exist on PageProxy but do on Page.
    
    Args:
        proxy: PageProxy instance to validate
        context: Context string for error messages
        
    Returns:
        List of missing/broken properties (empty if valid)
    """
    required_properties = [
        'title', 'date', 'tags', 'slug', 'url', 'permalink',
        'source_path', 'output_path', 'metadata',
        '_site', '_section'
    ]
    
    issues = []
    for prop in required_properties:
        if not hasattr(proxy, prop):
            issues.append(f"Missing property: {prop}")
        elif prop in ['url', 'permalink']:
            # Test that these can be called without crashing
            try:
                getattr(proxy, prop)
            except Exception as e:
                issues.append(f"Property {prop} raises: {e}")
    
    return issues
```

**Usage:** Call in content discovery after creating proxies:
```python
if logger.level <= DEBUG:
    issues = validate_proxy_contract(proxy, f"discovery:{page.source_path.name}")
    if issues:
        logger.warning("proxy_contract_violation", page=str(page.source_path), issues=issues)
```

### 3. Better Test Output for Hash Mismatches

**Current:** Just shows mismatched hashes  
**Proposed:** Show actual content differences

```python
# In tests/integration/stateful/helpers.py

def compare_outputs_detailed(site_dir: Path, full_hashes: dict, inc_hashes: dict) -> dict:
    """
    Compare build outputs and return detailed diff information.
    
    Returns:
        {
            'file_set_diff': {...},
            'content_diffs': {
                'file.html': {
                    'full_hash': '...',
                    'inc_hash': '...',
                    'diff_preview': '...first 500 chars of diff...',
                    'full_path': Path(...)
                }
            }
        }
    """
    output_dir = site_dir / "public"
    
    result = {
        'file_set_diff': {
            'full_only': set(full_hashes.keys()) - set(inc_hashes.keys()),
            'inc_only': set(inc_hashes.keys()) - set(full_hashes.keys())
        },
        'content_diffs': {}
    }
    
    for file_path in set(full_hashes.keys()) & set(inc_hashes.keys()):
        if full_hashes[file_path] != inc_hashes[file_path]:
            full_file = output_dir / file_path
            if full_file.exists() and full_file.stat().st_size < 100_000:  # Under 100KB
                try:
                    import difflib
                    full_content = full_file.read_text()
                    # Save inc version during incremental build for comparison
                    inc_file = site_dir / ".bengal" / "inc_snapshot" / file_path
                    if inc_file.exists():
                        inc_content = inc_file.read_text()
                        diff = list(difflib.unified_diff(
                            inc_content.splitlines()[:20],  # First 20 lines
                            full_content.splitlines()[:20],
                            lineterm=''
                        ))
                        result['content_diffs'][file_path] = {
                            'full_hash': full_hashes[file_path],
                            'inc_hash': inc_hashes[file_path],
                            'diff_preview': '\n'.join(diff)
                        }
                except Exception as e:
                    result['content_diffs'][file_path] = {
                        'error': str(e)
                    }
    
    return result
```

### 4. PageProxy Lifecycle Documentation

**Proposed:** Add comprehensive docstring to PageProxy explaining its lifecycle

```python
# In bengal/core/page/proxy.py class docstring

"""
Lazy-loaded page placeholder.

LIFECYCLE:
-----------
1. Discovery Phase (content_discovery.py):
   - Created from cached metadata for unchanged pages
   - Has: title, date, tags, slug, _section, _site, output_path
   - Does NOT have: content, rendered_html (lazy-loaded)

2. Filtering Phase (incremental.py):
   - PageProxy objects pass through find_work_early() unchanged
   - Only modified pages become full Page objects

3. Rendering Phase (render.py):
   - Modified pages rendered as full Page objects
   - PageProxy objects skipped (already cached)
   
4. Update Phase (build.py Phase 8.4):
   - Freshly rendered Page objects replace their PageProxy counterparts
   - site.pages now has mix of: fresh Page + old PageProxy

5. Postprocessing Phase (postprocess.py):
   - Iterates over site.pages (now has fresh Pages)
   - Uses Page.output_path, Page.title, etc.
   - ⚠️ CRITICAL: PageProxy must implement all properties used here

TRANSPARENCY CONTRACT:
----------------------
PageProxy must be transparent to:
- Templates (implements .url, .permalink, .title, etc.)
- Postprocessing (implements .output_path, metadata access)
- Navigation (implements .prev, .next via _ensure_loaded)

If adding new Page properties used by templates/postprocessing,
MUST also add to PageProxy or update _ensure_loaded().

VALIDATION:
-----------
Use validate_proxy_contract() to check compliance.
"""
```

### 5. Incremental Build State Assertions

**Proposed:** Add invariant checks in build pipeline

```python
# In bengal/orchestration/build.py

def _validate_incremental_state(self, phase: str) -> None:
    """Validate state during incremental builds for debugging."""
    if not self.incremental or logger.level > DEBUG:
        return
    
    if phase == "before_postprocess":
        # After Phase 8.4, site.pages should have NO PageProxy for rebuilt pages
        rebuilt_paths = {p.source_path for p in pages_to_build}
        stale_proxies = [
            p for p in self.site.pages 
            if type(p).__name__ == "PageProxy" and p.source_path in rebuilt_paths
        ]
        
        if stale_proxies:
            logger.warning(
                "stale_proxies_detected_before_postprocess",
                count=len(stale_proxies),
                files=[str(p.source_path.name) for p in stale_proxies[:5]]
            )
        
        # All pages should have output_path for postprocessing
        missing_output = [
            p for p in self.site.pages
            if not getattr(p, 'output_path', None) and not p.metadata.get('_generated')
        ]
        
        if missing_output:
            logger.warning(
                "pages_missing_output_path_before_postprocess",
                count=len(missing_output),
                files=[str(p.source_path.name) for p in missing_output[:5]]
            )
```

## Implementation Priority

**High Priority** (do now):
1. ✅ Enhanced logging (10 lines, huge debugging value)
2. ✅ PageProxy lifecycle docs (prevents future bugs)

**Medium Priority** (next sprint):
3. PageProxy contract validation (catches issues early)
4. Incremental state assertions (debugging aid)

**Low Priority** (nice to have):
5. Better test output (only needed when tests fail)

## Summary

The bug was found by existing tests ✓, but debugging was hard because:
- No visibility into Page/PageProxy mix
- No validation of PageProxy completeness
- No documentation of PageProxy lifecycle

These improvements make the next similar bug **much faster to debug**.

