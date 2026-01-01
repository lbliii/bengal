"""
Unit tests for Feature Detector.

Tests CSS feature detection from page content:
- Mermaid diagram detection
- Data table detection
- Graph visualization detection
- Interactive widget detection
"""

from __future__ import annotations

from unittest.mock import MagicMock


class TestFeatureDetector:
    """Tests for FeatureDetector class."""

    def test_detects_mermaid_code_block(self) -> None:
        """Should detect mermaid diagrams from code blocks."""
        from bengal.orchestration.feature_detector import FeatureDetector

        detector = FeatureDetector()
        content = """
# My Page

Here's a diagram:

```mermaid
graph TD
    A --> B
```
"""
        features = detector.detect_features_in_content(content)

        assert "mermaid" in features

    def test_detects_mermaid_directive(self) -> None:
        """Should detect mermaid from Bengal directives."""
        from bengal.orchestration.feature_detector import FeatureDetector

        detector = FeatureDetector()
        content = """
# My Page

:::{mermaid}
graph TD
    A --> B
:::
"""
        features = detector.detect_features_in_content(content)

        assert "mermaid" in features

    def test_detects_datatable(self) -> None:
        """Should detect data tables from tabulator references."""
        from bengal.orchestration.feature_detector import FeatureDetector

        detector = FeatureDetector()
        content = """
# Data Display

Using tabulator to show data:

```javascript
new Tabulator("#table", {});
```
"""
        features = detector.detect_features_in_content(content)

        assert "data_tables" in features

    def test_detects_datatable_directive(self) -> None:
        """Should detect data tables from Bengal directives."""
        from bengal.orchestration.feature_detector import FeatureDetector

        detector = FeatureDetector()
        content = """
# My Page

:::{datatable}
data.csv
:::
"""
        features = detector.detect_features_in_content(content)

        assert "data_tables" in features

    def test_detects_interactive_content(self) -> None:
        """Should detect interactive widgets."""
        from bengal.orchestration.feature_detector import FeatureDetector

        detector = FeatureDetector()
        content = """
# Interactive Demo

This uses marimo for interactive content.
"""
        features = detector.detect_features_in_content(content)

        assert "interactive" in features

    def test_returns_empty_for_plain_content(self) -> None:
        """Should return empty set for plain markdown."""
        from bengal.orchestration.feature_detector import FeatureDetector

        detector = FeatureDetector()
        content = """
# Simple Page

This is just plain text with no special features.

- Item 1
- Item 2
"""
        features = detector.detect_features_in_content(content)

        assert len(features) == 0

    def test_returns_empty_for_empty_content(self) -> None:
        """Should return empty set for empty content."""
        from bengal.orchestration.feature_detector import FeatureDetector

        detector = FeatureDetector()
        features = detector.detect_features_in_content("")

        assert len(features) == 0

    def test_returns_empty_for_none_content(self) -> None:
        """Should handle None content gracefully."""
        from bengal.orchestration.feature_detector import FeatureDetector

        detector = FeatureDetector()
        features = detector.detect_features_in_content(None)  # type: ignore

        assert len(features) == 0

    def test_detects_multiple_features(self) -> None:
        """Should detect multiple features in same content."""
        from bengal.orchestration.feature_detector import FeatureDetector

        detector = FeatureDetector()
        content = """
# Complex Page

```mermaid
graph TD
    A --> B
```

Using tabulator:

```javascript
new Tabulator("#table", {});
```
"""
        features = detector.detect_features_in_content(content)

        assert "mermaid" in features
        assert "data_tables" in features

    def test_detect_features_in_page(self) -> None:
        """Should detect features from page object."""
        from bengal.orchestration.feature_detector import FeatureDetector

        detector = FeatureDetector()

        page = MagicMock()
        # Note: source code uses page._source, not page.content
        page._source = """
```mermaid
graph TD
    A --> B
```
"""
        page.metadata = {}

        features = detector.detect_features_in_page(page)

        assert "mermaid" in features

    def test_detect_features_from_metadata(self) -> None:
        """Should detect features from page metadata."""
        from bengal.orchestration.feature_detector import FeatureDetector

        detector = FeatureDetector()

        page = MagicMock()
        page._source = ""  # Required: source code uses page._source
        page.metadata = {"mermaid": True}

        features = detector.detect_features_in_page(page)

        assert "mermaid" in features

    def test_detect_interactive_from_metadata(self) -> None:
        """Should detect interactive feature from metadata."""
        from bengal.orchestration.feature_detector import FeatureDetector

        detector = FeatureDetector()

        page = MagicMock()
        page._source = ""  # Required: source code uses page._source
        page.metadata = {"interactive": True}

        features = detector.detect_features_in_page(page)

        assert "interactive" in features


class TestDetectSiteFeatures:
    """Tests for detect_site_features function."""

    def test_aggregates_features_from_all_pages(self) -> None:
        """Should aggregate features from all pages."""
        from bengal.orchestration.feature_detector import detect_site_features

        site = MagicMock()

        page1 = MagicMock()
        page1._source = "```mermaid\ngraph TD\n```"  # Required: source code uses page._source
        page1.metadata = {}

        page2 = MagicMock()
        page2._source = "Using tabulator"  # Required: source code uses page._source
        page2.metadata = {}

        site.pages = [page1, page2]

        features = detect_site_features(site)

        assert "mermaid" in features
        assert "data_tables" in features

    def test_returns_empty_for_empty_site(self) -> None:
        """Should return empty set for site with no pages."""
        from bengal.orchestration.feature_detector import detect_site_features

        site = MagicMock()
        site.pages = []

        features = detect_site_features(site)

        assert len(features) == 0

    def test_handles_pages_without_features(self) -> None:
        """Should handle pages with no special features."""
        from bengal.orchestration.feature_detector import detect_site_features

        site = MagicMock()

        page = MagicMock()
        page._source = "# Simple page\n\nJust text."  # Required: source code uses page._source
        page.metadata = {}

        site.pages = [page]

        features = detect_site_features(site)

        assert len(features) == 0
