---
title: Health Check Codes Reference
nav_title: Health Codes
description: Complete reference for all Bengal health check codes with explanations and fixes
weight: 10
icon: stethoscope
tags: [reference, health, validation]
---

# Health Check Codes Reference

Bengal's health check system uses prefixed codes for quick identification and filtering. Use `bengal validate --ignore <code>` to suppress specific checks.

## Code Categories

| Prefix | Category | Description |
|--------|----------|-------------|
| H2xx | Links | Internal and external link validation |
| H3xx | Output | Build output directory and asset checks |
| H4xx | URL Collisions | Duplicate URL detection |
| H5xx | Navigation | Next/prev links, breadcrumbs, section navigation |
| H6xx | Menus | Menu configuration and links |
| H7xx | Directives | MyST directive syntax and usage |
| H8xx | Taxonomy | Tags, categories, and pagination |
| H9xx | Cache | Build cache integrity |
| H10xx | Performance | Build timing and throughput |
| H11xx | Sitemap | Sitemap.xml validation |
| H12xx | RSS | RSS feed validation |
| H13xx | Fonts | Font configuration and files |
| H14xx | Assets | CSS, JS, and image files |
| H15xx | Connectivity | Knowledge graph and page linking |
| H16xx | Config | Configuration file validation |
| H17xx | Rendering | Template and HTML output validation |
| H18xx | Tracks | Learning track configuration |
| H19xx | Anchors | Heading anchors and references |
| H20xx | Ownership | Reserved namespace violations |

---

## Link Checks (H2xx) {#links}

### H201: Broken Internal Links {#h201}

Internal links point to pages that don't exist.

**Severity**: Error

**Common Causes**
- Page was moved or deleted
- Typo in link path
- Case sensitivity mismatch

**How to Fix**
1. Update the link to point to the correct page
2. Create the missing page
3. Remove the broken link

---

### H202: Broken External Links {#h202}

External links may be temporarily unavailable or incorrect.

**Severity**: Warning

**Common Causes**
- External site is down
- URL has changed
- Network connectivity issues

**How to Fix**
1. Verify the external URL is correct
2. Update to the new URL if it changed
3. Consider using archive links for important references

---

## Output Checks (H3xx) {#output}

### H301: Suspiciously Small Pages {#h301}

Pages are unusually small, which may indicate rendering errors.

**Severity**: Warning

**Common Causes**
- Template rendering failed silently
- Content is empty
- Fallback HTML was generated

**How to Fix**
1. Review the page content and template
2. Check for rendering errors in build output
3. Ensure content files have actual content

---

### H302: Missing Assets Directory {#h302}

No assets directory found in build output.

**Severity**: Error

**Common Causes**
- Theme assets not discovered
- Asset copy step failed
- Theme not properly configured

**How to Fix**
1. Verify theme configuration in `bengal.toml`
2. Check that theme has assets directory
3. Review build logs for asset copy errors

---

### H303: No CSS Files {#h303}

No CSS files found in the output.

**Severity**: Warning

**Common Causes**
- Theme CSS not copied
- Asset discovery failed
- Theme not applied

**How to Fix**
1. Check theme configuration
2. Verify CSS files exist in theme
3. Review asset discovery settings

---

### H304: No JS Files {#h304}

No JavaScript files found in output (for default theme).

**Severity**: Warning

**Common Causes**
- JS files not copied
- Asset discovery issue
- Theme doesn't include JS

**How to Fix**
1. Check if theme requires JavaScript
2. Verify JS files exist in theme assets
3. Review asset discovery configuration

---

### H305: Output Directory Missing {#h305}

Output directory does not exist after build.

**Severity**: Error

**Common Causes**
- Build process failed
- Output path misconfigured
- Permissions issue

**How to Fix**
1. Check build logs for errors
2. Verify `output_dir` in configuration
3. Ensure write permissions on target directory

---

## URL Collision Checks (H4xx) {#url-collisions}

### H401: URL Collisions Detected {#h401}

Multiple pages output to the same URL.

**Severity**: Error

**Common Causes**
- Duplicate slugs in frontmatter
- Autodoc section index conflicts
- Manual content at same path as generated content

**How to Fix**
1. Rename one page or adjust its slug
2. Move autodoc index to a different path
3. Review URL generation in configuration

---

### H402: Section/Page URL Conflict {#h402}

A page has the same URL as a section.

**Severity**: Warning

**Common Causes**
- Page at same path as section `_index.md`
- Conflicting slug configuration

**How to Fix**
1. Move the page inside the section
2. Use a different slug for the page
3. Consider making the page the section index

---

## Navigation Checks (H5xx) {#navigation}

### H501: Broken Next/Prev Links {#h501}

Pages have navigation links pointing to missing pages.

**Severity**: Error

**Common Causes**
- Bug in navigation system
- Page deleted after navigation computed

**How to Fix**
1. This is likely a Bengal bug - report it
2. Rebuild the site from scratch
3. Check for orphaned navigation entries

---

### H502: Invalid Breadcrumb Ancestors {#h502}

Breadcrumb ancestors don't correspond to real sections.

**Severity**: Error

**Common Causes**
- Section hierarchy corrupted
- Missing section index files

**How to Fix**
1. Ensure all sections have `_index.md`
2. Review section hierarchy
3. Rebuild the site

---

### H503: Invalid Breadcrumb Trails {#h503}

Breadcrumb trails have issues with section hierarchy.

**Severity**: Warning

**Common Causes**
- Section index missing
- Orphaned content pages

**How to Fix**
1. Add `_index.md` to sections
2. Move content into proper sections

---

### H504: Section Navigation Issues {#h504}

Sections with pages are missing index or archive pages.

**Severity**: Warning

**Common Causes**
- Missing `_index.md` in section
- Auto-generated archive not created

**How to Fix**
1. Create `_index.md` for the section
2. Check section configuration

---

### H505: Weight-Based Navigation Issues {#h505}

Navigation ordering by weight has problems.

**Severity**: Error

**Common Causes**
- Bug in navigation system
- Weight values not set correctly

**How to Fix**
1. Verify weight values in frontmatter
2. This may be a Bengal bug - report it

---

### H506: Missing Output Path {#h506}

Pages are missing their output path assignment.

**Severity**: Error

**Common Causes**
- Critical bug in content discovery
- `ContentOrchestrator._set_output_paths()` not called

**How to Fix**
1. This is a Bengal bug - report it
2. Check ContentOrchestrator is running

---

## Menu Checks (H6xx) {#menus}

### H601: Empty Menu {#h601}

A configured menu has no items.

**Severity**: Warning

**Common Causes**
- Menu defined but no items added
- Menu items not matching any pages

**How to Fix**
1. Add items to the menu in configuration
2. Add menu entries in page frontmatter
3. Remove unused menu definition

---

### H602: Broken Menu Links {#h602}

Menu items link to pages that may not exist.

**Severity**: Warning

**Common Causes**
- Linked page was moved or deleted
- Typo in menu URL

**How to Fix**
1. Update menu links to correct pages
2. Remove menu items for deleted pages

---

## Directive Checks (H7xx) {#directives}

### H701: Directive Syntax Errors {#h701}

Directives have syntax errors.

**Severity**: Error

**Common Causes**
- Invalid directive name
- Missing closing backticks
- Malformed options

**How to Fix**
1. Check directive syntax matches MyST format
2. Ensure closing backticks match opening count
3. Review directive documentation

---

### H702: Fence Nesting Issues {#h702}

Directives use 3 backticks but contain code blocks with 3 backticks.

**Severity**: Warning

**Common Causes**
- Code block inside directive uses same fence count
- Nested directives without increasing fence count

**How to Fix**
1. Change directive opening from ``` to ```` (4+ backticks)
2. Or change inner code blocks to use fewer backticks

**Example**

❌ **Nested with same fence count**:
````markdown
```{note}
Here's some code:
```python
print("hello")
```
```
````

✅ **Correct nesting**:
`````markdown
````{note}
Here's some code:
```python
print("hello")
```
````
`````

---

### H703: Incomplete Directives {#h703}

Directives are incomplete (missing required content or options).

**Severity**: Error

**Common Causes**
- Required content missing
- Required options not provided
- Directive body empty when required

**How to Fix**
1. Add required content to directive body
2. Provide all required options
3. Review directive documentation for requirements

---

### H704: Directive Usage Could Be Improved {#h704}

Directives could be simplified or improved.

**Severity**: Warning

**Common Causes**
- Single-item directives that could be simpler
- Overuse of complex directives

**How to Fix**
1. Consider simpler alternatives
2. Review if directive is necessary

---

### H705: Heavy Directive Usage {#h705}

Pages have many directives which may slow rendering.

**Severity**: Warning

**Common Causes**
- Complex documentation pages
- Overuse of directives

**How to Fix**
1. Consider splitting large pages
2. Use simpler formatting where possible

---

### H706: Too Many Tabs {#h706}

Tab blocks have many tabs which slow rendering.

**Severity**: Warning

**Common Causes**
- Many language/platform variations
- Complex comparison content

**How to Fix**
1. Split into multiple tabs blocks
2. Consider separate pages for some variants

---

### H707: Directive Rendering Errors {#h707}

Directives failed to render correctly.

**Severity**: Error

**Common Causes**
- Missing closing fence
- Invalid directive syntax
- Unknown directive type

**How to Fix**
1. Check directive syntax
2. Verify closing fence exists
3. Ensure directive is registered

---

## Taxonomy Checks (H8xx) {#taxonomy}

### H801: Missing Tag Pages {#h801}

Tags have no generated pages.

**Severity**: Error

**Common Causes**
- Dynamic page generation failed
- Tag page generation disabled

**How to Fix**
1. Check `Site.generate_dynamic_pages()` is running
2. Verify taxonomy configuration

---

### H802: Orphaned Tag Pages {#h802}

Tag pages exist but their tags aren't in the taxonomy.

**Severity**: Error

**Common Causes**
- Tag was removed from all content
- Taxonomy not properly collected

**How to Fix**
1. Remove orphaned tag pages
2. Rebuild the site

---

### H803: Missing Tag Index Page {#h803}

Site has tags but no `/tags/` index page.

**Severity**: Warning

**Common Causes**
- Tag index generation disabled
- `Site._create_tag_index_page()` not called

**How to Fix**
1. Enable tag index generation
2. Create manual `/tags/_index.md`

---

### H804: Sections Without Archive {#h804}

Sections have content but no archive/index page.

**Severity**: Warning

**Common Causes**
- Missing `_index.md` in section
- Archive generation disabled

**How to Fix**
1. Create `_index.md` for the section
2. Enable auto-generated archive pages

---

### H805: Taxonomy Consistency Issues {#h805}

Taxonomy collection has inconsistencies.

**Severity**: Error

**Common Causes**
- Bug in `Site.collect_taxonomies()`
- Taxonomy data corruption

**How to Fix**
1. This is likely a Bengal bug - report it
2. Rebuild the site from scratch

---

### H806: Pagination Issues {#h806}

Pagination generation has problems.

**Severity**: Error

**Common Causes**
- Bug in pagination generation
- Invalid pagination configuration

**How to Fix**
1. Check pagination configuration
2. This may be a Bengal bug - report it

---

## Cache Checks (H9xx) {#cache}

### H901: Legacy Cache Location {#h901}

Cache is at legacy location (`public/.bengal-cache.json`).

**Severity**: Warning

**Common Causes**
- Site was built with older Bengal version
- Cache not migrated

**How to Fix**
1. Run `bengal build` to migrate cache automatically
2. Or delete old cache and rebuild

---

### H902: Cache Unreadable {#h902}

Cache file exists but cannot be read.

**Severity**: Error

**Common Causes**
- File permissions issue
- Cache file corrupted
- Disk read error

**How to Fix**
1. Delete cache and rebuild: `bengal clean --cache && bengal build`
2. Check file permissions

---

### H903: Invalid Cache Structure {#h903}

Cache structure is invalid or corrupted.

**Severity**: Error

**Common Causes**
- Cache corruption
- Interrupted build
- Version mismatch

**How to Fix**
1. Delete cache and rebuild: `bengal clean --cache && bengal build`

---

### H904: Very Large Cache File {#h904}

Cache file is larger than 50 MB.

**Severity**: Warning

**Common Causes**
- Many files tracked
- Excessive file tracking
- Cache not cleaned

**How to Fix**
1. Review what's being cached
2. Clean old cache entries

---

### H905: Too Many Cached Files {#h905}

Cache is tracking over 10,000 files.

**Severity**: Warning

**Common Causes**
- Very large site
- Unnecessary files being tracked

**How to Fix**
1. Review file tracking configuration
2. Exclude unnecessary files

---

### H906: Orphaned Cache Dependencies {#h906}

Cache references files that no longer exist.

**Severity**: Warning

**Common Causes**
- Files were deleted
- Normal cache staleness

**How to Fix**
1. Cache will auto-clean on next build
2. Or run `bengal clean --cache && bengal build`

---

## Performance Checks (H10xx) {#performance}

### H1001: Slow Build Time {#h1001}

Build is slower than expected.

**Severity**: Warning

**Common Causes**
- Slow template functions
- Large assets
- System resource constraints

**How to Fix**
1. Profile build with `bengal build --profile`
2. Optimize slow template functions
3. Reduce asset sizes

---

### H1002: Slow Throughput {#h1002}

Pages per second is lower than expected.

**Severity**: Warning

**Common Causes**
- Parallel builds disabled
- Performance bottlenecks

**How to Fix**
1. Enable parallel builds: `parallel = true`
2. Review template complexity
3. Check for blocking operations

---

### H1003: High Average Render Time {#h1003}

Average page render time is high (>100ms/page).

**Severity**: Warning

**Common Causes**
- Complex templates
- Slow template functions
- Large page content

**How to Fix**
1. Simplify templates
2. Optimize template functions
3. Split large pages

---

## Sitemap Checks (H11xx) {#sitemap}

### H1101: Missing Sitemap {#h1101}

Sitemap.xml was not generated.

**Severity**: Warning

**Common Causes**
- Sitemap generation disabled
- `SitemapGenerator` not called

**How to Fix**
1. Enable sitemap generation
2. Check build configuration

---

### H1102: Malformed Sitemap XML {#h1102}

Sitemap XML cannot be parsed.

**Severity**: Error

**Common Causes**
- Sitemap generation bug
- File corruption

**How to Fix**
1. Check sitemap generation logic
2. Rebuild the site

---

### H1103: Invalid Sitemap Root Element {#h1103}

Sitemap root element is not `urlset`.

**Severity**: Error

**How to Fix**
1. This is a Bengal bug - report it
2. Sitemap should have `<urlset>` as root

---

### H1104: Non-Standard Sitemap xmlns {#h1104}

Sitemap uses non-standard namespace.

**Severity**: Warning

**How to Fix**
1. Use standard namespace for compatibility
2. Check sitemap generation template

---

### H1105: Empty Sitemap {#h1105}

Sitemap has no URL elements.

**Severity**: Warning

**Common Causes**
- No publishable pages
- Sitemap generation issue

**How to Fix**
1. Check that site has publishable content
2. Review sitemap generation

---

### H1106: URLs Missing loc Element {#h1106}

Sitemap URLs are missing the required `<loc>` element.

**Severity**: Error

**How to Fix**
1. This is a Bengal bug - report it
2. Each `<url>` must have a `<loc>`

---

### H1107: Relative URLs in Sitemap {#h1107}

Sitemap contains relative URLs instead of absolute.

**Severity**: Error

**Common Causes**
- `baseurl` not configured
- Sitemap generation bug

**How to Fix**
1. Set `baseurl` in configuration
2. Verify sitemap uses absolute URLs

---

### H1108: Duplicate Sitemap URLs {#h1108}

Sitemap contains duplicate URL entries.

**Severity**: Error

**Common Causes**
- URL collision in site
- Sitemap generation bug

**How to Fix**
1. Fix URL collisions (see H401)
2. Report bug if URLs are unique

---

### H1109: Missing Pages in Sitemap {#h1109}

Sitemap has fewer URLs than publishable pages.

**Severity**: Warning

**Common Causes**
- Pages excluded from sitemap
- Pages missing `output_path`

**How to Fix**
1. Review sitemap exclusion settings
2. Check all pages have output paths

---

## RSS Feed Checks (H12xx) {#rss}

### H1201: Missing RSS Feed {#h1201}

RSS feed not generated despite having dated content.

**Severity**: Warning

**Common Causes**
- RSS generation disabled
- `RSSGenerator` not called

**How to Fix**
1. Enable RSS generation
2. Check build configuration

---

### H1202: Malformed RSS XML {#h1202}

RSS feed XML cannot be parsed.

**Severity**: Error

**Common Causes**
- RSS generation bug
- File corruption

**How to Fix**
1. Check RSS generation logic
2. Rebuild the site

---

### H1203: Invalid RSS Root Element {#h1203}

RSS root element is not `rss`.

**Severity**: Error

**How to Fix**
1. This is a Bengal bug - report it
2. RSS feed should have `<rss>` as root

---

### H1204: Non-Standard RSS Version {#h1204}

RSS version is not 2.0.

**Severity**: Warning

**How to Fix**
1. Use RSS 2.0 for maximum compatibility
2. Check RSS generation template

---

### H1205: Missing RSS Channel {#h1205}

RSS feed has no `<channel>` element.

**Severity**: Error

**How to Fix**
1. This is a Bengal bug - report it
2. RSS 2.0 requires a `<channel>` element

---

### H1206: Missing Required Channel Elements {#h1206}

RSS channel missing required elements (title, link, description).

**Severity**: Error

**How to Fix**
1. Configure site title and description
2. Set `baseurl` in configuration

---

### H1207: Empty RSS Feed {#h1207}

RSS feed has no items.

**Severity**: Warning

**Common Causes**
- No dated content
- RSS generation issue

**How to Fix**
1. Add dated content with `date` in frontmatter
2. Review RSS generation logic

---

### H1208: Invalid RSS Items {#h1208}

RSS items missing required elements (title, link).

**Severity**: Error

**How to Fix**
1. Ensure content has titles
2. Check RSS item generation

---

### H1209: Relative RSS Channel Link {#h1209}

RSS channel link is relative, not absolute.

**Severity**: Warning

**How to Fix**
1. Set `baseurl` in configuration
2. Verify RSS uses absolute URLs

---

### H1210: Relative RSS Item URLs {#h1210}

RSS item links are relative instead of absolute.

**Severity**: Error

**How to Fix**
1. Set `baseurl` in configuration
2. Verify RSS item generation uses absolute URLs

---

## Font Checks (H13xx) {#fonts}

### H1301: Missing fonts.css {#h1301}

fonts.css not generated despite font configuration.

**Severity**: Warning

**Common Causes**
- `FontHelper.process()` not called
- Font processing failed

**How to Fix**
1. Check font configuration
2. Review build logs for font errors

---

### H1302: Missing Fonts Directory {#h1302}

Fonts directory does not exist in output.

**Severity**: Error

**Common Causes**
- Font files not downloaded
- Font processing failed

**How to Fix**
1. Check font configuration
2. Verify network connectivity
3. Review font processing logs

---

### H1303: No Font Files {#h1303}

No font files found in assets/fonts/.

**Severity**: Error

**Common Causes**
- Font download failed
- Network connectivity issues

**How to Fix**
1. Check network connectivity
2. Review font download logs
3. Try manual font installation

---

### H1304: Insufficient Font Files {#h1304}

Fewer font files than expected for configured families.

**Severity**: Warning

**Common Causes**
- Some fonts failed to download
- Font family configuration issue

**How to Fix**
1. Check for download errors in logs
2. Verify font family names

---

### H1305: Cannot Read fonts.css {#h1305}

fonts.css file cannot be read.

**Severity**: Error

**Common Causes**
- File permissions issue
- Encoding problem

**How to Fix**
1. Check file permissions
2. Regenerate fonts.css

---

### H1306: No @font-face Rules {#h1306}

fonts.css has no @font-face declarations.

**Severity**: Error

**Common Causes**
- FontCSSGenerator issue
- Empty font configuration

**How to Fix**
1. Check font configuration
2. Verify FontCSSGenerator is working

---

### H1307: Broken Font References {#h1307}

CSS references font files that don't exist.

**Severity**: Error

**Common Causes**
- Font download failed
- Path mismatch

**How to Fix**
1. Check font files exist
2. Regenerate fonts.css

---

### H1308: Oversized Font Files {#h1308}

Font files are very large (>200 KB).

**Severity**: Warning

**Common Causes**
- Using full font families
- Non-subset fonts

**How to Fix**
1. Use variable fonts
2. Subset fonts to needed characters
3. Use fewer font weights

---

### H1309: Large Total Font Size {#h1309}

Total font size exceeds 1 MB.

**Severity**: Warning

**How to Fix**
1. Reduce number of font weights
2. Use font subsetting
3. Consider system fonts

---

## Asset Checks (H14xx) {#assets}

### H1401: Missing Assets Directory {#h1401}

No assets directory found in output.

**Severity**: Warning

**Common Causes**
- Assets not copied
- Asset discovery failed

**How to Fix**
1. Check asset configuration
2. Verify source assets exist

---

### H1402: No CSS Files in Assets {#h1402}

No CSS files found in assets directory.

**Severity**: Warning

**Common Causes**
- Theme CSS not discovered
- CSS not copied

**How to Fix**
1. Check theme has CSS files
2. Review asset discovery settings

---

### H1403: Large CSS Files {#h1403}

CSS files exceed size threshold.

**Severity**: Warning

**How to Fix**
1. Enable CSS minification
2. Split large CSS files
3. Remove unused styles

---

### H1404: Large JavaScript Files {#h1404}

JavaScript files exceed size threshold.

**Severity**: Warning

**How to Fix**
1. Enable JS minification
2. Use code splitting
3. Remove unused code

---

### H1405: Large Image Files {#h1405}

Image files exceed size threshold.

**Severity**: Warning

**How to Fix**
1. Optimize images
2. Use appropriate formats (WebP, AVIF)
3. Resize to needed dimensions

---

### H1406: Large Total Asset Size {#h1406}

Total asset size exceeds 10 MB.

**Severity**: Warning

**How to Fix**
1. Optimize all assets
2. Remove unused assets
3. Use CDN for large files

---

### H1407: Unminified CSS {#h1407}

Large CSS files may not be minified.

**Severity**: Info

**How to Fix**
1. Enable CSS minification in config
2. Use build-time CSS processing

---

### H1408: Unminified JavaScript {#h1408}

Large JS files may not be minified.

**Severity**: Info

**How to Fix**
1. Enable JS minification in config
2. Use build-time JS processing

---

## Connectivity Checks (H15xx) {#connectivity}

### H1501: Many Isolated Pages {#h1501}

Many pages have no meaningful connections.

**Severity**: Error

**Common Causes**
- Missing internal links
- No tags or categories
- Orphaned content

**How to Fix**
1. Add internal links between related pages
2. Use tags to group related content
3. Add cross-references

---

### H1502: Isolated Pages Found {#h1502}

Some pages are isolated (low connectivity score).

**Severity**: Warning

**How to Fix**
1. Add navigation or cross-references
2. Link from related pages

---

### H1503: Lightly-Linked Pages {#h1503}

Pages rely only on structural links.

**Severity**: Warning

**Common Causes**
- Only connected via navigation
- No explicit cross-references

**How to Fix**
1. Add explicit cross-references
2. Link from related content

---

### H1504: Hub Pages Detected {#h1504}

Pages have very many outgoing references.

**Severity**: Warning

**How to Fix**
1. Consider splitting into sub-topics
2. Create multiple entry points

---

### H1505: Low Average Connectivity Score {#h1505}

Site-wide connectivity is low.

**Severity**: Warning

**How to Fix**
1. Add more internal links
2. Use tags and cross-references
3. Aim for average score >= 1.0

---

### H1506: Low Average Connectivity Links {#h1506}

Average links per page is very low.

**Severity**: Warning

**How to Fix**
1. Add more internal links
2. Use cross-reference patterns
3. Well-connected content improves SEO

---

## Config Checks (H16xx) {#config}

### H1601: Missing Configuration Fields {#h1601}

Recommended configuration fields are missing.

**Severity**: Warning

**How to Fix**
1. Add suggested fields to `bengal.toml`
2. Review configuration documentation

---

### H1602: Trailing Slash in Base URL {#h1602}

Base URL ends with `/`.

**Severity**: Info

**Common Causes**
- Copy/paste error
- Intentional but may cause issues

**How to Fix**
1. Remove trailing slash from `baseurl`
2. `baseurl = "https://example.com"` not `"https://example.com/"`

---

### H1603: Very High max_workers {#h1603}

`max_workers` is set very high (>20).

**Severity**: Warning

**Common Causes**
- Over-optimization attempt
- Copy/paste error

**How to Fix**
1. Reduce to 8-12 workers
2. Very high values may cause resource exhaustion

---

### H1604: Incremental Without Parallel {#h1604}

Incremental builds enabled but parallel disabled.

**Severity**: Info

**How to Fix**
1. Enable `parallel = true` for faster incremental builds
2. Or this may be intentional for debugging

---

## Rendering Checks (H17xx) {#rendering}

### H1701: HTML Structure Issues {#h1701}

Pages have HTML structure problems.

**Severity**: Warning

**Common Causes**
- Template missing DOCTYPE
- Missing `<html>`, `<head>`, or `<body>` tags

**How to Fix**
1. Check template files for proper HTML5 structure
2. Verify base template is complete

---

### H1702: Unrendered Jinja2 Syntax {#h1702}

Pages may have unrendered template syntax.

**Severity**: Warning

**Common Causes**
- Template escaping issues
- Documentation examples (which is OK)

**How to Fix**
1. Check for template rendering errors
2. If documenting Jinja2, escape properly

---

### H1703: Missing Template Functions {#h1703}

Essential template functions not registered.

**Severity**: Error

**Common Causes**
- TemplateEngine initialization issue
- Function registration failed

**How to Fix**
1. This is a Bengal bug - report it
2. Check TemplateEngine.__init__()

---

### H1704: Template Function Validation Failed {#h1704}

Could not validate template functions.

**Severity**: Warning

**Common Causes**
- TemplateEngine initialization problem

**How to Fix**
1. Check for initialization errors
2. Report if persistent

---

### H1705: Missing SEO Metadata {#h1705}

Pages missing basic SEO elements.

**Severity**: Warning

**Common Causes**
- Template missing `<title>` or meta description
- Frontmatter missing description

**How to Fix**
1. Add `<title>` to templates
2. Add meta description tags
3. Set `description` in frontmatter

---

## Track Checks (H18xx) {#tracks}

### H1801: Invalid Track Structure {#h1801}

Track configuration is not a dictionary.

**Severity**: Error

**How to Fix**
1. Fix track definition in `tracks.yaml`
2. Use dict with `title` and `items` fields

---

### H1802: Track Missing items Field {#h1802}

Track missing required `items` field.

**Severity**: Error

**How to Fix**
1. Add `items` list to track definition
2. Include page paths in items

---

### H1803: Track items Not a List {#h1803}

Track `items` field is not a list.

**Severity**: Error

**How to Fix**
1. Use list syntax for items: `items: [page1.md, page2.md]`

---

### H1804: Invalid Track Item Type {#h1804}

Track item is not a string.

**Severity**: Warning

**How to Fix**
1. Use string page paths for track items
2. Example: `items: ["guide/intro.md", "guide/basics.md"]`

---

### H1805: Missing Track Pages {#h1805}

Track references pages that don't exist.

**Severity**: Warning

**How to Fix**
1. Check page paths in `tracks.yaml`
2. Create missing pages or remove references

---

### H1806: Invalid track_id in Page {#h1806}

Page references a track that doesn't exist.

**Severity**: Warning

**How to Fix**
1. Add the track to `tracks.yaml`
2. Or remove `track_id` from page frontmatter

---

## Anchor Checks (H19xx) {#anchors}

### H1901: Duplicate Anchor IDs {#h1901}

Page has duplicate anchor IDs.

**Severity**: Error (strict) / Warning (default)

**Common Causes**
- Duplicate headings
- Conflicting explicit anchor IDs

**How to Fix**
1. Rename one of the duplicates
2. Use unique anchor IDs

---

### H1902: Broken Anchor References {#h1902}

Anchor references point to non-existent anchors.

**Severity**: Warning

**Common Causes**
- Typo in anchor reference
- Target heading was renamed/deleted

**How to Fix**
1. Fix the anchor reference
2. Add explicit anchor with `{#id}` syntax
3. Check similar anchors suggested in error

---

## Ownership Checks (H20xx) {#ownership}

### H2001: Reserved Namespace Violations {#h2001}

User content placed in reserved namespaces.

**Severity**: Warning

**Reserved Namespaces**
- `/tags/` - reserved for taxonomy
- `/search/`, `/404.html`, `/graph/` - reserved for special pages
- Autodoc prefixes - reserved for autodoc output

**How to Fix**
1. Move content to a different path
2. Adjust the slug in frontmatter
3. Use a custom section instead

---

## Using --ignore

To suppress specific health checks, use the `--ignore` flag:

```bash
# Ignore a single code
bengal validate --ignore H202

# Ignore multiple codes
bengal validate --ignore H202 --ignore H1403 --ignore H1404

# Combine with other options
bengal validate --verbose --ignore H301
```

Common ignore patterns:

```bash
# Ignore external link checks (for offline development)
bengal validate --ignore H202

# Ignore performance warnings during development
bengal validate --ignore H1001 --ignore H1002 --ignore H1003

# Ignore asset size warnings for documentation sites
bengal validate --ignore H1403 --ignore H1404 --ignore H1405
```

---

## Getting Help

If you encounter a health check issue:

1. Check this page for the code (Ctrl+F / Cmd+F)
2. Review the suggested fix
3. Run with `--verbose` for more details
4. Check the [troubleshooting guide](/docs/building/troubleshooting/)

For bugs or unclear errors, please [open an issue](https://github.com/lbliii/bengal/issues).
