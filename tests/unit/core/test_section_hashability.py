"""
Test Section hashability and set operations.

Tests that Section objects are properly hashable based on path,
enabling set storage, dictionary keys, and O(1) membership tests.
"""

import pytest
from pathlib import Path
from bengal.core.section import Section
from bengal.core.page import Page


class TestSectionHashability:
    """Test that Section objects are properly hashable."""
    
    def test_section_is_hashable(self, tmp_path):
        """Sections can be hashed."""
        section = Section(name="blog", path=tmp_path / "blog")
        assert isinstance(hash(section), int)
    
    def test_section_equality_by_path(self, tmp_path):
        """Sections with same path are equal."""
        path = tmp_path / "blog"
        section1 = Section(name="blog", path=path)
        section2 = Section(name="blog", path=path)
        
        assert section1 == section2
        assert hash(section1) == hash(section2)
    
    def test_section_inequality_different_paths(self, tmp_path):
        """Sections with different paths are not equal."""
        section1 = Section(name="blog", path=tmp_path / "blog")
        section2 = Section(name="docs", path=tmp_path / "docs")
        
        assert section1 != section2
    
    def test_section_hash_stable_across_mutations(self, tmp_path):
        """Hash remains stable when mutable fields change."""
        section = Section(name="blog", path=tmp_path / "blog")
        initial_hash = hash(section)
        
        # Mutate various fields
        page1 = Page(source_path=tmp_path / "blog/post1.md")
        page2 = Page(source_path=tmp_path / "blog/post2.md")
        section.pages.extend([page1, page2])
        section.metadata = {'title': 'Blog Section', 'description': 'My blog'}
        section.index_page = page1
        
        # Add subsection
        subsection = Section(name="tutorials", path=tmp_path / "blog/tutorials")
        section.subsections.append(subsection)
        
        # Hash should remain unchanged
        assert hash(section) == initial_hash
    
    def test_section_in_set(self, tmp_path):
        """Sections can be stored in sets."""
        section1 = Section(name="blog", path=tmp_path / "blog")
        section2 = Section(name="docs", path=tmp_path / "docs")
        section3 = Section(name="blog", path=tmp_path / "blog")  # Duplicate
        
        sections = {section1, section2, section3}
        
        # Should deduplicate section1 and section3
        assert len(sections) == 2
        assert section1 in sections
        assert section2 in sections
        assert section3 in sections  # Same as section1
    
    def test_section_as_dict_key(self, tmp_path):
        """Sections can be used as dictionary keys."""
        section1 = Section(name="blog", path=tmp_path / "blog")
        section2 = Section(name="docs", path=tmp_path / "docs")
        
        data = {
            section1: "blog data",
            section2: "docs data"
        }
        
        assert data[section1] == "blog data"
        assert data[section2] == "docs data"
        
        # Lookup with equivalent section works
        section1_copy = Section(name="blog", path=tmp_path / "blog")
        assert data[section1_copy] == "blog data"
    
    def test_section_findable_in_set_after_mutation(self, tmp_path):
        """Section remains findable in set after mutation."""
        section = Section(name="blog", path=tmp_path / "blog")
        sections = {section}
        
        # Mutate the section
        section.pages.append(Page(source_path=tmp_path / "blog/post.md"))
        section.metadata = {'updated': True}
        
        # Should still be findable
        assert section in sections
    
    def test_section_equality_ignores_pages(self, tmp_path):
        """Sections are equal based on path, not pages."""
        path = tmp_path / "blog"
        section1 = Section(name="blog", path=path)
        section2 = Section(name="blog", path=path)
        
        # Add pages to only one section
        section1.pages.append(Page(source_path=tmp_path / "blog/post1.md"))
        section1.pages.append(Page(source_path=tmp_path / "blog/post2.md"))
        
        # Still equal despite different pages
        assert section1 == section2
        assert hash(section1) == hash(section2)
    
    def test_section_equality_ignores_name(self, tmp_path):
        """Sections are equal based on path, even if name differs."""
        path = tmp_path / "blog"
        section1 = Section(name="blog", path=path)
        section2 = Section(name="Blog Posts", path=path)  # Different name
        
        # Equal despite different names
        assert section1 == section2
        assert hash(section1) == hash(section2)
    
    def test_section_not_equal_to_other_types(self, tmp_path):
        """Sections are not equal to non-Section objects."""
        section = Section(name="blog", path=tmp_path / "blog")
        
        assert section != str(tmp_path / "blog")
        assert section != tmp_path / "blog"
        assert section != None
        assert section != 42
        assert section != {'name': 'blog', 'path': tmp_path / "blog"}


class TestSectionSetOperations:
    """Test set operations with sections."""
    
    def test_set_union(self, tmp_path):
        """Set union works with sections."""
        section1 = Section(name="blog", path=tmp_path / "blog")
        section2 = Section(name="docs", path=tmp_path / "docs")
        section3 = Section(name="tutorials", path=tmp_path / "tutorials")
        
        set1 = {section1, section2}
        set2 = {section2, section3}
        
        union = set1 | set2
        assert len(union) == 3
        assert section1 in union
        assert section2 in union
        assert section3 in union
    
    def test_set_intersection(self, tmp_path):
        """Set intersection works with sections."""
        section1 = Section(name="blog", path=tmp_path / "blog")
        section2 = Section(name="docs", path=tmp_path / "docs")
        section3 = Section(name="tutorials", path=tmp_path / "tutorials")
        
        set1 = {section1, section2}
        set2 = {section2, section3}
        
        intersection = set1 & set2
        assert len(intersection) == 1
        assert section2 in intersection
    
    def test_set_difference(self, tmp_path):
        """Set difference works with sections."""
        section1 = Section(name="blog", path=tmp_path / "blog")
        section2 = Section(name="docs", path=tmp_path / "docs")
        section3 = Section(name="tutorials", path=tmp_path / "tutorials")
        
        set1 = {section1, section2, section3}
        set2 = {section2}
        
        difference = set1 - set2
        assert len(difference) == 2
        assert section1 in difference
        assert section3 in difference


class TestSectionDictionaryOperations:
    """Test dictionary operations with sections as keys."""
    
    def test_dict_get_and_set(self, tmp_path):
        """Basic dict operations with section keys."""
        section = Section(name="blog", path=tmp_path / "blog")
        
        data = {}
        data[section] = "some value"
        
        assert data[section] == "some value"
        assert section in data
    
    def test_dict_update(self, tmp_path):
        """Dict update with equivalent section."""
        section1 = Section(name="blog", path=tmp_path / "blog")
        section2 = Section(name="blog", path=tmp_path / "blog")  # Same path
        
        data = {section1: "first value"}
        data[section2] = "second value"  # Should update, not add
        
        assert len(data) == 1
        assert data[section1] == "second value"
        assert data[section2] == "second value"


class TestSectionHashStability:
    """Test hash stability in various scenarios."""
    
    def test_hash_consistent_across_calls(self, tmp_path):
        """Hash value is consistent across multiple calls."""
        section = Section(name="blog", path=tmp_path / "blog")
        
        hash1 = hash(section)
        hash2 = hash(section)
        hash3 = hash(section)
        
        assert hash1 == hash2 == hash3
    
    def test_hash_stable_with_all_fields_set(self, tmp_path):
        """Hash stable even when all fields are populated."""
        section = Section(name="blog", path=tmp_path / "blog")
        
        # Populate all fields
        section.pages = [
            Page(source_path=tmp_path / "blog/post1.md"),
            Page(source_path=tmp_path / "blog/post2.md")
        ]
        section.subsections = [
            Section(name="tutorials", path=tmp_path / "blog/tutorials")
        ]
        section.metadata = {'title': 'Blog', 'description': 'My blog'}
        section.index_page = section.pages[0]
        section.parent = Section(name="root", path=tmp_path)
        
        hash1 = hash(section)
        
        # Modify everything except path
        section.pages = []
        section.subsections = []
        section.metadata = {}
        section.index_page = None
        section.parent = None
        
        hash2 = hash(section)
        
        assert hash1 == hash2


class TestSectionPageIntegration:
    """Test interaction between hashable Sections and Pages."""
    
    def test_tracking_affected_sections(self, tmp_path):
        """Real-world use case: tracking affected sections."""
        # Create sections
        blog_section = Section(name="blog", path=tmp_path / "blog")
        docs_section = Section(name="docs", path=tmp_path / "docs")
        
        # Create pages
        pages = [
            Page(source_path=tmp_path / "blog/post1.md"),
            Page(source_path=tmp_path / "blog/post2.md"),
            Page(source_path=tmp_path / "docs/guide1.md"),
            Page(source_path=tmp_path / "blog/post3.md"),
        ]
        
        # Assign pages to sections
        pages[0]._section = blog_section
        pages[1]._section = blog_section
        pages[2]._section = docs_section
        pages[3]._section = blog_section
        
        # Track affected sections (simulating incremental build)
        affected_sections = set()
        for page in pages:
            if hasattr(page, '_section') and page._section:
                affected_sections.add(page._section)
        
        # Should have 2 unique sections
        assert len(affected_sections) == 2
        assert blog_section in affected_sections
        assert docs_section in affected_sections
    
    def test_section_to_pages_mapping(self, tmp_path):
        """Map sections to their pages using dict."""
        section1 = Section(name="blog", path=tmp_path / "blog")
        section2 = Section(name="docs", path=tmp_path / "docs")
        
        page1 = Page(source_path=tmp_path / "blog/post1.md")
        page2 = Page(source_path=tmp_path / "blog/post2.md")
        page3 = Page(source_path=tmp_path / "docs/guide.md")
        
        # Build mapping
        section_pages = {
            section1: [page1, page2],
            section2: [page3]
        }
        
        assert len(section_pages[section1]) == 2
        assert len(section_pages[section2]) == 1
        assert page1 in section_pages[section1]
        assert page3 in section_pages[section2]

