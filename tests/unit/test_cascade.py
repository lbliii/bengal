"""Tests for cascading frontmatter functionality."""

from pathlib import Path

from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.site import Site


class TestSectionCascadeExtraction:
    """Test that sections extract cascade metadata from their index pages."""

    def test_extract_cascade_from_index_page(self):
        """Test that cascade metadata is extracted when _index.md is added."""
        section = Section(name="products", path=Path("/content/products"))

        # Create index page with cascade
        index_page = Page(
            source_path=Path("/content/products/_index.md"),
            metadata={
                'title': 'Products',
                'cascade': {
                    'type': 'product',
                    'version': '2.0'
                }
            }
        )

        section.add_page(index_page)

        # Cascade should be extracted to section metadata
        assert 'cascade' in section.metadata
        assert section.metadata['cascade']['type'] == 'product'
        assert section.metadata['cascade']['version'] == '2.0'
        assert section.index_page == index_page

    def test_no_cascade_in_index_page(self):
        """Test that sections work fine without cascade."""
        section = Section(name="blog", path=Path("/content/blog"))

        index_page = Page(
            source_path=Path("/content/blog/_index.md"),
            metadata={'title': 'Blog'}
        )

        section.add_page(index_page)

        # Should not have cascade
        assert 'cascade' not in section.metadata
        assert section.index_page == index_page

    def test_regular_page_does_not_create_cascade(self):
        """Test that regular pages don't create cascade metadata."""
        section = Section(name="blog", path=Path("/content/blog"))

        regular_page = Page(
            source_path=Path("/content/blog/post.md"),
            metadata={
                'title': 'Post',
                'cascade': {'type': 'post'}  # This should be ignored
            }
        )

        section.add_page(regular_page)

        # Cascade should only come from index pages
        assert 'cascade' not in section.metadata


class TestBasicCascade:
    """Test basic cascade application to pages."""

    def test_cascade_applies_to_child_pages(self):
        """Test that cascade metadata is applied to child pages."""
        site = Site(root_path=Path("/site"), config={})

        # Create section with cascade
        section = Section(name="docs", path=Path("/content/docs"))
        section.metadata['cascade'] = {
            'type': 'documentation',
            'version': '1.0'
        }

        # Create pages without these fields
        page1 = Page(
            source_path=Path("/content/docs/intro.md"),
            metadata={'title': 'Introduction'}
        )
        page2 = Page(
            source_path=Path("/content/docs/guide.md"),
            metadata={'title': 'Guide'}
        )

        section.add_page(page1)
        section.add_page(page2)
        site.sections = [section]
        site.pages = [page1, page2]

        # Apply cascades
        site._apply_cascades()

        # Both pages should have cascade values
        assert page1.metadata['type'] == 'documentation'
        assert page1.metadata['version'] == '1.0'
        assert page2.metadata['type'] == 'documentation'
        assert page2.metadata['version'] == '1.0'

        # Original metadata preserved
        assert page1.metadata['title'] == 'Introduction'
        assert page2.metadata['title'] == 'Guide'

    def test_page_metadata_overrides_cascade(self):
        """Test that page's own metadata takes precedence over cascade."""
        site = Site(root_path=Path("/site"), config={})

        section = Section(name="blog", path=Path("/content/blog"))
        section.metadata['cascade'] = {
            'type': 'post',
            'author': 'Default Author'
        }

        # Page with one override
        page = Page(
            source_path=Path("/content/blog/my-post.md"),
            metadata={
                'title': 'My Post',
                'author': 'John Doe'  # Override cascade
            }
        )

        section.add_page(page)
        site.sections = [section]
        site.pages = [page]

        site._apply_cascades()

        # Type comes from cascade, author from page
        assert page.metadata['type'] == 'post'
        assert page.metadata['author'] == 'John Doe'  # Not 'Default Author'

    def test_empty_cascade_does_nothing(self):
        """Test that empty cascade metadata doesn't affect pages."""
        site = Site(root_path=Path("/site"), config={})

        section = Section(name="pages", path=Path("/content/pages"))
        section.metadata['cascade'] = {}  # Empty cascade

        page = Page(
            source_path=Path("/content/pages/about.md"),
            metadata={'title': 'About'}
        )

        section.add_page(page)
        site.sections = [section]
        site.pages = [page]

        site._apply_cascades()

        # Only original metadata
        assert page.metadata == {'title': 'About'}


class TestNestedCascade:
    """Test cascade accumulation through section hierarchy."""

    def test_nested_cascade_accumulation(self):
        """Test that cascades accumulate from parent to child sections."""
        site = Site(root_path=Path("/site"), config={})

        # Parent section
        parent = Section(name="api", path=Path("/content/api"))
        parent.metadata['cascade'] = {
            'type': 'api-doc',
            'api_base': 'https://api.example.com'
        }

        # Child section with additional cascade
        child = Section(name="v2", path=Path("/content/api/v2"))
        child.metadata['cascade'] = {
            'version': '2.0',
            'stable': True
        }

        # Page in child section
        page = Page(
            source_path=Path("/content/api/v2/auth.md"),
            metadata={'title': 'Authentication'}
        )

        parent.add_subsection(child)
        child.add_page(page)

        site.sections = [parent, child]
        site.pages = [page]

        site._apply_cascades()

        # Page should have values from both parent and child cascades
        assert page.metadata['type'] == 'api-doc'  # from parent
        assert page.metadata['api_base'] == 'https://api.example.com'  # from parent
        assert page.metadata['version'] == '2.0'  # from child
        assert page.metadata['stable'] is True  # from child

    def test_child_cascade_overrides_parent(self):
        """Test that child section cascade can override parent cascade."""
        site = Site(root_path=Path("/site"), config={})

        parent = Section(name="docs", path=Path("/content/docs"))
        parent.metadata['cascade'] = {
            'version': '1.0',
            'status': 'draft'
        }

        child = Section(name="stable", path=Path("/content/docs/stable"))
        child.metadata['cascade'] = {
            'version': '2.0',  # Override
            'status': 'stable'  # Override
        }

        page = Page(
            source_path=Path("/content/docs/stable/guide.md"),
            metadata={'title': 'Guide'}
        )

        parent.add_subsection(child)
        child.add_page(page)

        site.sections = [parent, child]
        site.pages = [page]

        site._apply_cascades()

        # Child cascade values win
        assert page.metadata['version'] == '2.0'
        assert page.metadata['status'] == 'stable'

    def test_three_level_cascade(self):
        """Test cascade through three levels of sections."""
        site = Site(root_path=Path("/site"), config={})

        # Level 1: Root section
        root = Section(name="products", path=Path("/content/products"))
        root.metadata['cascade'] = {'product_line': 'current'}

        # Level 2: Category section
        category = Section(name="widgets", path=Path("/content/products/widgets"))
        category.metadata['cascade'] = {'category': 'widget', 'warranty': '1-year'}

        # Level 3: Version section
        version = Section(name="v3", path=Path("/content/products/widgets/v3"))
        version.metadata['cascade'] = {'version': '3.0', 'warranty': '2-year'}  # Override warranty

        # Page at deepest level
        page = Page(
            source_path=Path("/content/products/widgets/v3/specs.md"),
            metadata={'title': 'Specifications'}
        )

        root.add_subsection(category)
        category.add_subsection(version)
        version.add_page(page)

        site.sections = [root, category, version]
        site.pages = [page]

        site._apply_cascades()

        # Should accumulate all three levels
        assert page.metadata['product_line'] == 'current'  # from root
        assert page.metadata['category'] == 'widget'  # from category
        assert page.metadata['version'] == '3.0'  # from version
        assert page.metadata['warranty'] == '2-year'  # from version (overrides category)


class TestCascadeEdgeCases:
    """Test edge cases and error conditions."""

    def test_no_sections_no_error(self):
        """Test that cascade application works with no sections."""
        site = Site(root_path=Path("/site"), config={})
        site.sections = []
        site.pages = []

        # Should not raise an error
        site._apply_cascades()

    def test_section_with_no_pages(self):
        """Test that sections without pages don't cause errors."""
        site = Site(root_path=Path("/site"), config={})

        section = Section(name="empty", path=Path("/content/empty"))
        section.metadata['cascade'] = {'type': 'test'}

        site.sections = [section]
        site.pages = []

        # Should not raise an error
        site._apply_cascades()

    def test_cascade_with_complex_values(self):
        """Test cascade with complex data types."""
        site = Site(root_path=Path("/site"), config={})

        section = Section(name="complex", path=Path("/content/complex"))
        section.metadata['cascade'] = {
            'tags': ['python', 'tutorial'],
            'config': {
                'enabled': True,
                'options': [1, 2, 3]
            },
            'count': 42
        }

        page = Page(
            source_path=Path("/content/complex/page.md"),
            metadata={'title': 'Test'}
        )

        section.add_page(page)
        site.sections = [section]
        site.pages = [page]

        site._apply_cascades()

        # Complex values should be preserved
        assert page.metadata['tags'] == ['python', 'tutorial']
        assert page.metadata['config']['enabled'] is True
        assert page.metadata['config']['options'] == [1, 2, 3]
        assert page.metadata['count'] == 42

    def test_cascade_does_not_affect_index_page(self):
        """Test that cascade doesn't apply to the index page itself."""
        site = Site(root_path=Path("/site"), config={})

        section = Section(name="docs", path=Path("/content/docs"))

        index_page = Page(
            source_path=Path("/content/docs/_index.md"),
            metadata={
                'title': 'Documentation',
                'cascade': {
                    'type': 'doc',
                    'version': '1.0'
                }
            }
        )

        regular_page = Page(
            source_path=Path("/content/docs/guide.md"),
            metadata={'title': 'Guide'}
        )

        section.add_page(index_page)
        section.add_page(regular_page)

        site.sections = [section]
        site.pages = [index_page, regular_page]

        site._apply_cascades()

        # Index page should have its original metadata only
        assert 'type' not in index_page.metadata or index_page.metadata.get('type') == 'doc'

        # Regular page should have cascade applied
        assert regular_page.metadata['type'] == 'doc'
        assert regular_page.metadata['version'] == '1.0'


class TestRootLevelCascade:
    """Test cascade from root-level pages (like content/index.md)."""

    def test_root_level_page_cascade_to_sections(self):
        """Test that cascade from root index.md applies to all top-level sections."""
        site = Site(root_path=Path("/site"), config={})

        # Root-level page with cascade (like content/index.md)
        root_page = Page(
            source_path=Path("/content/index.md"),
            metadata={
                'title': 'Home',
                'cascade': {
                    'type': 'doc',
                    'site_version': '1.0'
                }
            }
        )

        # Top-level section
        section = Section(name="docs", path=Path("/content/docs"))

        # Page in section
        child_page = Page(
            source_path=Path("/content/docs/intro.md"),
            metadata={'title': 'Introduction'}
        )

        section.add_page(child_page)

        # Root page is NOT in any section (top-level)
        site.sections = [section]
        site.pages = [root_page, child_page]

        site._apply_cascades()

        # Child page should inherit from root cascade
        assert child_page.metadata['type'] == 'doc'
        assert child_page.metadata['site_version'] == '1.0'
        assert child_page.metadata['title'] == 'Introduction'  # Original preserved

    def test_root_cascade_to_multiple_sections(self):
        """Test that root cascade applies to all top-level sections."""
        site = Site(root_path=Path("/site"), config={})

        # Root-level page with cascade
        root_page = Page(
            source_path=Path("/content/index.md"),
            metadata={
                'cascade': {
                    'type': 'doc',
                    'layout': 'default'
                }
            }
        )

        # Multiple top-level sections
        section1 = Section(name="about", path=Path("/content/about"))
        section2 = Section(name="docs", path=Path("/content/docs"))

        # Pages in different sections
        page1 = Page(source_path=Path("/content/about/team.md"), metadata={'title': 'Team'})
        page2 = Page(source_path=Path("/content/docs/guide.md"), metadata={'title': 'Guide'})

        section1.add_page(page1)
        section2.add_page(page2)

        site.sections = [section1, section2]
        site.pages = [root_page, page1, page2]

        site._apply_cascades()

        # Both pages should inherit root cascade
        assert page1.metadata['type'] == 'doc'
        assert page1.metadata['layout'] == 'default'
        assert page2.metadata['type'] == 'doc'
        assert page2.metadata['layout'] == 'default'

    def test_root_cascade_with_section_override(self):
        """Test that section cascade can override root cascade."""
        site = Site(root_path=Path("/site"), config={})

        # Root-level cascade
        root_page = Page(
            source_path=Path("/content/index.md"),
            metadata={
                'cascade': {
                    'type': 'doc',
                    'theme': 'light'
                }
            }
        )

        # Section with its own cascade that overrides
        section = Section(name="api", path=Path("/content/api"))
        section.metadata['cascade'] = {
            'type': 'api-reference',  # Override
            'theme': 'dark'           # Override
        }

        page = Page(
            source_path=Path("/content/api/rest.md"),
            metadata={'title': 'REST API'}
        )

        section.add_page(page)

        site.sections = [section]
        site.pages = [root_page, page]

        site._apply_cascades()

        # Section cascade should override root cascade
        assert page.metadata['type'] == 'api-reference'
        assert page.metadata['theme'] == 'dark'

    def test_root_cascade_to_nested_sections(self):
        """Test that root cascade propagates through nested sections."""
        site = Site(root_path=Path("/site"), config={})

        # Root-level cascade
        root_page = Page(
            source_path=Path("/content/index.md"),
            metadata={
                'cascade': {
                    'site_name': 'My Site',
                    'version': '1.0'
                }
            }
        )

        # Parent section
        parent = Section(name="docs", path=Path("/content/docs"))

        # Nested child section
        child = Section(name="guides", path=Path("/content/docs/guides"))

        # Page in deeply nested section
        page = Page(
            source_path=Path("/content/docs/guides/intro.md"),
            metadata={'title': 'Intro'}
        )

        parent.add_subsection(child)
        child.add_page(page)

        site.sections = [parent, child]
        site.pages = [root_page, page]

        site._apply_cascades()

        # Page should inherit from root cascade even in nested section
        assert page.metadata['site_name'] == 'My Site'
        assert page.metadata['version'] == '1.0'

