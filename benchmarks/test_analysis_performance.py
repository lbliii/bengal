"""
Benchmark suite for Bengal analysis algorithm performance.

This suite establishes baselines and validates performance improvements
for analysis algorithms (PageRank, Link Suggestions, etc.).

RFC: rfc-analysis-algorithm-optimization
Optimizations Tracked:
    - PageRank: O(I × N²) → O(I × E) via incoming edges index
    - Link Suggestions: O(N² × T) → O(N × overlap × T) via inverted indices

Benchmark Categories:
====================

1. Synthetic Graph Generation
   - Generate sites with configurable page counts and link densities
   - Create realistic tag/category distributions

2. PageRank Performance
   - test_pagerank_100_pages: Small site baseline
   - test_pagerank_1k_pages: Medium site
   - test_pagerank_5k_pages: Large site
   - test_pagerank_10k_pages: Very large site (primary target)

3. Link Suggestions Performance
   - test_link_suggestions_100_pages: Small site baseline
   - test_link_suggestions_1k_pages: Medium site
   - test_link_suggestions_5k_pages: Large site

4. Graph Build Performance
   - test_graph_build_performance: Graph construction baseline

Expected Performance (Post-Optimization):
=========================================
- PageRank 10K pages: < 30 seconds (vs ~8 min pre-optimization)
- Link Suggestions 10K pages: < 2 minutes (vs ~20 min pre-optimization)
- Expected speedup: 10-100x for PageRank, 5-20x for Link Suggestions
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass


@dataclass
class SyntheticPage:
    """Mock page for benchmarking analysis algorithms."""

    title: str
    source_path: Path
    tags: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    related_posts: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def __hash__(self):
        return hash(self.title)

    def __eq__(self, other):
        if isinstance(other, SyntheticPage):
            return self.title == other.title
        return False

    def extract_links(self):
        """Mock link extraction - links are pre-populated."""
        pass


class SyntheticSite:
    """
    Generate synthetic sites with configurable characteristics.

    Produces realistic graph structures for benchmarking:
    - Power-law link distribution (few pages have many links)
    - Tag clustering (pages share tags in realistic groups)
    - Category hierarchy (1-5 categories per page)
    """

    def __init__(
        self,
        page_count: int,
        avg_links_per_page: int = 5,
        avg_tags_per_page: int = 3,
        tag_pool_size: int = 50,
        category_pool_size: int = 10,
        seed: int = 42,
    ):
        """
        Initialize synthetic site generator.

        Args:
            page_count: Number of pages to generate
            avg_links_per_page: Average outgoing links per page
            avg_tags_per_page: Average tags per page
            tag_pool_size: Total unique tags in the site
            category_pool_size: Total unique categories
            seed: Random seed for reproducibility
        """
        self.page_count = page_count
        self.avg_links = avg_links_per_page
        self.avg_tags = avg_tags_per_page
        self.tag_pool_size = tag_pool_size
        self.category_pool_size = category_pool_size
        self.seed = seed

        random.seed(seed)

        # Generate tag and category pools
        self.tag_pool = [f"tag-{i}" for i in range(tag_pool_size)]
        self.category_pool = [f"category-{i}" for i in range(category_pool_size)]

        # Generate pages
        self.pages: list[SyntheticPage] = []
        self._generate_pages()
        self._generate_links()

        # Mock site attributes
        self.config = {"parallel_graph": False}
        self.xref_index = self._build_xref_index()
        self.taxonomies = {}
        self.menu = {}

    def _generate_pages(self):
        """Generate pages with tags and categories."""
        for i in range(self.page_count):
            # Power-law tag distribution: most pages have few tags, some have many
            num_tags = min(
                max(1, int(random.gauss(self.avg_tags, 2))),
                len(self.tag_pool),
            )
            tags = random.sample(self.tag_pool, num_tags)

            # 1-2 categories per page
            num_cats = random.randint(1, 2)
            categories = random.sample(self.category_pool, min(num_cats, len(self.category_pool)))

            page = SyntheticPage(
                title=f"Page {i}",
                source_path=Path(f"content/page-{i}.md"),
                tags=tags,
                categories=categories,
                metadata={},
            )
            self.pages.append(page)

    def _generate_links(self):
        """Generate internal links with power-law distribution."""
        for page in self.pages:
            # Power-law: most pages have few links, some hub pages have many
            if random.random() < 0.1:  # 10% are hub pages
                num_links = random.randint(self.avg_links * 2, self.avg_links * 5)
            else:
                num_links = max(0, int(random.gauss(self.avg_links, 2)))

            # Select random target pages (excluding self)
            possible_targets = [p for p in self.pages if p != page]
            if possible_targets and num_links > 0:
                num_links = min(num_links, len(possible_targets))
                targets = random.sample(possible_targets, num_links)
                page.links = [t.title for t in targets]

    def _build_xref_index(self) -> dict:
        """Build cross-reference index for link resolution."""
        by_slug = {}
        by_path = {}
        by_id = {}

        for page in self.pages:
            slug = page.title.lower().replace(" ", "-")
            by_slug[slug] = [page]
            by_path[str(page.source_path)] = page

        return {
            "by_slug": by_slug,
            "by_path": by_path,
            "by_id": by_id,
        }

    def get(self, key, default=None):
        """Dict-like access for config compatibility."""
        return self.config.get(key, default)


class MockKnowledgeGraph:
    """
    Mock KnowledgeGraph for testing analysis algorithms in isolation.

    Provides the same interface as KnowledgeGraph but with direct
    control over graph structure for benchmarking.
    """

    def __init__(self, site: SyntheticSite):
        self.site = site
        self._pages = site.pages
        self._pages_set = set(site.pages)

        # Graph data structures (populated by build())
        self.incoming_refs: dict[SyntheticPage, float] = {}
        self.outgoing_refs: dict[SyntheticPage, set[SyntheticPage]] = {}
        self.incoming_edges: dict[SyntheticPage, list[SyntheticPage]] = {}

        # Cached results
        self._pagerank_results = None
        self._path_results = None

    def get_analysis_pages(self) -> list[SyntheticPage]:
        """Return all pages for analysis."""
        return [p for p in self._pages if not p.metadata.get("_generated")]

    def build(self):
        """Build graph from synthetic site."""
        from collections import defaultdict

        self.incoming_refs = defaultdict(float)
        self.outgoing_refs = defaultdict(set)
        self.incoming_edges = defaultdict(list)

        # Build page lookup by title
        page_by_title = {p.title: p for p in self._pages}

        for page in self._pages:
            for link in page.links:
                target = page_by_title.get(link)
                if target and target != page:
                    self.incoming_refs[target] += 1
                    self.outgoing_refs[page].add(target)
                    # Build reverse index for optimized PageRank
                    self.incoming_edges[target].append(page)


# Fixtures for different site sizes
@pytest.fixture
def synthetic_100_site():
    """Generate a 100-page synthetic site."""
    return SyntheticSite(page_count=100, seed=42)


@pytest.fixture
def synthetic_1k_site():
    """Generate a 1,000-page synthetic site."""
    return SyntheticSite(page_count=1000, seed=42)


@pytest.fixture
def synthetic_5k_site():
    """Generate a 5,000-page synthetic site."""
    return SyntheticSite(page_count=5000, seed=42)


@pytest.fixture
def synthetic_10k_site():
    """Generate a 10,000-page synthetic site."""
    return SyntheticSite(page_count=10000, seed=42)


# Graph Build Benchmarks
@pytest.mark.benchmark(group="graph_build")
def test_graph_build_100_pages(benchmark, synthetic_100_site):
    """Benchmark graph construction for 100 pages."""
    graph = MockKnowledgeGraph(synthetic_100_site)

    def build_graph():
        graph.build()

    benchmark(build_graph)


@pytest.mark.benchmark(group="graph_build")
def test_graph_build_1k_pages(benchmark, synthetic_1k_site):
    """Benchmark graph construction for 1K pages."""
    graph = MockKnowledgeGraph(synthetic_1k_site)

    def build_graph():
        graph.build()

    benchmark(build_graph)


# PageRank Benchmarks
@pytest.mark.benchmark(group="pagerank")
def test_pagerank_100_pages(benchmark, synthetic_100_site):
    """Benchmark PageRank for 100 pages (baseline)."""
    from bengal.analysis.page_rank import PageRankCalculator

    graph = MockKnowledgeGraph(synthetic_100_site)
    graph.build()

    calculator = PageRankCalculator(graph, damping=0.85, max_iterations=50)

    def compute_pagerank():
        return calculator.compute()

    result = benchmark(compute_pagerank)
    assert result.converged or result.iterations == 50


@pytest.mark.benchmark(group="pagerank")
def test_pagerank_1k_pages(benchmark, synthetic_1k_site):
    """Benchmark PageRank for 1K pages."""
    from bengal.analysis.page_rank import PageRankCalculator

    graph = MockKnowledgeGraph(synthetic_1k_site)
    graph.build()

    calculator = PageRankCalculator(graph, damping=0.85, max_iterations=50)

    def compute_pagerank():
        return calculator.compute()

    result = benchmark(compute_pagerank)
    assert result.converged or result.iterations == 50


@pytest.mark.benchmark(group="pagerank")
@pytest.mark.slow
def test_pagerank_5k_pages(benchmark, synthetic_5k_site):
    """Benchmark PageRank for 5K pages (large site)."""
    from bengal.analysis.page_rank import PageRankCalculator

    graph = MockKnowledgeGraph(synthetic_5k_site)
    graph.build()

    calculator = PageRankCalculator(graph, damping=0.85, max_iterations=50)

    def compute_pagerank():
        return calculator.compute()

    result = benchmark(compute_pagerank)
    assert result.converged or result.iterations == 50


# Link Suggestions Benchmarks
@pytest.mark.benchmark(group="link_suggestions")
def test_link_suggestions_100_pages(benchmark, synthetic_100_site):
    """Benchmark link suggestions for 100 pages (baseline)."""
    from bengal.analysis.link_suggestions import LinkSuggestionEngine

    graph = MockKnowledgeGraph(synthetic_100_site)
    graph.build()

    engine = LinkSuggestionEngine(graph, min_score=0.2, max_suggestions_per_page=5)

    def generate_suggestions():
        return engine.generate_suggestions()

    result = benchmark(generate_suggestions)
    assert result.pages_analyzed == 100


@pytest.mark.benchmark(group="link_suggestions")
def test_link_suggestions_1k_pages(benchmark, synthetic_1k_site):
    """Benchmark link suggestions for 1K pages."""
    from bengal.analysis.link_suggestions import LinkSuggestionEngine

    graph = MockKnowledgeGraph(synthetic_1k_site)
    graph.build()

    engine = LinkSuggestionEngine(graph, min_score=0.2, max_suggestions_per_page=5)

    def generate_suggestions():
        return engine.generate_suggestions()

    result = benchmark(generate_suggestions)
    assert result.pages_analyzed == 1000


@pytest.mark.benchmark(group="link_suggestions")
@pytest.mark.slow
def test_link_suggestions_5k_pages(benchmark, synthetic_5k_site):
    """Benchmark link suggestions for 5K pages (large site)."""
    from bengal.analysis.link_suggestions import LinkSuggestionEngine

    graph = MockKnowledgeGraph(synthetic_5k_site)
    graph.build()

    engine = LinkSuggestionEngine(graph, min_score=0.2, max_suggestions_per_page=5)

    def generate_suggestions():
        return engine.generate_suggestions()

    result = benchmark(generate_suggestions)
    assert result.pages_analyzed == 5000


# Correctness Tests (non-benchmark)
def test_pagerank_correctness_after_optimization(synthetic_100_site):
    """
    Verify PageRank produces correct results after optimization.

    Compares against known properties:
    - Scores sum to approximately 1.0
    - Scores are positive
    - Highly-linked pages have higher scores
    """
    from bengal.analysis.page_rank import PageRankCalculator

    graph = MockKnowledgeGraph(synthetic_100_site)
    graph.build()

    calculator = PageRankCalculator(graph, damping=0.85, max_iterations=100)
    result = calculator.compute()

    # Verify convergence
    assert result.converged, f"PageRank did not converge in {result.iterations} iterations"

    # Verify score normalization (sum ≈ 1.0)
    total_score = sum(result.scores.values())
    assert abs(total_score - 1.0) < 0.01, f"Scores sum to {total_score}, expected ~1.0"

    # Verify all scores are positive
    assert all(s >= 0 for s in result.scores.values()), "Found negative PageRank scores"

    # Verify ranking makes sense: pages with more incoming links should rank higher
    top_pages = result.get_top_pages(10)
    for page, _score in top_pages[:5]:
        incoming = graph.incoming_refs.get(page, 0)
        # Top pages should have above-average incoming links
        avg_incoming = sum(graph.incoming_refs.values()) / len(graph.incoming_refs)
        assert incoming >= avg_incoming * 0.5, (
            f"Top page {page.title} has only {incoming} incoming links"
        )


def test_link_suggestions_correctness_after_optimization(synthetic_100_site):
    """
    Verify link suggestions are sensible after optimization.

    Checks:
    - Suggestions don't include self-links
    - Suggestions don't include existing links
    - Suggestions have valid scores and reasons
    """
    from bengal.analysis.link_suggestions import LinkSuggestionEngine

    graph = MockKnowledgeGraph(synthetic_100_site)
    graph.build()

    engine = LinkSuggestionEngine(graph, min_score=0.1, max_suggestions_per_page=5)
    result = engine.generate_suggestions()

    for suggestion in result.suggestions:
        # No self-links
        assert suggestion.source != suggestion.target, "Self-link found in suggestions"

        # No existing links
        existing = graph.outgoing_refs.get(suggestion.source, set())
        assert suggestion.target not in existing, (
            f"Existing link suggested: {suggestion.source.title} -> {suggestion.target.title}"
        )

        # Valid score
        assert 0 <= suggestion.score <= 2.0, f"Invalid score: {suggestion.score}"

        # Has reasons
        assert len(suggestion.reasons) > 0 or suggestion.score < 0.2, (
            "No reasons for high-score suggestion"
        )


# Combined benchmark for before/after comparison
@pytest.mark.benchmark(group="combined")
def test_full_analysis_pipeline_100_pages(benchmark, synthetic_100_site):
    """
    Benchmark complete analysis pipeline: build → pagerank → suggestions.

    This represents a realistic workflow where all analysis is performed.
    """
    from bengal.analysis.link_suggestions import LinkSuggestionEngine
    from bengal.analysis.page_rank import PageRankCalculator

    def full_pipeline():
        graph = MockKnowledgeGraph(synthetic_100_site)
        graph.build()

        calculator = PageRankCalculator(graph, damping=0.85, max_iterations=50)
        pagerank_result = calculator.compute()
        graph._pagerank_results = pagerank_result

        engine = LinkSuggestionEngine(graph, min_score=0.2, max_suggestions_per_page=5)
        suggestions = engine.generate_suggestions()

        return pagerank_result, suggestions

    results = benchmark(full_pipeline)
    pagerank_result, suggestions = results
    assert pagerank_result.converged or pagerank_result.iterations == 50
    assert suggestions.pages_analyzed == 100
