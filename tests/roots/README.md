# Bengal Test Roots

Minimal, reusable site structures for testing.

## Available Roots

### test-basic
**Purpose**: Minimal smoke test site  
**Structure**: 1 page (index.md), default config  
**Use for**: Basic build tests, simple assertions, quick validation

```python
@pytest.mark.bengal(testroot="test-basic")
def test_basic_build(site, build_site):
    build_site()
    assert len(site.pages) == 1
```

### test-baseurl
**Purpose**: Tests baseurl handling  
**Structure**: 2 pages (index.md, about.md), baseurl="/site"  
**Use for**: URL generation, link tests, baseurl overrides

```python
@pytest.mark.bengal(testroot="test-baseurl")
def test_baseurl_paths(site, build_site):
    build_site()
    html = (site.output_dir / "index.html").read_text()
    assert 'href="/site/assets/' in html
```

### test-taxonomy
**Purpose**: Tests taxonomy/tagging  
**Structure**: 3 pages with tags (python, testing)  
**Use for**: Tag generation, taxonomy pages, filtering

```python
@pytest.mark.bengal(testroot="test-taxonomy")
def test_tag_pages(site, build_site):
    build_site()
    assert (site.output_dir / "tags/python/index.html").exists()
```

### test-templates
**Purpose**: Documentation with template examples  
**Structure**: 1 page with {{/* */}} template syntax  
**Use for**: Template escaping, documentation builds

```python
@pytest.mark.bengal(testroot="test-templates")
def test_template_escaping(site, build_site):
    build_site()
    html = (site.output_dir / "guide/index.html").read_text()
    # Template examples should be escaped
    assert "&#123;&#123;" in html  # {{ escaped
```

### test-assets
**Purpose**: Tests custom assets  
**Structure**: 1 page + custom assets/images/  
**Use for**: Asset discovery, asset copying, asset references

```python
@pytest.mark.bengal(testroot="test-assets")
def test_asset_copying(site, build_site):
    build_site()
    assert (site.output_dir / "assets/images/test.png").exists()
```

## Design Principles

1. **Minimal**: Each root has ≤5 files (keep focused)
2. **Single-purpose**: One root, one scenario
3. **Composable**: Use confoverrides for variations
4. **Fast**: Small sites build quickly
5. **Maintainable**: Well-documented purpose

## Adding New Roots

When adding a new test root:

1. Create directory: `tests/roots/test-<scenario>/`
2. Add minimal `bengal.toml` with clear defaults
3. Add just enough content to test the scenario
4. Document in this README
5. Use descriptive names: `test-<feature>` or `test-<bug-id>`

## Common Patterns

### Override Config
```python
@pytest.mark.bengal(
    testroot="test-basic",
    confoverrides={"site.title": "Custom Title"}
)
def test_custom_title(site):
    assert site.config["site"]["title"] == "Custom Title"
```

### Multiple Pages from Same Root
```python
@pytest.mark.parametrize("baseurl", ["/", "/site", "https://example.com"])
@pytest.mark.bengal(testroot="test-basic")
def test_various_baseurls(site, baseurl):
    # confoverrides can be applied via fixture params if needed
    pass
```

### Build Variations
```python
@pytest.mark.bengal(testroot="test-basic")
def test_incremental_build(site, build_site):
    build_site()  # Full build
    # Modify content
    build_site(incremental=True)  # Incremental
```

## Maintenance

- Keep roots minimal (resist adding more files)
- Periodically audit: Are roots still necessary?
- Consolidate when possible
- Remove deprecated roots after migration
