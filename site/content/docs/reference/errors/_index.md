---
title: Error Code Reference
nav_title: Error Codes
description: Complete reference for all Bengal error codes with explanations and solutions
weight: 50
icon: bug
tags: [reference, errors, troubleshooting]
---

# Error Code Reference

Bengal uses prefixed error codes for quick identification and searchability. Each code links to its entry below with explanations and solutions.

## Code Systems

Bengal has two code systems:

- **Build Errors (Axxx-Xxxx)**: Errors that occur during the build process. These stop the build or cause content issues.
- **Health Codes (Hxxx)**: Health check warnings and suggestions from `bengal validate`. See [Health Check Codes](/docs/reference/errors/health-codes/) for the complete reference.

## Build Error Categories

| Prefix | Category | Description |
|--------|----------|-------------|
| A | Cache | Build cache operations errors |
| C | Config | Configuration loading and validation errors |
| D | Discovery | Content and section discovery errors |
| G | Graph | Graph analysis errors |
| N | Content | Content file parsing and frontmatter errors |
| P | Parsing | YAML, JSON, TOML, and markdown parsing errors |
| R | Rendering | Template rendering and output generation errors |
| S | Server | Development server errors |
| T | Template Function | Shortcode, directive, and icon errors |
| X | Asset | Static asset processing errors |

---

## Cache Errors (Axxx) {#cache}

### A001: Cache Corruption {#a001}

The build cache has become corrupted and cannot be read.

**Common Causes**
- Interrupted build process
- Disk space issues during cache write
- Manual modification of cache files

**How to Fix**
1. Delete the `.bengal/cache/` directory
2. Run `bengal build` to regenerate the cache

---

### A002: Cache Version Mismatch {#a002}

The cache was created with a different Bengal version.

**Common Causes**
- Bengal was upgraded or downgraded
- Cache from a different project

**How to Fix**
1. Delete the `.bengal/cache/` directory
2. Run `bengal build` to regenerate with current version

---

### A003: Cache Read Error {#a003}

Failed to read from the build cache.

**Common Causes**
- File permissions issue
- Cache file was deleted mid-build
- Disk read error

**How to Fix**
1. Check file permissions on `.bengal/cache/`
2. Delete and regenerate the cache if corrupted

---

### A004: Cache Write Error {#a004}

Failed to write to the build cache.

**Common Causes**
- Insufficient disk space
- File permissions issue
- Directory doesn't exist

**How to Fix**
1. Check available disk space
2. Verify write permissions on `.bengal/` directory

---

### A005: Cache Invalidation Error {#a005}

Failed to invalidate stale cache entries.

**Common Causes**
- Cache corruption
- Concurrent build processes

**How to Fix**
1. Delete `.bengal/cache/` and rebuild
2. Avoid running multiple builds simultaneously

---

### A006: Cache Lock Timeout {#a006}

Could not acquire cache lock within timeout period.

**Common Causes**
- Another Bengal process is running
- Previous build crashed while holding lock

**How to Fix**
1. Wait for other builds to complete
2. Delete `.bengal/cache/*.lock` files if no builds are running

---

## Config Errors (Cxxx) {#config}

### C001: Config YAML Parse Error {#c001}

Invalid YAML/TOML syntax in configuration file.

The configuration file (`bengal.toml` or `bengal.yaml`) contains invalid syntax that cannot be parsed. Bengal cannot start without a valid configuration file.

**Common Causes**
- Missing colons after keys
- Incorrect indentation (YAML uses spaces, not tabs)
- Unquoted special characters (`:`, `#`, `@`)
- Unclosed quotes or brackets
- Mixing YAML and TOML syntax

**How to Fix**
1. Check the line number in the error message
2. Look for the common issues listed above
3. Use a YAML validator: https://yamlvalidator.com
4. Compare with the example config in Bengal documentation

**Example**

❌ **Invalid**:
```yaml
title My Site    # Missing colon
```

✅ **Valid**:
```yaml
title: My Site
```

---

### C002: Config Key Missing {#c002}

A required configuration key was not found.

The configuration file is missing a required key. Some Bengal features require specific configuration to be present.

**Common Causes**
- Typo in configuration key name
- Key defined in wrong section
- Missing required configuration section

**How to Fix**
1. Check the spelling of the configuration key
2. Verify the key is in the correct section
3. Review the Bengal configuration reference

---

### C003: Config Invalid Value {#c003}

A configuration value failed validation.

A configuration value is not valid for its setting. This could be a wrong type, an invalid option, or a value outside allowed range.

**Common Causes**
- Using an unsupported value for a setting
- Type mismatch (e.g., string instead of number)
- Invalid file format extension
- Unsupported template engine name

**How to Fix**
1. Check the allowed values for the setting
2. Verify the type matches what's expected
3. Review the configuration reference documentation

**Example**

❌ **Invalid**:
```toml
template_engine = "unknown_engine"
```

✅ **Valid**:
```toml
template_engine = "kida"  # default, or "jinja2", "mako", "patitas"
```

---

### C004: Config Type Mismatch {#c004}

Configuration value has wrong type.

**Common Causes**
- String provided where number expected
- List provided where single value expected
- Boolean syntax error

**How to Fix**
1. Check the expected type in documentation
2. Use correct YAML/TOML type syntax

---

### C005: Config Defaults Missing {#c005}

Required default configuration could not be loaded.

**Common Causes**
- Bengal installation is corrupted
- Custom defaults file is missing

**How to Fix**
1. Reinstall Bengal: `pip install --force-reinstall bengal`
2. Check that default config files exist in installation

---

### C006: Config Environment Unknown {#c006}

Specified environment configuration not found.

**Common Causes**
- Typo in environment name
- Environment config file missing

**How to Fix**
1. Check available environments in `bengal.toml`
2. Create the environment config if needed

---

### C007: Config Circular Reference {#c007}

Configuration contains circular references.

**Common Causes**
- Config A includes B, which includes A
- Self-referencing configuration value

**How to Fix**
1. Review configuration includes and references
2. Break the circular dependency

---

### C008: Config Deprecated Key {#c008}

Configuration uses a deprecated key.

**Common Causes**
- Using old configuration format
- Key was renamed in newer version

**How to Fix**
1. Check the migration guide for the new key name
2. Update configuration to use current syntax

---

## Discovery Errors (Dxxx) {#discovery}

### D001: Content Directory Not Found {#d001}

The content directory could not be located.

Bengal could not find the content directory specified in your configuration. Without content, there's nothing to build.

**Common Causes**
- Running bengal from wrong directory
- Content directory was renamed or moved
- Typo in content_dir configuration

**How to Fix**
1. Verify you're in the site root directory
2. Check that `content/` directory exists
3. Run `bengal init` to create site structure

---

### D002: Invalid Content Path {#d002}

Content path contains invalid characters or structure.

**Common Causes**
- Special characters in file/folder names
- Path too long for filesystem
- Symbolic link issues

**How to Fix**
1. Use only alphanumeric characters, hyphens, and underscores
2. Keep paths reasonably short
3. Avoid symbolic links in content directory

---

### D003: Section Index Missing {#d003}

A content section is missing its `_index.md` file.

**Common Causes**
- Section folder created without index
- Index file accidentally deleted

**How to Fix**
1. Create `_index.md` in the section folder
2. Add required frontmatter with title

---

### D004: Circular Section Reference {#d004}

Sections reference each other in a loop.

**Common Causes**
- Section A's parent is B, but B's parent is A
- Symbolic links creating loops

**How to Fix**
1. Review section hierarchy
2. Remove circular parent references

---

### D005: Duplicate Page Path {#d005}

Multiple pages have the same URL.

Two or more pages are configured to output to the same URL. This would cause one to overwrite the other.

**Common Causes**
- Duplicate slugs in frontmatter
- Conflicting autodoc output paths
- Multiple index files in same directory

**How to Fix**
1. Give each page a unique slug
2. Check autodoc configuration for conflicts
3. Remove duplicate content files

---

### D006: Invalid File Pattern {#d006}

File pattern in configuration is invalid.

**Common Causes**
- Malformed glob pattern
- Unsupported pattern syntax

**How to Fix**
1. Check glob pattern syntax
2. Test pattern with `bengal explain patterns`

---

### D007: Permission Denied {#d007}

Cannot access file or directory due to permissions.

**Common Causes**
- File owned by different user
- Read permissions not set
- File system mounted read-only

**How to Fix**
1. Check file permissions: `ls -la`
2. Fix permissions: `chmod 644 filename`
3. Verify filesystem is not read-only

---

## Graph Errors (Gxxx) {#graph}

### G001: Graph Not Built {#g001}

Attempted to query graph before it was built.

**Common Causes**
- Calling graph functions before `build()`
- Build failed silently

**How to Fix**
1. Ensure `site.build()` completes before graph queries
2. Check for earlier build errors

---

### G002: Graph Invalid Parameter {#g002}

Invalid parameter passed to graph function.

**Common Causes**
- Page ID doesn't exist
- Invalid depth or limit value

**How to Fix**
1. Verify page IDs exist in the graph
2. Use positive integers for depth/limit

---

### G003: Graph Cycle Detected {#g003}

Circular reference detected in page relationships.

**Common Causes**
- Page A links to B, B links to A as prerequisite
- Circular navigation structure

**How to Fix**
1. Review page relationships
2. Break the cycle by removing one reference

---

### G004: Graph Disconnected Component {#g004}

Pages are not reachable from navigation.

**Common Causes**
- Orphan pages without parent section
- Missing navigation links

**How to Fix**
1. Add pages to appropriate sections
2. Create navigation links to disconnected pages

---

### G005: Graph Analysis Failed {#g005}

Graph analysis computation failed.

**Common Causes**
- Graph is too large
- Memory constraints
- Invalid graph state

**How to Fix**
1. Reduce graph size if possible
2. Increase available memory
3. Rebuild the site from scratch

---

## Content Errors (Nxxx) {#content}

### N001: Frontmatter Invalid {#n001}

Cannot parse frontmatter in content file.

The frontmatter (YAML between `---` delimiters) in a content file contains syntax errors and cannot be parsed.

**Common Causes**
- Missing closing `---` delimiter
- Invalid YAML syntax in frontmatter
- Tabs instead of spaces for indentation
- Special characters not properly quoted

**How to Fix**
1. Check that frontmatter has both opening and closing `---`
2. Validate YAML syntax in the frontmatter
3. Ensure dates are in ISO format (YYYY-MM-DD)
4. Quote values with special characters

**Example**

❌ **Invalid**:
```markdown
---
title: My Post
date: yesterday  # Invalid date
---
```

✅ **Valid**:
```markdown
---
title: My Post
date: 2024-01-15
---
```

---

### N002: Frontmatter Date Invalid {#n002}

Date value in frontmatter cannot be parsed.

**Common Causes**
- Non-standard date format
- Invalid date (e.g., February 30)
- Timezone parsing issue

**How to Fix**
1. Use ISO format: `YYYY-MM-DD`
2. Optionally add time: `YYYY-MM-DDTHH:MM:SS`
3. Verify the date is valid

---

### N003: Content File Encoding {#n003}

File uses unsupported character encoding.

**Common Causes**
- File saved in non-UTF-8 encoding
- Binary data in text file
- Corrupted file

**How to Fix**
1. Convert file to UTF-8: `iconv -f LATIN1 -t UTF-8 file.md`
2. Re-save file with UTF-8 encoding in your editor
3. Check for binary content

---

### N004: Content File Not Found {#n004}

Referenced content file does not exist.

**Common Causes**
- Typo in filename reference
- File was moved or deleted
- Case sensitivity mismatch

**How to Fix**
1. Verify the file path is correct
2. Check for case sensitivity issues
3. Restore or recreate the file

---

### N005: Content Markdown Error {#n005}

Markdown parsing failed.

**Common Causes**
- Malformed markdown syntax
- Unclosed code blocks
- Invalid HTML embedded in markdown

**How to Fix**
1. Check for unclosed code fences (```)
2. Validate embedded HTML
3. Use a markdown linter

---

### N006: Content Shortcode Error {#n006}

Shortcode in content failed to render.

**Common Causes**
- Invalid shortcode syntax
- Missing required shortcode argument
- Shortcode function raised error

**How to Fix**
1. Check shortcode syntax: `{{< shortcode arg="value" >}}`
2. Verify all required arguments are provided
3. Review shortcode documentation

---

### N007: Content TOC Extraction Error {#n007}

Failed to extract table of contents.

**Common Causes**
- Invalid heading structure
- Heading without text
- Parser error

**How to Fix**
1. Ensure headings have text content
2. Use proper heading hierarchy (h1 → h2 → h3)

---

### N008: Content Taxonomy Invalid {#n008}

Invalid taxonomy value in frontmatter.

**Common Causes**
- Taxonomy value is not a list
- Invalid taxonomy name
- Taxonomy not defined in config

**How to Fix**
1. Use list syntax for taxonomies: `tags: [a, b, c]`
2. Check taxonomy is defined in config
3. Verify taxonomy value format

---

### N009: Content Weight Invalid {#n009}

Weight value must be a number.

**Common Causes**
- Weight is a string instead of number
- Weight contains non-numeric characters

**How to Fix**
1. Use integer for weight: `weight: 10`
2. Remove quotes around weight value

---

### N010: Content Slug Invalid {#n010}

Slug contains invalid characters.

**Common Causes**
- Spaces in slug
- Special characters
- Non-ASCII characters

**How to Fix**
1. Use only lowercase letters, numbers, and hyphens
2. Example: `slug: my-page-title`

---

## Parsing Errors (Pxxx) {#parsing}

### P001: YAML Parse Error {#p001}

YAML file contains syntax errors.

**Common Causes**
- Indentation with tabs instead of spaces
- Missing colon after key
- Unquoted special characters

**How to Fix**
1. Use spaces for indentation (2 or 4 spaces)
2. Ensure colons after keys: `key: value`
3. Quote special values: `title: "My: Title"`

---

### P002: JSON Parse Error {#p002}

JSON file contains syntax errors.

**Common Causes**
- Trailing comma in array or object
- Missing quotes around keys
- Single quotes instead of double

**How to Fix**
1. Remove trailing commas
2. Use double quotes for strings
3. Validate with `python -m json.tool file.json`

---

### P003: TOML Parse Error {#p003}

TOML file contains syntax errors.

**Common Causes**
- Invalid table syntax
- Missing quotes around strings with spaces
- Incorrect date format

**How to Fix**
1. Use `[section]` for tables
2. Quote strings with spaces
3. Use RFC 3339 date format

---

### P004: Markdown Parse Error {#p004}

Markdown file cannot be parsed.

**Common Causes**
- Unclosed code blocks
- Invalid HTML
- Corrupted file

**How to Fix**
1. Check for unclosed ``` code fences
2. Validate embedded HTML
3. Check file encoding

---

### P005: Frontmatter Delimiter Missing {#p005}

Content file is missing frontmatter delimiters.

**Common Causes**
- Missing opening `---`
- Missing closing `---`
- Extra whitespace before delimiter

**How to Fix**
1. Ensure file starts with `---`
2. Add closing `---` after frontmatter
3. Remove whitespace before first delimiter

**Example**

✅ **Correct**:
```markdown
---
title: My Page
---

Content starts here.
```

---

### P006: Glossary Parse Error {#p006}

Glossary file contains errors.

**Common Causes**
- Invalid glossary format
- Missing required fields
- Duplicate term definitions

**How to Fix**
1. Check glossary file format
2. Ensure each term has required fields
3. Remove duplicate definitions

---

## Rendering Errors (Rxxx) {#rendering}

### R001: Template Not Found {#r001}

Template file could not be located.

Bengal could not find the specified template file. This usually happens when a page requests a template that doesn't exist.

**Common Causes**
- Typo in template name in frontmatter
- Template file not in templates/ directory
- Theme template not found
- Case sensitivity issue (templates/Page.html vs page.html)

**How to Fix**
1. Check the template name in your page's frontmatter
2. Verify the template file exists in templates/ or theme
3. Check for case sensitivity in the filename
4. Run `bengal explain templates` to see available templates

**Example**

❌ **Frontmatter referencing missing template**:
```yaml
---
layout: custom-page  # This template doesn't exist
---
```

✅ **Using existing template**:
```yaml
---
layout: page  # This template exists
---
```

---

### R002: Template Syntax Error {#r002}

Jinja2/template syntax error.

The template contains a syntax error that prevents it from being parsed. This is usually a Jinja2 syntax issue.

**Common Causes**
- Missing `{% end %}` or `{% endfor %}`
- Unclosed `{{` or `{%` tags
- Invalid filter syntax
- Mismatched block names

**How to Fix**
1. Check the line number in the error message
2. Ensure all blocks have matching end tags
3. Verify filter syntax: `{{ value | filter }}`
4. Check for unclosed variable tags

**Example**

❌ **Missing end tag**:
```kida
{% if page.draft %}
  Draft content
{# Missing {% end %} #}
```

✅ **Correct**:
```kida
{% if page.draft %}
  Draft content
{% end %}
```

---

### R003: Template Undefined Variable {#r003}

Variable used in template is not defined.

**Common Causes**
- Typo in variable name
- Variable not passed to template context
- Using variable before it's set

**How to Fix**
1. Check spelling of variable name
2. Verify variable is in template context
3. Use `{{ variable | default("") }}` for optional variables

---

### R004: Template Filter Error {#r004}

Template filter raised an error.

**Common Causes**
- Passing wrong type to filter
- Filter not registered
- Filter function raised exception

**How to Fix**
1. Check filter expects the input type you're providing
2. Verify custom filters are registered
3. Review filter documentation

---

### R005: Template Include Error {#r005}

Could not include referenced template.

**Common Causes**
- Included template doesn't exist
- Circular include detected
- Include path is incorrect

**How to Fix**
1. Verify included template path
2. Check for circular includes
3. Use relative path from templates/ directory

---

### R006: Template Macro Error {#r006}

Macro definition or call failed.

**Common Causes**
- Macro not defined
- Wrong number of arguments
- Macro raised error

**How to Fix**
1. Ensure macro is imported: `{% from "macros.html" import mymacro %}`
2. Check macro signature matches call
3. Review macro implementation

---

### R007: Template Block Error {#r007}

Template block inheritance error.

**Common Causes**
- Block name mismatch with parent
- Missing parent template
- Invalid block nesting

**How to Fix**
1. Verify block names match parent template
2. Check parent template exists
3. Ensure blocks are not nested incorrectly

---

### R008: Template Context Error {#r008}

Template context is invalid or corrupted.

**Common Causes**
- Custom context processor raised error
- Conflicting context values
- Memory issue with large context

**How to Fix**
1. Review custom context processors
2. Check for conflicting variable names
3. Reduce context size if very large

---

### R009: Template Inheritance Error {#r009}

Template inheritance chain is invalid.

**Common Causes**
- Parent template not found
- Circular inheritance
- Invalid extends syntax

**How to Fix**
1. Verify parent template exists
2. Check for circular inheritance
3. Use correct syntax: `{% extends "base.html" %}`

---

### R010: Render Output Error {#r010}

Failed to write rendered output.

**Common Causes**
- Disk full
- Permission denied
- Invalid output path

**How to Fix**
1. Check available disk space
2. Verify write permissions on output directory
3. Check output path is valid

---

## Server Errors (Sxxx) {#server}

### S001: Server Port In Use {#s001}

The requested port is already in use.

**Common Causes**
- Another bengal server running
- Different application using the port
- Previous server didn't shut down cleanly

**How to Fix**
1. Use a different port: `bengal serve --port 8001`
2. Find and stop the process using the port
3. Wait for port to be released (can take ~30 seconds)

---

### S002: Server Bind Error {#s002}

Could not bind to the network interface.

**Common Causes**
- Permission denied for port < 1024
- Network interface doesn't exist
- Firewall blocking

**How to Fix**
1. Use port >= 1024 (no sudo required)
2. Check bind address is valid
3. Review firewall settings

---

### S003: Server Reload Error {#s003}

Live reload failed to trigger.

**Common Causes**
- WebSocket connection lost
- Browser extension blocking
- File watcher issue

**How to Fix**
1. Refresh browser manually
2. Disable browser extensions temporarily
3. Restart the dev server

---

### S004: Server WebSocket Error {#s004}

WebSocket connection for live reload failed.

**Common Causes**
- Proxy not configured for WebSocket
- Browser doesn't support WebSocket
- Network issue

**How to Fix**
1. Configure proxy to forward WebSocket
2. Try a different browser
3. Check network connectivity

---

### S005: Server Static File Error {#s005}

Could not serve static file.

**Common Causes**
- File doesn't exist
- Permission denied
- Path traversal blocked

**How to Fix**
1. Verify file exists in static/ directory
2. Check file permissions
3. Use valid relative paths only

---

## Template Function Errors (Txxx) {#template-function}

### T001: Shortcode Not Found {#t001}

Referenced shortcode is not registered.

**Common Causes**
- Typo in shortcode name
- Shortcode not defined
- Shortcode file not loaded

**How to Fix**
1. Check shortcode name spelling
2. Verify shortcode is defined in `shortcodes/` directory
3. Run `bengal explain shortcodes` to list available shortcodes

---

### T002: Shortcode Argument Error {#t002}

Shortcode received invalid arguments.

**Common Causes**
- Missing required argument
- Wrong argument type
- Unknown argument name

**How to Fix**
1. Check shortcode documentation for required arguments
2. Verify argument types match expected
3. Remove unknown arguments

---

### T003: Shortcode Render Error {#t003}

Shortcode execution failed.

**Common Causes**
- Shortcode code raised exception
- Invalid return value
- Template error in shortcode

**How to Fix**
1. Check shortcode implementation
2. Review error message for details
3. Test shortcode in isolation

---

### T004: Directive Not Found {#t004}

Referenced directive is not registered.

**Common Causes**
- Typo in directive name
- Directive not defined
- Using MyST syntax for unregistered directive

**How to Fix**
1. Check directive name spelling
2. Verify directive is registered
3. Review available directives in documentation

---

### T005: Directive Argument Error {#t005}

Directive received invalid arguments.

**Common Causes**
- Missing required argument
- Invalid argument format
- Argument value out of range

**How to Fix**
1. Check directive documentation
2. Provide all required arguments
3. Use correct argument format

---

### T006: Directive Since Empty {#t006}

The `{since}` directive requires a version parameter.

**How to Fix**

Provide a version string:

```markdown
{since}`v2.0`
```

---

### T007: Directive Deprecated Empty {#t007}

The `{deprecated}` directive requires a version parameter.

**How to Fix**

Provide a version string:

```markdown
{deprecated}`v1.5`
```

---

### T008: Directive Changed Empty {#t008}

The `{changed}` directive requires a version parameter.

**How to Fix**

Provide a version string:

```markdown
{changed}`v2.1`
```

---

### T009: Directive Include Not Found {#t009}

The included file in directive was not found.

**Common Causes**
- Typo in file path
- File doesn't exist
- Incorrect relative path

**How to Fix**
1. Verify file path is correct
2. Check file exists at specified location
3. Use path relative to content directory

---

### T010: Icon Not Found {#t010}

An icon referenced in frontmatter, directive, or inline syntax does not exist in the icon search path.

Bengal searches these directories in order:

1. **Site theme icons**: `themes/{theme}/assets/icons/` in your project
2. **Theme icons**: Icons bundled with the theme
3. **Parent theme icons**: If your theme extends another
4. **Bengal defaults**: Phosphor icons (unless `extend_defaults: false`)

**Common Causes**
- Typo in icon name (e.g., `icon: warnng` instead of `icon: warning`)
- Using an icon that hasn't been added to your theme
- Referencing a Phosphor icon name that differs from Bengal's naming
- Using `extend_defaults: false` without providing all needed icons

**How to Fix**
1. Run `bengal icons` to list available icons
2. Fix typos in icon names
3. Add custom icons to `themes/{theme}/assets/icons/`

**Adding Custom Icons**

Create an icons directory in your theme:

```tree
themes/my-theme/assets/icons/
├── my-custom-icon.svg   # New icon
└── warning.svg          # Overrides default
```

See [Icon Reference](/docs/reference/icons/#custom-icons) for SVG format requirements and configuration options.

---

## Asset Errors (Xxxx) {#asset}

### X001: Asset Not Found {#x001}

Static asset file could not be located.

**Common Causes**
- Typo in asset path
- Asset file missing
- Case sensitivity mismatch

**How to Fix**
1. Check asset path in template or content
2. Verify file exists in `static/` directory
3. Check for case sensitivity issues

---

### X002: Asset Invalid Path {#x002}

Asset path contains invalid characters.

**Common Causes**
- Path traversal attempt (`../`)
- Special characters in path
- Absolute path used

**How to Fix**
1. Use relative paths only
2. Remove special characters
3. Don't use `..` in asset paths

---

### X003: Asset Processing Failed {#x003}

Asset pipeline processing failed.

**Common Causes**
- Invalid image format
- Processing tool not available
- Memory limit exceeded

**How to Fix**
1. Verify asset file is valid
2. Install required processing tools
3. Reduce asset size or processing complexity

---

### X004: Asset Copy Error {#x004}

Failed to copy asset to output directory.

**Common Causes**
- Permission denied
- Disk full
- Target file locked

**How to Fix**
1. Check write permissions on output directory
2. Free up disk space
3. Close applications that may lock files

---

### X005: Asset Fingerprint Error {#x005}

Failed to generate asset fingerprint/hash.

**Common Causes**
- File read error
- Very large file
- Memory issue

**How to Fix**
1. Check file is readable
2. Reduce file size if very large
3. Increase available memory

---

### X006: Asset Minify Error {#x006}

Asset minification failed.

**Common Causes**
- Invalid CSS/JS syntax
- Minifier not available
- Unsupported features in source

**How to Fix**
1. Validate CSS/JS syntax
2. Install minification dependencies
3. Check for syntax not supported by minifier

---

## Getting Help

If you encounter an error:

1. Check the error message and suggestion in the CLI output
2. Search this page for the error code (Ctrl+F / Cmd+F)
3. Review the troubleshooting steps above
4. Check the [troubleshooting guide](/docs/building/troubleshooting/)

For bugs or unclear errors, please [open an issue](https://github.com/bengal-ssg/bengal/issues).
