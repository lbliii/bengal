# CLI Template Whitespace Cleanup

**Date**: October 4, 2025  
**Status**: Complete  
**Impact**: All CLI autodoc generated pages

---

## Problem

The HTML output for CLI command documentation pages had excessive whitespace issues:

1. **Extra blank lines in code blocks** - unnecessary whitespace before closing ```
2. **Multiple blank lines between sections** - up to 3 blank lines between Options and Help
3. **Inconsistent spacing** - double blank lines after description sections
4. **Poor visual presentation** - made documentation look unprofessional

---

## Solution

Fixed two Jinja2 templates in `bengal/autodoc/templates/cli/`:

### 1. `command.md.jinja2` (Individual Command Pages)

**Changes Made:**

- **Line 13-19**: Fixed double blank line after description
  - Only add blank line before deprecated warning when it exists
  - Otherwise, single blank line between description and Usage

- **Line 24-26**: Fixed code block in Usage section
  - Added blank line before closing ``` for proper formatting
  - Ensures command is on one line, closing tag on next

- **Line 35-40**: Fixed argument metadata handling
  - Only output description + blank line when description exists
  - Removed trailing blank line after metadata

- **Line 51-60**: Fixed option metadata handling  
  - Only output description + blank line when description exists
  - Removed trailing blank line after last metadata field

- **Line 63-81**: Fixed section spacing
  - Removed blank lines after endif for options section
  - Only add blank line before Examples/See Also when they exist
  - Single blank line before Help section

- **Line 84-86**: Fixed Help code block
  - Removed blank line inside code block
  - Proper formatting for help command

### 2. `command-group.md.jinja2` (CLI Index Page)

**Changes Made:**

- **Line 26-29**: Fixed code block in Usage section
  - Added blank line before closing ``` 
  - Ensures command is on one line, closing tag on next

- **Line 47-53**: Fixed Getting Help code block
  - Removed blank line inside code block
  - Proper multi-line help command formatting

---

## Results

### Before
```markdown
## Usage

```bash
main clean [ARGUMENTS] [OPTIONS]```    ❌ Closing tag on same line

## Arguments

### source


                                        ❌ Double blank line
**Type:** `path`  
**Required:** No  
**Default:** `.`

                                        ❌ Extra blank line after metadata
## Options

### --config

Path to config file (default: bengal.toml)

**Type:** `path`  

### --force, -f

Skip confirmation prompt

**Type:** Flag (boolean)  
**Default:** `False`  


                                        ❌ THREE blank lines
## Help

```bash
main clean --help
                                        ❌ Blank line inside code block
```
```

### After
```markdown
## Usage

```bash
main clean [ARGUMENTS] [OPTIONS]
```                                     ✅ Proper code block

## Arguments

### source

**Type:** `path`  
**Required:** No  
**Default:** `.`                       ✅ No extra blank line

## Options

### --config

Path to config file (default: bengal.toml)

**Type:** `path`  

### --force, -f

Skip confirmation prompt

**Type:** Flag (boolean)  
**Default:** `False`  
                                       ✅ Single blank line
## Help

```bash
main clean --help
```                                    ✅ No extra blank line
```

---

## Files Regenerated

After template fixes, regenerated all CLI documentation:

```bash
cd examples/showcase
python -m bengal.cli autodoc-cli --app bengal.cli:main --output content/cli --clean
python -m bengal.cli build
```

Generated pages:
- `content/cli/index.md` - main CLI index
- `content/cli/commands/autodoc.md`
- `content/cli/commands/autodoc-cli.md`
- `content/cli/commands/build.md`
- `content/cli/commands/clean.md`
- `content/cli/commands/cleanup.md`
- `content/cli/commands/serve.md`
- `content/cli/commands/new.md`
- `content/cli/commands/page.md`
- `content/cli/commands/site.md`

---

## Quality Improvements

### Visual Quality
- **Before**: Scattered, unprofessional appearance with inconsistent spacing
- **After**: Clean, consistent, professional documentation

### HTML Output
- **Before**: Multiple `<p><br></p>` tags creating excessive whitespace
- **After**: Proper semantic HTML with clean spacing

### Maintainability
- Templates now have clear, consistent whitespace rules
- Conditional blank lines only appear when sections exist
- No redundant blank lines between template blocks

---

## Technical Details

### Jinja2 Whitespace Handling

Key learnings about Jinja2 template whitespace:

1. **Newlines after tags**: A newline after `{% endif %}` is preserved
2. **Blank lines in templates**: Create blank lines in output
3. **Conditional spacing**: Use `{% if section %}` + blank line pattern for optional sections
4. **Code blocks**: Always need blank line before closing ``` for proper markdown rendering

### Best Practices Applied

1. **Single blank line between major sections** (Usage, Arguments, Options, Help)
2. **Conditional blank lines** before optional sections (Examples, See Also)
3. **No blank lines inside code blocks** (except for multi-line commands)
4. **Description handling**: Only output description + blank when description exists

---

## Impact

- ✅ All 8 CLI command pages now have clean formatting
- ✅ Main CLI index page properly formatted
- ✅ Consistent whitespace across all auto-generated CLI documentation
- ✅ Professional, publication-ready appearance
- ✅ Template improvements will benefit all future CLI documentation generation

---

## Next Steps

Template improvements are now part of the autodoc system and will automatically apply to:
- Any new CLI commands added to Bengal
- Any external CLI apps documented using `bengal autodoc-cli`
- Future regenerations of CLI documentation

