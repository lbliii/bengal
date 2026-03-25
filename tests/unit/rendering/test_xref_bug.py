"""
Tests for cross-reference bug fixes.

Verifies that cross-references are NOT substituted inside code blocks,
and that [[ext:project:|Text]] works correctly inside markdown tables.
"""

import pytest

from bengal.rendering.plugins.cross_references import CrossReferencePlugin
from tests._testing.mocks import MockPage


class TestCrossReferenceBug:
    def test_xref_in_code_block_is_ignored(self, parser):
        """
        Test that cross-references [[...]] inside code blocks are NOT substituted.
        Current suspected behavior: They are substituted because the plugin regex runs on raw HTML.
        """
        # Create mock page and xref index
        mock_page = MockPage(
            title="Test Page",
            href="/test-url/",
            slug="test-page",
        )

        xref_index = {
            "by_path": {"doc/link": mock_page},
            "by_slug": {},
            "by_id": {},
            "by_heading": {},
        }

        parser.enable_cross_references(xref_index)

        # Markdown with a code block containing a cross-reference
        content = """
Here is a reference: [[doc/link]]

And here is code:
```
var x = [[doc/link]];
```
"""

        result = parser.parse_with_toc(content, {})
        html = result[0]

        # The text reference SHOULD be linked
        assert '<a href="/test-url/">Test Page</a>' in html

        # The code block reference SHOULD NOT be linked
        # Expected: <pre><code>var x = [[doc/link]];\n</code></pre>
        # If bug exists: <pre><code>var x = <a href="/test-url/">Test Page</a>;\n</code></pre>

        # Extract the code block content to check
        code_block_start = html.find("<pre>")
        code_block_end = html.find("</pre>")
        code_html = html[code_block_start:code_block_end]

        if '<a href="' in code_html:
            pytest.fail(f"Cross-reference was substituted inside code block: {code_html}")

        assert "[[doc/link]]" in code_html


class TestProtectTablePipes:
    """Tests for protect_table_pipes / restore_table_pipes.

    Cross-references like [[ext:kida:|Kida]] use | as the ref/text separator,
    which conflicts with markdown table cell delimiters. The protect/restore
    methods substitute pipes inside [[...]] before the parser splits table rows.
    """

    def test_protects_pipe_inside_brackets(self):
        """Pipe inside [[...]] is replaced with placeholder."""
        source = "| col | [[ext:kida:|Kida]] |"
        protected = CrossReferencePlugin.protect_table_pipes(source)

        assert "|Kida" not in protected
        assert CrossReferencePlugin._PIPE_PLACEHOLDER + "Kida" in protected

    def test_roundtrip(self):
        """protect then restore returns original text."""
        source = "| **Templates** | [[ext:kida:|Kida]] (fast) |"
        protected = CrossReferencePlugin.protect_table_pipes(source)
        restored = CrossReferencePlugin.restore_table_pipes(protected)

        assert restored == source

    def test_multiple_xrefs_in_one_line(self):
        """Multiple [[...]] patterns on one line are all protected."""
        source = "| **FT** | [[ext:kida:|Kida]], [[ext:patitas:|Patitas]] |"
        protected = CrossReferencePlugin.protect_table_pipes(source)

        assert "|Kida" not in protected
        assert "|Patitas" not in protected
        assert CrossReferencePlugin.restore_table_pipes(protected) == source

    def test_no_op_without_brackets(self):
        """Source without [[ is returned unchanged."""
        source = "| col1 | col2 |"
        assert CrossReferencePlugin.protect_table_pipes(source) == source

    def test_no_op_without_pipe(self):
        """Source without | is returned unchanged."""
        source = "[[ext:kida:Markup]] some text"
        assert CrossReferencePlugin.protect_table_pipes(source) == source

    def test_brackets_without_pipe_unchanged(self):
        """[[...]] that don't contain | are not modified."""
        source = "| col | [[docs/guide]] |"
        assert CrossReferencePlugin.protect_table_pipes(source) == source

    def test_nested_pipes_all_replaced(self):
        """Multiple pipes inside one [[...]] are all replaced."""
        source = "[[a|b|c]]"
        protected = CrossReferencePlugin.protect_table_pipes(source)

        assert "|" not in protected.replace(CrossReferencePlugin._PIPE_PLACEHOLDER, "")
        assert CrossReferencePlugin.restore_table_pipes(protected) == source
