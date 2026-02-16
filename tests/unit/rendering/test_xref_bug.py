"""
Tests for cross-reference bug fixes.

Verifies that cross-references are NOT substituted inside code blocks.
"""

import pytest

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
