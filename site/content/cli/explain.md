---
title: "explain"
type: "cli-reference"
css_class: "api-content"
source_file: "bengal/cli/commands/explain.py"
description: "🔍 Explain how a page is built - shows source info, template chain, dependencies, cache status, and diagnostics."
weight: 5
---

# explain

**Type:** Command  
**Source:** [View source](https://github.com/lbliii/bengal/blob/main/bengal/cli/commands/explain.py)

:::{badge} Command
:class: badge-secondary
:::

**Command:** `bengal explain`

🔍 Explain how a page is built.

Shows complete traceability for any page including source file information, frontmatter metadata, template inheritance chain, dependencies, shortcodes/directives used, cache status (HIT/MISS/STALE), and output location.

## Usage

```bash
bengal explain [OPTIONS] PAGE_PATH [SOURCE]
```

## Arguments

### `page_path` (required)

Path to the page to explain. Can be specified as:
- **Relative to content dir**: `docs/guide.md`
- **Full path**: `content/docs/guide.md`  
- **Partial match**: `guide.md` (if unique)

### `source` (optional)

Site root directory. Defaults to current directory (`.`).

## Options

### `-v, --verbose`

Show additional details including timing information and template variables.

### `-d, --diagnose`

Check for issues such as broken internal links, missing assets, and template errors.

### `--json`

Output explanation as JSON for programmatic use. Useful for scripting and CI integration.

### `--traceback [full|compact|minimal|off]`

Control traceback verbosity level.

## Output Sections

The explain command displays information in organized panels:

### 📁 Source

Information about the source file:
- **Path**: Location of the source markdown file
- **Size**: File size in human-readable format
- **Lines**: Line count
- **Modified**: Last modification timestamp
- **Encoding**: File encoding (usually UTF-8)

### 📝 Frontmatter

Parsed frontmatter metadata from the page including:
- `title`, `description`, `date`, `tags`, `type`, `template`, `weight`
- Any custom frontmatter fields

### 🎨 Template Chain

Template inheritance hierarchy showing:
- Which template renders the page
- Parent templates (extends chain)
- Included partials
- Theme source for each template

### 🔗 Dependencies

All dependencies that affect page output:
- **Content**: Section index pages, parent pages
- **Templates**: Template files used in rendering
- **Data**: Data files referenced by the page
- **Assets**: Images, diagrams, and other assets
- **Includes**: Files included via shortcodes

### 🧩 Directives/Shortcodes Used

List of MyST directives and shortcodes found in the content:
- Directive name
- Number of uses
- Line numbers where they appear

### 💾 Cache Status

Build cache status for the page:
- **HIT** ✅: Page is cached and valid
- **STALE** ⚠️: Cache exists but is outdated
- **MISS** ❌: Page not in cache
- Reason for status (e.g., "Source file modified")
- Which cache layers are populated (parsed content, rendered HTML)

### 📤 Output

Output information:
- **URL**: Public URL for the page
- **Path**: Output file path
- **Size**: Rendered HTML size (if built)

### ⚠️ Issues (with --diagnose)

When using `--diagnose`, potential issues are listed:
- **Template errors**: Missing templates, syntax errors
- **Broken links**: Internal links to non-existent pages
- **Missing assets**: Referenced images that don't exist

## Examples

### Basic explanation

```bash
bengal explain docs/getting-started.md
```

### Explain with issue diagnosis

```bash
bengal explain docs/api/reference.md --diagnose
```

### JSON output for CI

```bash
bengal explain docs/guide.md --json > page-info.json
```

### Verbose mode

```bash
bengal explain content/posts/hello-world.md --verbose
```

### Explain from different directory

```bash
bengal explain docs/guide.md /path/to/site
```

## Use Cases

### Debugging Template Issues

When a page isn't rendering as expected, use explain to see which template is being used:

```bash
bengal explain my-page.md
```

Check the "Template Chain" section to verify the correct template is selected.

### Understanding Cache Behavior

To understand why a page is or isn't being cached:

```bash
bengal explain my-page.md
```

The "Cache Status" section shows whether the page is cached and why it might be stale.

### Finding Broken Links

Before publishing, check pages for broken internal links:

```bash
bengal explain docs/index.md --diagnose
```

### CI/CD Integration

Export page metadata for automated checks:

```bash
# Check cache status in CI
STATUS=$(bengal explain docs/guide.md --json | jq -r '.cache.status')
if [ "$STATUS" = "STALE" ]; then
  echo "Warning: Page cache is stale"
fi
```

## Related Commands

- [`bengal validate`](/cli/validate/) - Run health checks on entire site
- [`bengal site build`](/cli/site/build/) - Build the site
- [`bengal health linkcheck`](/cli/health/linkcheck/) - Check all links

## See Also

- [Build Pipeline Concepts](/docs/about/concepts/build-pipeline/) - How Bengal builds pages
- [Templating Guide](/docs/about/concepts/templating/) - Template inheritance
- [Configuration Reference](/docs/about/concepts/configuration/) - Site configuration

