"""
Semantic Link Types and Connectivity Scoring for Bengal SSG.

Defines the semantic relationships between pages and provides weighted
connectivity scoring for nuanced content analysis. This replaces binary
orphan detection with a spectrum of connectivity levels that reveal
improvement opportunities.

Link Types (by editorial intent):
    High Intent (human-authored):
        - EXPLICIT: Markdown links [text](url) in content
        - MENU: Navigation menu items

    Medium Intent (algorithmic):
        - TAXONOMY: Shared tags/categories
        - RELATED: Computed related posts

    Low Intent (structural):
        - TOPICAL: Section hierarchy (parent → children)
        - SEQUENTIAL: Next/prev navigation

Default Weights:
    MENU: 10.0, EXPLICIT: 1.0, TAXONOMY: 1.0,
    RELATED: 0.75, TOPICAL: 0.5, SEQUENTIAL: 0.25

Connectivity Levels:
    - WELL_CONNECTED (🟢): Score >= 2.0 - No action needed
    - ADEQUATELY_LINKED (🟡): Score 1.0-2.0 - Could improve
    - LIGHTLY_LINKED (🟠): Score 0.25-1.0 - Should improve
    - ISOLATED (🔴): Score < 0.25 - Needs attention

Classes:
    LinkType: Enum of semantic link relationships
    LinkMetrics: Detailed link breakdown for weighted scoring
    ConnectivityLevel: Classification based on score thresholds
    ConnectivityReport: Site-wide connectivity analysis

Example:
    >>> metrics = LinkMetrics(explicit=2, taxonomy=1, topical=1)
    >>> score = metrics.connectivity_score()
    >>> level = ConnectivityLevel.from_score(score)
    >>> print(f"Score: {score}, Level: {level.label}")
    Score: 3.5, Level: Well-Connected

See Also:
    - bengal/analysis/knowledge_graph.py: Uses link types for graph building
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class LinkType(Enum):
    """
    Semantic relationship types between pages.

    Links carry meaning beyond simple connectivity. The type indicates
    the editorial intent and discoverability value of the relationship.

    Attributes:
        EXPLICIT: Human-authored markdown links [text](url) in content
        MENU: Navigation menu item (deliberate prominence)
        TAXONOMY: Shared tags/categories (topic clustering)
        RELATED: Algorithm-computed related posts (automated)
        TOPICAL: Section hierarchy parent → child (topical context)
        SEQUENTIAL: Next/prev navigation within section (reading order)
    """

    # Human-authored (high editorial intent)
    EXPLICIT = "explicit"
    MENU = "menu"

    # Algorithmic (medium intent)
    TAXONOMY = "taxonomy"
    RELATED = "related"

    # Structural (semantic context, low editorial intent)
    TOPICAL = "topical"
    SEQUENTIAL = "sequential"


# Default weights for each link type
DEFAULT_WEIGHTS: dict[LinkType, float] = {
    LinkType.EXPLICIT: 1.0,  # Human editorial endorsement
    LinkType.MENU: 10.0,  # Deliberate navigation prominence
    LinkType.TAXONOMY: 1.0,  # Topic clustering
    LinkType.RELATED: 0.75,  # Computed, not curated
    LinkType.TOPICAL: 0.5,  # Parent-child context
    LinkType.SEQUENTIAL: 0.25,  # Pure navigation structure
}


@dataclass
class LinkMetrics:
    """
    Detailed link breakdown for a page.

    Tracks the count of each link type pointing to a page,
    enabling weighted connectivity scoring.

    Attributes:
        explicit: Count of explicit markdown links
        menu: Count of menu item references
        taxonomy: Count of shared taxonomy links
        related: Count of related post links
        topical: Count of section hierarchy links (parent → child)
        sequential: Count of next/prev navigation links

    Example:
        >>> metrics = LinkMetrics(explicit=2, taxonomy=1, topical=1)
        >>> metrics.connectivity_score()
        3.5
        >>> metrics.has_human_links()
        True
    """

    explicit: int = 0
    menu: int = 0
    taxonomy: int = 0
    related: int = 0
    topical: int = 0
    sequential: int = 0

    def connectivity_score(self, weights: dict[LinkType, float] | None = None) -> float:
        """
        Calculate weighted connectivity score.

        Args:
            weights: Optional custom weights. Defaults to DEFAULT_WEIGHTS.

        Returns:
            Weighted sum of all link counts. Higher = better connected.
        """
        w = weights or DEFAULT_WEIGHTS
        return (
            self.explicit * w[LinkType.EXPLICIT]
            + self.menu * w[LinkType.MENU]
            + self.taxonomy * w[LinkType.TAXONOMY]
            + self.related * w[LinkType.RELATED]
            + self.topical * w[LinkType.TOPICAL]
            + self.sequential * w[LinkType.SEQUENTIAL]
        )

    def total_links(self) -> int:
        """Total number of incoming links (unweighted)."""
        return (
            self.explicit
            + self.menu
            + self.taxonomy
            + self.related
            + self.topical
            + self.sequential
        )

    def has_human_links(self) -> bool:
        """True if page has any human-authored links (explicit or menu)."""
        return self.explicit > 0 or self.menu > 0

    def has_structural_links(self) -> bool:
        """True if page has structural links (section/nav)."""
        return self.topical > 0 or self.sequential > 0

    def has_any_links(self) -> bool:
        """True if page has any incoming links."""
        return self.total_links() > 0

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary for serialization."""
        return {
            "explicit": self.explicit,
            "menu": self.menu,
            "taxonomy": self.taxonomy,
            "related": self.related,
            "topical": self.topical,
            "sequential": self.sequential,
        }


# Default thresholds for connectivity levels
DEFAULT_THRESHOLDS: dict[str, float] = {
    "well_connected": 2.0,  # Multiple link types
    "adequately_linked": 1.0,  # Has some connections
    "lightly_linked": 0.25,  # Only structural/single taxonomy
    # Below lightly_linked = isolated
}


class ConnectivityLevel(Enum):
    """
    Connectivity classification based on weighted score thresholds.

    Replaces binary orphan/not-orphan with nuanced levels that
    reveal opportunities for improvement.

    Levels (from best to worst):
        - WELL_CONNECTED: Score >= 2.0 (no action needed)
        - ADEQUATELY_LINKED: Score 1.0-2.0 (could improve)
        - LIGHTLY_LINKED: Score 0.25-1.0 (should improve)
        - ISOLATED: Score < 0.25 (needs attention)

    Example:
        >>> level = ConnectivityLevel.from_score(1.5)
        >>> print(level.value)
        adequately
        >>> level.emoji
        '🟡'
    """

    WELL_CONNECTED = "well_connected"
    ADEQUATELY_LINKED = "adequately"
    LIGHTLY_LINKED = "lightly"
    ISOLATED = "isolated"

    @classmethod
    def from_score(
        cls, score: float, thresholds: dict[str, float] | None = None
    ) -> ConnectivityLevel:
        """
        Classify a page based on its connectivity score.

        Args:
            score: Weighted connectivity score from LinkMetrics
            thresholds: Optional custom thresholds. Defaults to DEFAULT_THRESHOLDS.

        Returns:
            ConnectivityLevel classification
        """
        t = thresholds or DEFAULT_THRESHOLDS
        if score >= t["well_connected"]:
            return cls.WELL_CONNECTED
        elif score >= t["adequately_linked"]:
            return cls.ADEQUATELY_LINKED
        elif score >= t["lightly_linked"]:
            return cls.LIGHTLY_LINKED
        else:
            return cls.ISOLATED

    @property
    def emoji(self) -> str:
        """Get emoji indicator for this level."""
        return {
            ConnectivityLevel.WELL_CONNECTED: "🟢",
            ConnectivityLevel.ADEQUATELY_LINKED: "🟡",
            ConnectivityLevel.LIGHTLY_LINKED: "🟠",
            ConnectivityLevel.ISOLATED: "🔴",
        }[self]

    @property
    def label(self) -> str:
        """Get human-readable label for this level."""
        return {
            ConnectivityLevel.WELL_CONNECTED: "Well-Connected",
            ConnectivityLevel.ADEQUATELY_LINKED: "Adequately Linked",
            ConnectivityLevel.LIGHTLY_LINKED: "Lightly Linked",
            ConnectivityLevel.ISOLATED: "Isolated",
        }[self]

    @property
    def description(self) -> str:
        """Get description of what action is needed for this level."""
        return {
            ConnectivityLevel.WELL_CONNECTED: "No action needed",
            ConnectivityLevel.ADEQUATELY_LINKED: "Could improve with more links",
            ConnectivityLevel.LIGHTLY_LINKED: "Should add explicit cross-references",
            ConnectivityLevel.ISOLATED: "Needs immediate attention",
        }[self]


@dataclass
class ConnectivityReport:
    """
    Complete connectivity report for a site.

    Groups pages by connectivity level and provides distribution statistics.

    Attributes:
        isolated: Pages with score < 0.25
        lightly_linked: Pages with score 0.25-1.0
        adequately_linked: Pages with score 1.0-2.0
        well_connected: Pages with score >= 2.0
        total_pages: Total number of pages analyzed
        avg_score: Average connectivity score across all pages
    """

    isolated: list = field(default_factory=list)
    lightly_linked: list = field(default_factory=list)
    adequately_linked: list = field(default_factory=list)
    well_connected: list = field(default_factory=list)
    total_pages: int = 0
    avg_score: float = 0.0

    def get_distribution(self) -> dict[str, int]:
        """Get count distribution by level."""
        return {
            "isolated": len(self.isolated),
            "lightly_linked": len(self.lightly_linked),
            "adequately_linked": len(self.adequately_linked),
            "well_connected": len(self.well_connected),
        }

    def get_percentages(self) -> dict[str, float]:
        """Get percentage distribution by level."""
        if self.total_pages == 0:
            return {
                level: 0.0
                for level in ["isolated", "lightly_linked", "adequately_linked", "well_connected"]
            }
        return {
            level: (count / self.total_pages * 100)
            for level, count in self.get_distribution().items()
        }

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "isolated": [str(p.source_path) for p in self.isolated],
            "lightly_linked": [str(p.source_path) for p in self.lightly_linked],
            "adequately_linked": [str(p.source_path) for p in self.adequately_linked],
            "well_connected": [str(p.source_path) for p in self.well_connected],
            "distribution": self.get_distribution(),
            "percentages": self.get_percentages(),
            "total_pages": self.total_pages,
            "avg_score": round(self.avg_score, 2),
        }
