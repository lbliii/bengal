# CSS Bundling Strategy - The Right Way

**Date**: October 8, 2025  
**Status**: 🟢 Design Approved

---

## User's Vision (Correct!)

### Input
```
assets/css/
  style.css              ← Entry point (has @imports)
  components/
    buttons.css
    cards.css
    ...
  base/
    reset.css
    typography.css
```

### Output
```
public/assets/css/
  style.a1b2c3d4.css     ← Single bundled file (everything combined)
```

### Benefits
- ✅ 1 HTTP request instead of 30+
- ✅ Automatic dependency resolution
- ✅ Minified + Autoprefixed
- ✅ Clean output directory

---

## Architecture

### Phase 1: Discovery (Simple)
```python
class AssetDiscovery:
    def discover(self):
        # Just find ALL files, no CSS-specific logic
        for file in assets_dir.rglob('*'):
            assets.append(Asset(file))
```

**No special CSS handling!** Just find everything.

### Phase 2: Orchestration (Smart)
```python
class AssetOrchestrator:
    def process(self, assets):
        # Separate CSS entry points from regular assets
        css_entries = [a for a in assets if a.is_css_entry_point()]
        other_assets = [a for a in assets if not a.is_css_related()]
        
        # Bundle CSS entry points
        for entry in css_entries:
            bundled = self._bundle_css(entry)
            output_bundled(bundled)
        
        # Copy other assets normally
        for asset in other_assets:
            asset.copy_to_output()
```

### Phase 3: CSS Bundling (lightningcss)
```python
def _bundle_css(self, entry_asset):
    """
    Bundle CSS entry point using lightningcss.
    Resolves all @imports, minifies, autoprefixes.
    """
    try:
        import lightningcss
        
        # lightningcss.bundle() would be ideal, but Python doesn't have it
        # So we manually resolve @imports then process
        
        bundled_content = self._resolve_imports(entry_asset.source_path)
        
        result = lightningcss.process_stylesheet(
            bundled_content,
            minify=True,
            browsers_list=['last 2 versions'],
        )
        
        return result
        
    except ImportError:
        # Fallback: Just copy with warning
        warn_once("Install lightningcss for CSS bundling")
        return entry_asset.content
```

---

## Implementation Plan

### Step 1: Revert AssetDiscovery complexity
- Remove `_find_imported_css_files()` 
- Keep it simple: just find files

### Step 2: Add CSS entry point detection
```python
class Asset:
    def is_css_entry_point(self) -> bool:
        """Check if this is a CSS entry point (should be bundled)."""
        return (
            self.asset_type == 'css' and 
            self.source_path.name == 'style.css'
        )
    
    def is_css_module(self) -> bool:
        """Check if this is a CSS module (imported by entry point)."""
        return (
            self.asset_type == 'css' and 
            not self.is_css_entry_point()
        )
```

### Step 3: Update AssetOrchestrator
```python
def process(self, assets):
    # Find CSS entry points
    css_entries = [a for a in assets if a.is_css_entry_point()]
    
    # Find which CSS files are imported (should be skipped)
    imported_css = set()
    for entry in css_entries:
        imported_css.update(self._find_imports(entry))
    
    # Process assets
    for asset in assets:
        if asset.is_css_entry_point():
            # Bundle this entry point
            self._bundle_and_output(asset)
        elif asset.source_path in imported_css:
            # Skip - already bundled into entry point
            continue
        else:
            # Regular asset - copy normally
            asset.copy_to_output()
```

### Step 4: Implement bundling in Asset class
```python
def bundle_css(self) -> str:
    """Bundle CSS by resolving all @imports recursively."""
    # Already have this logic in _minify_css!
    # Just need to separate bundling from minification
    
    bundled = self._resolve_imports(self.source_path)
    return bundled

def _resolve_imports(self, css_file: Path) -> str:
    """Recursively resolve @import statements."""
    content = css_file.read_text()
    
    def replace_import(match):
        import_path = match.group(1)
        imported_file = css_file.parent / import_path
        
        if imported_file.exists():
            # Recursively resolve
            return self._resolve_imports(imported_file)
        return match.group(0)
    
    return re.sub(r'@import\s+url\([\'"]([^\'"]+)[\'"]\)', replace_import, content)
```

---

## Fallback Strategy (Without lightningcss)

If lightningcss not installed:

### Option A: Manual bundling only (no minification)
```python
# Bundle @imports manually
bundled = resolve_imports(style.css)

# Write as-is (not minified, but at least bundled)
output.write(bundled)

# Warning shown once
print("⚠️  Install lightningcss for minification and autoprefixing")
```

### Option B: Use csscompressor (minify but no bundle)
```python
# Copy style.css with @imports intact
# User gets 30+ requests but at least it works

print("⚠️  Install lightningcss for CSS bundling")
```

**Recommendation**: Option A (manual bundling)
- Still get 1 file output (good)
- Just not minified (acceptable fallback)

---

## File Structure Guidance

Document for users:

```markdown
## CSS Organization

Bengal uses `style.css` as your CSS entry point.

### Structure
```
assets/css/
  style.css              ← Your entry point (edit this)
  components/            ← Component styles (imported)
  base/                  ← Base styles (imported)
  utilities/             ← Utility classes (imported)
```

### style.css
```css
/* Import order matters! */
@import url('base/reset.css');
@import url('base/typography.css');
@import url('components/buttons.css');
@import url('components/cards.css');
```

### Build Output
```
public/assets/css/
  style.a1b2c3d4.css     ← Single bundled file
```

### Advanced: Multiple Entry Points

If you need separate CSS files (e.g., print styles):

```
assets/css/
  style.css              ← Main styles (bundled)
  print.css              ← Print styles (separate)
```

Both will be processed independently and output as separate files.
```

---

## Testing Plan

1. **Test bundling**: Verify @imports are resolved
2. **Test order**: CSS cascade order preserved
3. **Test minification**: Output is minified
4. **Test fingerprinting**: Hash-based cache busting works
5. **Test fallback**: Works without lightningcss (degraded)
6. **Test multiple entries**: Both style.css and print.css work

---

## Summary

✅ Simple discovery (no CSS logic)  
✅ Smart orchestration (detect entry points)  
✅ Proper bundling (resolve @imports)  
✅ Single output file (style.{hash}.css)  
✅ Graceful fallback (works without lightningcss)  
✅ Clear documentation (users know what to expect)  

This is the right architecture! ⭐

