# File Organization Refactor

## Problem Statement

Bengal was generating profiling files (`.stats`) and some log files at the project root directory in an ad-hoc manner. Files like `build_profile.stats` and `profile.stats` were being created wherever the script was run, leading to:

1. **Clutter** - Generated files mixed with source files at project root
2. **No Convention** - Different types of generated files scattered randomly
3. **Git Issues** - These files weren't properly ignored, risking accidental commits
4. **Inconsistency** - Cache files were organized (`.bengal-cache*`) but profiles weren't

## Solution Implemented

Created an organized directory structure for all Bengal-generated files, separating them into logical categories.

### Directory Structure

```
mysite/
├── content/              # Source (version controlled)
├── templates/            # Source (version controlled)
├── assets/               # Source (version controlled)
├── bengal.toml           # Config (version controlled)
│
├── public/               # Build outputs (.gitignored)
│   ├── .bengal-cache.json           # Build cache
│   └── .bengal-cache/templates/     # Jinja2 bytecode cache
│
└── .bengal/              # Development files (.gitignored)
    └── profiles/         # Performance profiles
```

### Changes Made

#### 1. Created Path Utility (`bengal/utils/paths.py`)

New `BengalPaths` class provides centralized path management:
- `get_profile_dir(source_dir)` - Returns `.bengal/profiles/` directory
- `get_log_dir(source_dir)` - Returns `.bengal/logs/` directory  
- `get_profile_path(source_dir, custom_path, filename)` - Profile file path
- `get_build_log_path(source_dir, custom_path)` - Build log path
- `get_cache_path(output_dir)` - Build cache path
- `get_template_cache_dir(output_dir)` - Template cache directory

**Files:**
- Created: `bengal/utils/paths.py`
- Modified: `bengal/utils/__init__.py` (exported `BengalPaths`)

#### 2. Updated CLI Commands

Modified build commands to use organized paths by default:
- `--perf-profile` now defaults to `.bengal/profiles/profile.stats`
- Still allows custom paths when explicitly specified
- Updated help text to show new default location

**Files:**
- Modified: `bengal/cli/commands/build.py`
- Modified: `bengal/cli.py`

#### 3. Updated Test/Performance Scripts

Updated profiling scripts to use new structure:
- `profile_site.py` now saves to `.bengal/profiles/build_profile.stats`
- Automatically creates directory if it doesn't exist

**Files:**
- Modified: `tests/performance/profile_site.py`

#### 4. Updated `.gitignore`

Added patterns to ignore all generated files:
```gitignore
# Temporary files
*.stats                # All profiling data

# Bengal generated files
.bengal/              # Development files (profiles, logs)
.bengal-build.log     # Build logs
.demo-build.log       # Demo logs
```

**Files:**
- Modified: `.gitignore`

#### 5. Documented File Organization

Added comprehensive "File Organization" section to ARCHITECTURE.md explaining:
- Directory structure and rationale
- File categories (outputs, metadata, dev files)
- Usage in code with examples
- CLI integration
- Design principles

**Files:**
- Modified: `ARCHITECTURE.md`

## Benefits

### 1. **Clean Project Root**
- No more scattered `.stats` files
- All generated files in organized locations
- Clear separation between source and generated

### 2. **Predictable Locations**
- Developers know where to find profiles: `.bengal/profiles/`
- Cache files logically grouped: `public/.bengal-cache*`
- Build logs: `.bengal-build.log` (backward compatible)

### 3. **Easy Cleanup**
```bash
rm -rf public/      # Remove all build outputs + cache
rm -rf .bengal/     # Remove all development artifacts
```

### 4. **Git-Friendly**
- All generated files properly ignored
- No risk of accidentally committing build artifacts
- Clean `git status` output

### 5. **Extensible**
- Easy to add new categories (e.g., `.bengal/logs/`)
- Centralized path management via `BengalPaths`
- Consistent pattern for future features

## Backward Compatibility

- **Build logs**: Still at `.bengal-build.log` for compatibility (may move in future)
- **Custom paths**: Users can still specify custom paths for profiles/logs
- **Cache location**: Unchanged (already in `public/.bengal-cache*`)

## Usage Examples

### CLI

```bash
# Profile with default organized path
bengal build --perf-profile

# Profile with custom path (still supported)
bengal build --perf-profile my-custom.stats

# Custom log file
bengal build --log-file debug.log
```

### Code

```python
from bengal.utils.paths import BengalPaths

# Get organized profile path
profile_path = BengalPaths.get_profile_path(
    source_dir=Path('.'),
    filename='my_profile.stats'
)
# Returns: .bengal/profiles/my_profile.stats

# With custom override
profile_path = BengalPaths.get_profile_path(
    source_dir=Path('.'),
    custom_path=Path('/tmp/profile.stats'),
    filename='default.stats'
)
# Returns: /tmp/profile.stats
```

## Testing

All modified files passed linting with no errors:
- ✅ `bengal/utils/paths.py`
- ✅ `bengal/utils/__init__.py`
- ✅ `tests/performance/profile_site.py`
- ✅ `bengal/cli/commands/build.py`
- ✅ `bengal/cli.py`

## Future Enhancements

1. **Migrate build logs** to `.bengal/logs/build.log` (currently `.bengal-build.log` for compatibility)
2. **Add log rotation** for long-running dev server logs
3. **Profile management commands** (e.g., `bengal profile list`, `bengal profile clean`)
4. **Cache inspection tools** (e.g., `bengal cache stats`)

## Conclusion

Bengal now automatically organizes all generated files into appropriate directories, providing a clean and predictable structure. Users no longer need to manually manage or clean up scattered build artifacts - everything is in its proper place and properly .gitignored.

The implementation follows best practices:
- ✅ Separation of concerns (source vs. generated)
- ✅ Easy cleanup (atomic directory removal)
- ✅ Git-friendly (proper .gitignore patterns)
- ✅ Extensible (centralized path management)
- ✅ Backward compatible (existing workflows still work)
