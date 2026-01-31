"""Unit tests for bengal.postprocess.utils.xml module."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from bengal.postprocess.utils.xml import indent_xml


class TestIndentXml:
    """Test XML indentation utility."""

    def test_adds_whitespace_to_nested_elements(self) -> None:
        """Test that indent_xml adds proper whitespace to nested elements."""
        root = ET.Element("root")
        child = ET.SubElement(root, "child")
        child.text = "content"

        indent_xml(root)

        # Check that whitespace was added
        assert root.text is not None
        assert "\n" in root.text
        assert child.tail is not None
        assert "\n" in child.tail

    def test_indentation_increases_with_depth(self) -> None:
        """Test that deeper elements have more indentation."""
        root = ET.Element("root")
        level1 = ET.SubElement(root, "level1")
        level2 = ET.SubElement(level1, "level2")
        level2.text = "deep"

        indent_xml(root)

        # root.text contains indent for level1 (2 spaces)
        assert root.text is not None
        assert "  " in root.text
        # level1.text contains indent for level2 (4 spaces)
        assert level1.text is not None
        assert "    " in level1.text

    def test_preserves_existing_text_content(self) -> None:
        """Test that existing text content is preserved."""
        root = ET.Element("root")
        child = ET.SubElement(root, "child")
        child.text = "Hello World"

        indent_xml(root)

        assert child.text == "Hello World"

    def test_handles_empty_element(self) -> None:
        """Test handling of element with no children."""
        root = ET.Element("empty")

        indent_xml(root)

        # Single element should not have internal whitespace
        assert root.text is None or root.text.strip() == ""

    def test_handles_multiple_siblings(self) -> None:
        """Test handling of multiple sibling elements."""
        root = ET.Element("root")
        ET.SubElement(root, "child1").text = "a"
        ET.SubElement(root, "child2").text = "b"
        ET.SubElement(root, "child3").text = "c"

        indent_xml(root)

        # All children should have proper tail whitespace
        children = list(root)
        for child in children[:-1]:
            assert child.tail is not None
            assert "\n" in child.tail

    def test_deeply_nested_structure(self) -> None:
        """Test deeply nested XML structure."""
        root = ET.Element("a")
        b = ET.SubElement(root, "b")
        c = ET.SubElement(b, "c")
        d = ET.SubElement(c, "d")
        d.text = "deep"

        indent_xml(root)

        # Verify structure is still valid and pretty-printed
        output = ET.tostring(root, encoding="unicode")
        assert "<a>" in output
        assert "<b>" in output
        assert "<c>" in output
        assert "<d>deep</d>" in output

    def test_rss_like_structure(self) -> None:
        """Test with RSS-like XML structure."""
        rss = ET.Element("rss")
        rss.set("version", "2.0")
        channel = ET.SubElement(rss, "channel")
        ET.SubElement(channel, "title").text = "Test Feed"
        ET.SubElement(channel, "link").text = "https://example.com"

        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = "Article"
        ET.SubElement(item, "link").text = "https://example.com/article"

        indent_xml(rss)

        output = ET.tostring(rss, encoding="unicode")
        # Should have proper structure
        assert "Test Feed" in output
        assert "Article" in output
        # Should have newlines
        assert "\n" in output

    def test_sitemap_like_structure(self) -> None:
        """Test with sitemap-like XML structure."""
        urlset = ET.Element("urlset")
        urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

        url1 = ET.SubElement(urlset, "url")
        ET.SubElement(url1, "loc").text = "https://example.com/"
        ET.SubElement(url1, "lastmod").text = "2024-01-15"

        url2 = ET.SubElement(urlset, "url")
        ET.SubElement(url2, "loc").text = "https://example.com/about/"

        indent_xml(urlset)

        output = ET.tostring(urlset, encoding="unicode")
        assert "example.com" in output
        assert "\n" in output

    def test_with_custom_starting_level(self) -> None:
        """Test indent_xml with non-zero starting level."""
        child = ET.Element("child")
        grandchild = ET.SubElement(child, "grandchild")
        grandchild.text = "content"

        # Start at level 2 (as if embedded in larger document)
        indent_xml(child, level=2)

        # Should have 4+ spaces of indentation
        assert child.text is not None
        assert "      " in child.text  # 6 spaces for level 3

    def test_idempotent_on_already_indented(self) -> None:
        """Test that running indent_xml twice produces same result."""
        root = ET.Element("root")
        child = ET.SubElement(root, "child")
        child.text = "content"

        indent_xml(root)
        first_output = ET.tostring(root, encoding="unicode")

        indent_xml(root)
        second_output = ET.tostring(root, encoding="unicode")

        # Should be the same (idempotent)
        assert first_output == second_output
