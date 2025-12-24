"""
Unit tests for Content Intelligence (Document Application RFC Phase 6).

Tests content analysis for Document Application optimizations:
- Code block detection for tab suggestions
- Accessibility analysis
- Navigation pattern detection
- Speculation recommendations
"""

from __future__ import annotations

from unittest.mock import MagicMock

from bengal.analysis.content_intelligence import (
    ContentAnalysisReport,
    ContentIntelligence,
    ContentSuggestion,
    analyze_content_intelligence,
)


class TestContentSuggestion:
    """Tests for ContentSuggestion dataclass."""

    def test_to_dict(self):
        """Suggestion should convert to dictionary."""
        suggestion = ContentSuggestion(
            type="tabs",
            severity="info",
            message="Test message",
            page_path="/docs/test/",
            line_number=42,
            suggestion="Use tabs",
        )

        result = suggestion.to_dict()

        assert result["type"] == "tabs"
        assert result["severity"] == "info"
        assert result["message"] == "Test message"
        assert result["page_path"] == "/docs/test/"
        assert result["line_number"] == 42
        assert result["suggestion"] == "Use tabs"


class TestContentAnalysisReport:
    """Tests for ContentAnalysisReport dataclass."""

    def test_to_dict(self):
        """Report should convert to dictionary."""
        report = ContentAnalysisReport(
            pages_analyzed=10,
            code_blocks_detected=["/docs/api/"],
        )

        result = report.to_dict()

        assert result["pages_analyzed"] == 10
        assert "/docs/api/" in result["code_blocks_detected"]

    def test_summary(self):
        """Report should generate summary text."""
        report = ContentAnalysisReport(
            pages_analyzed=5,
            code_blocks_detected=["/docs/a/", "/docs/b/"],
        )

        summary = report.summary()

        assert "Pages analyzed: 5" in summary
        assert "Tab candidates: 2" in summary


class TestContentIntelligence:
    """Tests for ContentIntelligence analyzer."""

    def _create_mock_page(
        self,
        path: str,
        content: str = "",
        raw_content: str = "",
    ):
        """Create a mock page."""
        page = MagicMock()
        page._path = path
        page.content = content
        page.raw_content = raw_content or content
        return page

    def _create_mock_site(self, pages: list):
        """Create a mock site with pages."""
        site = MagicMock()
        site.pages = pages
        site.config = {}
        return site

    def test_detects_multiple_code_blocks(self):
        """Should detect pages with multiple code blocks."""
        content = """
```python
def hello():
    pass
```

```javascript
function hello() {}
```

```go
func hello() {}
```
"""
        page = self._create_mock_page("/docs/example/", raw_content=content)
        site = self._create_mock_site([page])

        intel = ContentIntelligence(site)
        report = intel.analyze()

        assert "/docs/example/" in report.code_blocks_detected
        assert len(report.suggestions) > 0
        assert any(s.type == "tabs" for s in report.suggestions)

    def test_ignores_single_language_blocks(self):
        """Should not flag pages with same-language code blocks."""
        content = """
```python
def hello():
    pass
```

```python
def world():
    pass
```

```python
def foo():
    pass
```
"""
        page = self._create_mock_page("/docs/example/", raw_content=content)
        site = self._create_mock_site([page])

        intel = ContentIntelligence(site)
        report = intel.analyze()

        # Only 1 unique language - not a tab candidate
        assert "/docs/example/" not in report.code_blocks_detected

    def test_detects_accessibility_warnings(self):
        """Should detect accessibility issues."""
        content = """
<h1>Title</h1>
<h3>Skipped h2!</h3>
<img src="test.png">
"""
        page = self._create_mock_page("/docs/test/", content=content)
        site = self._create_mock_site([page])

        intel = ContentIntelligence(site)
        report = intel.analyze()

        # Should have warnings for skipped heading and missing alt
        assert len(report.accessibility_warnings) > 0
        types = [w.type for w in report.accessibility_warnings]
        assert "accessibility" in types

    def test_tracks_navigation_patterns(self):
        """Should track section navigation patterns."""
        pages = [
            self._create_mock_page("/docs/page1/"),
            self._create_mock_page("/docs/page2/"),
            self._create_mock_page("/docs/page3/"),
            self._create_mock_page("/blog/post1/"),
        ]
        site = self._create_mock_site(pages)

        intel = ContentIntelligence(site)
        report = intel.analyze()

        assert "/docs/" in report.navigation_patterns
        assert report.navigation_patterns["/docs/"] == 3
        assert report.navigation_patterns["/blog/"] == 1

    def test_generates_speculation_recommendations(self):
        """Should generate speculation recommendations for sections."""
        pages = [self._create_mock_page(f"/docs/page{i}/") for i in range(15)]
        site = self._create_mock_site(pages)

        intel = ContentIntelligence(site)
        report = intel.analyze()

        # With 15 pages in /docs/, should recommend eager
        assert "/docs/" in report.speculation_recommendations
        assert report.speculation_recommendations["/docs/"] == "eager"


class TestConvenienceFunction:
    """Tests for analyze_content_intelligence function."""

    def test_analyze_content_intelligence(self):
        """Convenience function should work."""
        page = MagicMock()
        page._path = "/docs/test/"
        page.content = ""
        page.raw_content = ""

        site = MagicMock()
        site.pages = [page]
        site.config = {}

        report = analyze_content_intelligence(site)

        assert report.pages_analyzed == 1


