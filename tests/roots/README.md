# Bengal Test Roots

Minimal, reusable site structures for testing.

**Note**: Some roots now use skeleton manifests (`skeleton.yaml`) for declarative structure definition. The `site_factory` fixture automatically uses skeleton manifests when available, falling back to directory copying for backward compatibility.

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

### test-directives
**Purpose**: Tests directive parsing and rendering  
**Structure**: 4+ pages with cards, admonitions, and nested content  
**Use for**: Card directives, admonitions, glossary, cross-references, child-cards

```python
@pytest.mark.bengal(testroot="test-directives")
def test_card_directive(site, build_site):
    build_site()
    html = (site.output_dir / "cards/index.html").read_text()
    assert "card-grid" in html
```

**Structure**:
- `_index.md` → Home with child-cards directive
- `cards.md` → Card grid examples
- `admonitions.md` → Note, warning, tip, important directives
- `sections/_index.md` → Section index
- `sections/page.md` → Nested page with cross-references
- `data/glossary.yaml` → Glossary terms

### test-navigation
**Purpose**: Tests navigation hierarchies and menu building  
**Structure**: Multi-level hierarchy (3 levels deep)  
**Use for**: Menu building, breadcrumbs, section navigation

```python
@pytest.mark.bengal(testroot="test-navigation")
def test_breadcrumbs(site, build_site):
    build_site()
    html = (site.output_dir / "docs/getting-started/quickstart/index.html").read_text()
    # Should have breadcrumb: Home > Docs > Getting Started > Quickstart
    assert "breadcrumb" in html.lower() or "nav" in html.lower()
```

**Structure**:
- `_index.md` → Home
- `docs/_index.md` → Docs section
- `docs/getting-started/_index.md` → Getting Started subsection
- `docs/getting-started/quickstart.md` → Deeply nested page
- `docs/reference/_index.md` → Reference subsection
- `docs/reference/api.md` → Reference page
- `blog/_index.md` → Flat blog section

### test-large
**Purpose**: Performance testing with 100+ pages  
**Structure**: 100+ generated pages in 5 sections  
**Use for**: Performance benchmarks, parallel rendering, memory usage

```python
@pytest.mark.bengal(testroot="test-large")
@pytest.mark.slow
def test_parallel_build_performance(site, build_site, benchmark):
    result = benchmark(lambda: build_site(parallel=True))
    assert result < 5.0  # Should complete in <5 seconds
```

**Generation**: Run `python tests/roots/test-large/generate.py` to (re)generate content.

**Structure**:
- `_index.md` → Home
- `docs/`, `guides/`, `tutorials/`, `reference/`, `api/` → 5 sections
- 20 pages per section → 100 total pages with cross-links

---

## Maintenance

- Keep roots minimal (resist adding more files)
- Periodically audit: Are roots still necessary?
- Consolidate when possible
- Remove deprecated roots after migration

### test-cascade
**Purpose**: Tests cascading frontmatter through nested sections  
**Structure**: Nested products/widgets/ hierarchy with _index.md cascade files  
**Use for**: Cascade behavior, metadata inheritance, nested sections, overrides

```python
@pytest.mark.bengal(testroot="test-cascade")
def test_cascade_inheritance(site):
    site.discover_content()
    widget = next(p for p in site.pages if "super-widget" in str(p.source_path))
    # Inherits from both products/ and widgets/ cascades
    assert widget.metadata["type"] == "product"
    assert widget.metadata["category"] == "widget"
```

**Structure**:
- `products/_index.md` → cascade: type, show_price, product_line
- `products/widgets/_index.md` → cascade: category, warranty
- `products/widgets/super-widget.md` → inherits all
- `products/widgets/custom-widget.md` → inherits but overrides type
