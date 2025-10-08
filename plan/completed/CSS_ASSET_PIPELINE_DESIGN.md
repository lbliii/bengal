# CSS Asset Pipeline Design Analysis

**Date**: October 8, 2025  
**Status**: 🔴 Design Review  
**Context**: Current implementation causes 30+ HTTP requests for CSS

---

## Current State: Problems

### 1. Architectural Issues
```python
# AssetDiscovery now parses CSS to find imports
def _find_imported_css_files(self):
    # Scans ALL CSS files
    # Builds dependency graph
    # Decides what to skip
```

**Problems:**
- ❌ Discovery doing business logic (not just discovery)
- ❌ Tight coupling between discovery and CSS bundling
- ❌ Every CSS file is read twice (discovery + processing)
- ❌ Fragile: What if @import uses variables? URLs? Conditional imports?

### 2. User Experience Issues
```
public/assets/css/
  style.{hash}.css              ← Only this shows up
  # All other CSS files skipped
```

**Problems:**
- ❌ What if user WANTS separate CSS files? (e.g., print.css, critical.css)
- ❌ No way to opt-in/opt-out of bundling
- ❌ Breaks if someone creates a standalone component CSS

### 3. Dependency Issues
```python
# Without lightningcss: 30+ HTTP requests
# With lightningcss: Bundled
```

**Problems:**
- ❌ Catastrophic failure mode (30+ requests without optional dep)
- ❌ Python lightningcss doesn't have parity with Node version
- ❌ No fallback bundling strategy

---

## Core Needs (First Principles)

### What do users ACTUALLY need?

1. **Fast page loads** (1-3 CSS HTTP requests max)
2. **Easy authoring** (organize CSS into logical files)
3. **Production optimization** (minify, autoprefix, bundle)
4. **Flexibility** (separate critical.css, print.css if needed)
5. **Zero config** (works out of the box)

### What do SSG developers need?

1. **Clear architecture** (separation of concerns)
2. **Testability** (each piece does one thing)
3. **Extensibility** (easy to add new asset types)
4. **Performance** (parallel processing where possible)

---

## Design Options

### Option 1: Convention Over Configuration (Current + Fix)

**Concept**: Designate entry points by convention

```
assets/css/
  style.css          ← Entry point (in root)
  print.css          ← Entry point (in root)
  components/        ← Modules (not in root)
    buttons.css
    cards.css
  base/
    reset.css
```

**Rules:**
- CSS files in `assets/css/*.css` = entry points (copied & bundled)
- CSS files in subdirectories = modules (skipped, will be imported)

**Pros:**
- ✅ Simple to understand
- ✅ No configuration needed
- ✅ Supports multiple entry points (print.css, etc.)

**Cons:**
- ❌ Still requires parsing imports (but only for entry points)
- ❌ Convention might not be obvious to new users
- ❌ Can't have entry point in subdirectory

**Implementation:**
```python
def discover(self):
    css_root = self.assets_dir / 'css'
    
    for file_path in self.assets_dir.rglob('*'):
        rel_path = file_path.relative_to(self.assets_dir)
        
        # For CSS: Only include root-level files
        if file_path.suffix == '.css':
            if file_path.parent == css_root:
                # Entry point - will be bundled
                asset = Asset(source_path=file_path, is_css_entry=True)
            else:
                # Module - skip
                continue
        else:
            # Non-CSS assets: include everything
            asset = Asset(source_path=file_path)
        
        self.assets.append(asset)
```

---

### Option 2: Explicit Configuration

**Concept**: User declares entry points in config

```toml
# bengal.toml
[assets.css]
entry_points = ["css/style.css", "css/print.css"]
bundle = true
minify = true
```

**Pros:**
- ✅ Explicit intent
- ✅ Complete control
- ✅ Easy to test
- ✅ Clear documentation

**Cons:**
- ❌ More configuration (not "zero config")
- ❌ Easy to forget to update config when adding CSS

---

### Option 3: Single Entry Point (Simplest)

**Concept**: Only bundle `style.css`, everything else is standalone

```
assets/css/
  style.css          ← ONLY this is bundled
  critical.css       ← Standalone (NOT bundled)
  print.css          ← Standalone (NOT bundled)
```

**Rules:**
- `style.css` = Main entry point (bundled with all @imports)
- Any other CSS file = Standalone (copied as-is)

**Pros:**
- ✅ Dead simple to understand
- ✅ Minimal configuration
- ✅ Clear primary entry point
- ✅ Still allows standalone CSS for special cases

**Cons:**
- ❌ Less flexible (assumes style.css is main file)
- ❌ Standalone files still have @import issues

**Implementation:**
```python
def discover(self):
    for file_path in self.assets_dir.rglob('*'):
        if file_path.suffix == '.css':
            # Check if this file is imported by style.css
            if file_path.name == 'style.css':
                asset = Asset(source_path=file_path, should_bundle=True)
            elif self._is_imported_by_style_css(file_path):
                # Skip - will be bundled into style.css
                continue
            else:
                # Standalone CSS file
                asset = Asset(source_path=file_path, should_bundle=False)
        else:
            asset = Asset(source_path=file_path)
        
        self.assets.append(asset)
```

---

### Option 4: External Build Tool (Industry Standard)

**Concept**: Use dedicated CSS tooling (PostCSS, Lightning CSS CLI, Vite)

```toml
# bengal.toml
[assets]
build_command = "npm run build:css"
source_dir = "assets_src"
output_dir = "assets"
```

**Workflow:**
```bash
# User's package.json
{
  "scripts": {
    "build:css": "postcss assets_src/css/style.css -o assets/css/style.css"
  }
}

# Bengal runs this before asset discovery
$ npm run build:css
$ bengal build
```

**Pros:**
- ✅ Industry-standard tools
- ✅ Full feature set (PostCSS plugins, Sass, etc.)
- ✅ Battle-tested
- ✅ Separation of concerns (Bengal doesn't do CSS)

**Cons:**
- ❌ Requires Node.js
- ❌ More complex setup
- ❌ Not "just Python"

---

## Hybrid Approach: Built-in + Escape Hatch

**Concept**: Simple bundling built-in, support external tools for power users

### Phase 1: Built-in (Simple)
```python
# Convention: Only bundle style.css
# Everything else copied as-is
```

### Phase 2: External (Power Users)
```toml
[assets]
prebuild_command = "npm run build:css"  # Optional
```

**Pros:**
- ✅ Zero config for simple cases
- ✅ Escape hatch for complex cases
- ✅ Clear upgrade path

---

## Recommended Solution

### ⭐ Option 3: Single Entry Point + Fallback

**Why:**
1. **Simple mental model**: "style.css is your main CSS"
2. **Zero config**: Works out of the box
3. **Flexible**: Can still add print.css, critical.css as standalone
4. **Graceful degradation**: Without lightningcss, at least only style.css has @imports

**Implementation Strategy:**

1. **Asset Discovery** (simple, no CSS parsing):
   ```python
   def discover(self):
       # Just find all files, mark CSS appropriately
       for file in self.assets_dir.rglob('*'):
           if file.name == 'style.css':
               asset = Asset(file, is_main_css=True)
           else:
               asset = Asset(file)
           self.assets.append(asset)
   ```

2. **Asset Processing** (handles bundling):
   ```python
   def process_css(asset):
       if asset.is_main_css:
           # Bundle all @imports
           bundle_imports(asset)
       # Always minify
       minify(asset)
   ```

3. **Template Helper** (guides users):
   ```html
   <!-- Automatic -->
   {{ css('style.css') }}  <!-- Outputs bundled, minified, fingerprinted -->
   
   <!-- Explicit standalone -->
   {{ css('print.css', media='print') }}
   ```

4. **Documentation**:
   ```markdown
   ## CSS Organization
   
   - `assets/css/style.css` - Main stylesheet (automatically bundled)
   - `assets/css/print.css` - Print styles (standalone)
   - `assets/css/components/*.css` - Imported by style.css
   ```

---

## Migration Path

1. **Immediate** (today):
   - Revert AssetDiscovery changes (too complex)
   - Implement single entry point logic
   - Update warning message

2. **Short-term** (this week):
   - Better fallback for missing lightningcss
   - Documentation for CSS organization
   - Example project structure

3. **Long-term** (future):
   - Add `prebuild_command` for external tools
   - Consider PostCSS integration
   - Investigate Python-native bundler

---

## Decision Criteria

Which option should we choose? Consider:

1. **User skill level**: Beginners need simple, experts need powerful
2. **Project complexity**: Blog vs. documentation site vs. app
3. **Performance**: Must work well without optional deps
4. **Maintenance**: Can we maintain custom CSS bundler?

**My recommendation**: Option 3 (Single Entry Point) because:
- ✅ Matches 80% use case (one main stylesheet)
- ✅ Simple to explain and document
- ✅ Graceful degradation without lightningcss
- ✅ Easy to test and maintain
- ✅ Clear path to external tools if needed

