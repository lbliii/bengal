"""
Content Intelligence for Document Applications.

Analyzes content at author-time to provide intelligent suggestions
and optimizations for Document Application features.

Features:
- Code example detection → Suggest CSS-state tabs
- Content relationship analysis → Optimize speculation rules
- Navigation pattern detection → Suggest prefetch strategies
- Accessibility analysis → Emit warnings
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

__all__ = [
    "ContentIntelligence",
    "ContentAnalysisReport",
    "analyze_content_intelligence",
]

logger = get_logger(__name__)


@dataclass
class ContentSuggestion:
    """A suggestion for content optimization."""

    type: str  # tabs | prefetch | prerender | accessibility | structure
    severity: str  # info | warning | error
    message: str
    page_path: str
    line_number: int | None = None
    suggestion: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "severity": self.severity,
            "message": self.message,
            "page_path": self.page_path,
            "line_number": self.line_number,
            "suggestion": self.suggestion,
        }


@dataclass
class ContentAnalysisReport:
    """
    Report of content intelligence analysis.

    Attributes:
        pages_analyzed: Number of pages analyzed
        code_blocks_detected: Pages with multiple code blocks (tab candidates)
        accessibility_warnings: Accessibility issues found
        navigation_patterns: Detected navigation patterns
        suggestions: List of improvement suggestions
        speculation_recommendations: Recommended speculation rules
    """

    pages_analyzed: int = 0
    code_blocks_detected: list[str] = field(default_factory=list)
    accessibility_warnings: list[ContentSuggestion] = field(default_factory=list)
    navigation_patterns: dict[str, int] = field(default_factory=dict)
    suggestions: list[ContentSuggestion] = field(default_factory=list)
    speculation_recommendations: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "pages_analyzed": self.pages_analyzed,
            "code_blocks_detected": self.code_blocks_detected,
            "accessibility_warnings": [w.to_dict() for w in self.accessibility_warnings],
            "navigation_patterns": self.navigation_patterns,
            "suggestions_count": len(self.suggestions),
            "suggestions": [s.to_dict() for s in self.suggestions[:20]],  # Top 20
            "speculation_recommendations": self.speculation_recommendations,
        }

    def summary(self) -> str:
        """Generate a human-readable summary."""
        lines = [
            "═" * 60,
            "  Document Application: Content Intelligence Report",
            "═" * 60,
            "",
            f"  Pages analyzed: {self.pages_analyzed}",
            f"  Tab candidates: {len(self.code_blocks_detected)}",
            f"  Accessibility warnings: {len(self.accessibility_warnings)}",
            f"  Total suggestions: {len(self.suggestions)}",
            "",
        ]

        if self.code_blocks_detected:
            lines.append("  📑 Pages with multiple code blocks (consider tabs):")
            for path in self.code_blocks_detected[:5]:
                lines.append(f"     • {path}")
            if len(self.code_blocks_detected) > 5:
                lines.append(f"     ... and {len(self.code_blocks_detected) - 5} more")
            lines.append("")

        if self.accessibility_warnings:
            lines.append("  ⚠️  Accessibility warnings:")
            for warning in self.accessibility_warnings[:5]:
                lines.append(f"     • {warning.page_path}: {warning.message}")
            if len(self.accessibility_warnings) > 5:
                lines.append(f"     ... and {len(self.accessibility_warnings) - 5} more")
            lines.append("")

        if self.speculation_recommendations:
            lines.append("  🚀 Speculation recommendations:")
            for path, eagerness in list(self.speculation_recommendations.items())[:5]:
                lines.append(f"     • {path}: {eagerness}")
            lines.append("")

        lines.append("═" * 60)
        return "\n".join(lines)


class ContentIntelligence:
    """
    Analyzes content for Document Application optimizations.

    This runs at author-time (during build) to provide intelligent
    suggestions for improving the user experience.

    Example usage:
        intel = ContentIntelligence(site)
        report = intel.analyze()
        print(report.summary())
    """

    def __init__(self, site: Site):
        """
        Initialize content intelligence analyzer.

        Args:
            site: The Bengal site instance
        """
        self.site = site

    def analyze(self) -> ContentAnalysisReport:
        """
        Perform content intelligence analysis.

        Returns:
            ContentAnalysisReport with analysis results
        """
        report = ContentAnalysisReport()

        for page in self.site.pages:
            report.pages_analyzed += 1
            self._analyze_page(page, report)

        # Generate speculation recommendations
        self._generate_speculation_recommendations(report)

        return report

    def _analyze_page(self, page: Any, report: ContentAnalysisReport) -> None:
        """
        Analyze a single page for content patterns.

        Args:
            page: Page to analyze
            report: Report to update
        """
        path = getattr(page, "_path", "") or ""
        content = getattr(page, "content", "") or ""
        raw_content = getattr(page, "raw_content", "") or content

        # Check for multiple code blocks (tab candidates)
        self._check_code_blocks(path, raw_content, report)

        # Check for accessibility issues
        self._check_accessibility(page, path, content, report)

        # Track navigation patterns
        self._track_navigation_patterns(page, path, report)

    def _check_code_blocks(self, path: str, content: str, report: ContentAnalysisReport) -> None:
        """
        Check for multiple code blocks that could be tabs.

        Detects patterns like:
        - Multiple consecutive fenced code blocks
        - Code blocks with different language tags
        """
        # Find all fenced code blocks
        code_block_pattern = re.compile(r"```(\w+)?")
        languages = code_block_pattern.findall(content)

        if len(languages) >= 3:
            # Check if they're different languages (tab candidate)
            unique_langs = set(lang for lang in languages if lang)
            if len(unique_langs) >= 2:
                report.code_blocks_detected.append(path)
                report.suggestions.append(
                    ContentSuggestion(
                        type="tabs",
                        severity="info",
                        message=f"Page has {len(languages)} code blocks with {len(unique_langs)} languages",
                        page_path=path,
                        suggestion="Consider using tab-set directive for code examples",
                    )
                )

    def _check_accessibility(
        self, page: Any, path: str, content: str, report: ContentAnalysisReport
    ) -> None:
        """
        Check for accessibility issues.

        Checks:
        - Missing alt text on images
        - Heading structure
        - Link text quality
        """
        # Check for images without alt text
        img_pattern = re.compile(r'<img[^>]*(?<!alt=")[^>]*>')
        imgs_without_alt = img_pattern.findall(content)

        for img in imgs_without_alt:
            if 'alt=""' not in img and "alt=''" not in img:
                report.accessibility_warnings.append(
                    ContentSuggestion(
                        type="accessibility",
                        severity="warning",
                        message="Image may be missing alt text",
                        page_path=path,
                        suggestion="Add descriptive alt text to images",
                    )
                )
                break  # One warning per page is enough

        # Check heading structure
        headings = re.findall(r"<h([1-6])", content)
        if headings:
            # Check for skipped heading levels
            levels = [int(h) for h in headings]
            for i in range(1, len(levels)):
                if levels[i] > levels[i - 1] + 1:
                    report.accessibility_warnings.append(
                        ContentSuggestion(
                            type="accessibility",
                            severity="warning",
                            message=f"Heading levels skipped (h{levels[i - 1]} to h{levels[i]})",
                            page_path=path,
                            suggestion="Maintain proper heading hierarchy",
                        )
                    )
                    break

    def _track_navigation_patterns(
        self, page: Any, path: str, report: ContentAnalysisReport
    ) -> None:
        """
        Track navigation patterns for speculation optimization.
        """
        # Get section from path
        parts = path.strip("/").split("/")
        if parts and parts[0]:
            section = f"/{parts[0]}/"
            report.navigation_patterns[section] = report.navigation_patterns.get(section, 0) + 1

    def _generate_speculation_recommendations(self, report: ContentAnalysisReport) -> None:
        """
        Generate speculation rule recommendations based on content analysis.
        """
        if not report.navigation_patterns:
            return

        # Sort sections by page count
        sorted_sections = sorted(
            report.navigation_patterns.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        # Top sections get more aggressive prefetch
        for _i, (section, count) in enumerate(sorted_sections[:5]):
            if count >= 10:
                report.speculation_recommendations[section] = "eager"
            elif count >= 5:
                report.speculation_recommendations[section] = "moderate"
            else:
                report.speculation_recommendations[section] = "conservative"


def analyze_content_intelligence(site: Site) -> ContentAnalysisReport:
    """
    Convenience function to analyze content intelligence.

    Args:
        site: The Bengal site instance

    Returns:
        ContentAnalysisReport with analysis results
    """
    intel = ContentIntelligence(site)
    return intel.analyze()
