"""
Unit tests for Dashboard widgets.

These tests verify that UI components correctly interface with Core models
and handle various edge cases (like orphan pages or virtual sections).
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from bengal.cli.dashboard.widgets.content_browser import ContentBrowser
from bengal.core.page import Page
from bengal.core.section import Section


class TestContentBrowser:
    """Tests for the ContentBrowser widget."""

    def test_rebuild_tree_logic(self):
        """Verify _rebuild_tree correctly groups pages by section."""
        # Create a mock site with pages and sections
        mock_site = MagicMock()
        
        # Section 1
        sec1 = MagicMock(spec=Section)
        sec1.path = Path("docs")
        sec1.title = "Documentation"
        sec1.source_path = Path("docs") # For safety in case someone uses old attr
        
        # Page 1 in Section 1
        p1 = MagicMock(spec=Page)
        p1.title = "Getting Started"
        p1.section_path = "docs"
        p1.metadata = {}
        p1.assigned_template = None
        
        # Orphan Page
        p2 = MagicMock(spec=Page)
        p2.title = "Root Page"
        p2.section_path = None
        p2.metadata = {"_generated": True}
        p2.assigned_template = "archive.html"
        
        mock_site.pages = [p1, p2]
        mock_site.sections = [sec1]
        
        # Mock the Tree widget
        with patch("bengal.cli.dashboard.widgets.content_browser.Tree") as MockTree:
            # Create widget
            widget = ContentBrowser()
            widget._site = mock_site
            
            # Setup tree mocks
            tree_root = MockTree.return_value.root
            section_node = MagicMock()
            tree_root.add.return_value = section_node
            
            # Run the logic we want to test
            widget._rebuild_tree()
            
            # Print calls for debugging
            print(f"\nDEBUG: add calls: {tree_root.add.call_args_list}")
            
            # Verify section was added
            # Use ANY for the section object to avoid mock identity issues
            from unittest.mock import ANY
            tree_root.add.assert_any_call(
                "📁 Documentation (1)",
                data={"type": "section", "section": ANY}
            )
            
            # Verify page under section was added
            section_node.add_leaf.assert_called_once()
            args, kwargs = section_node.add_leaf.call_args
            assert "Getting Started" in args[0]
            
            # Verify orphan page was added to root
            tree_root.add_leaf.assert_called_once()
            args, kwargs = tree_root.add_leaf.call_args
            assert "Root Page" in args[0]
            assert "⚡" in args[0] # Indicator for _generated
            assert "📚" in args[0] # Indicator for archive.html
