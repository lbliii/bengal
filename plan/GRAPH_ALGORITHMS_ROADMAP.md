# Graph Algorithms & Page Ranking - Implementation Roadmap

**Date:** October 9, 2025  
**Status:** Planning  
**Prerequisites:** ✅ Hashable Pages (completed)  
**Estimated Effort:** 12-15 hours  

---

## 🎯 Executive Summary

With hashable pages, we can now implement sophisticated graph algorithms to:
1. **PageRank** - Identify most important pages for optimization
2. **Community Detection** - Find natural content clusters
3. **Path Analysis** - Understand user navigation flows
4. **Influence Scoring** - Measure page impact on site

**Business Value:**
- 📊 Data-driven content strategy decisions
- 🎯 Optimize high-impact pages first
- 🗺️ Improve site structure and navigation
- 🔍 Better SEO through link analysis

---

## 📊 Use Cases

### 1. Content Strategy Dashboard
```python
from bengal.analysis import GraphAnalyzer

analyzer = GraphAnalyzer(site)
analyzer.build_graph()

# Which pages should we focus on?
top_pages = analyzer.get_top_ranked_pages(limit=20)
for page, score in top_pages:
    print(f"{page.title}: importance={score:.3f}")

# Which content clusters exist?
clusters = analyzer.find_communities()
print(f"Found {len(clusters)} natural content groups")
```

### 2. Build Optimization
```python
# Prioritize rendering high-impact pages first
important_pages = analyzer.get_pages_above_percentile(90)
site_config['render_priority'] = important_pages

# Stream low-impact pages to save memory
leaf_pages = analyzer.get_leaves()
site_config['stream_pages'] = leaf_pages
```

### 3. Navigation Improvements
```python
# Find poorly connected pages
isolated = analyzer.find_isolated_clusters()
print(f"⚠️  {len(isolated)} pages have weak connections")

# Suggest internal links
suggestions = analyzer.suggest_links(page, max_suggestions=5)
for target, relevance in suggestions:
    print(f"Consider linking to: {target.title} (relevance: {relevance:.2f})")
```

---

## 🏗️ Architecture Design

### Current State (Post-Hashability)

```
┌─────────────────────────────────────────────┐
│ KnowledgeGraph                               │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  - incoming_refs: Dict[Page, int]           │
│  - outgoing_refs: Dict[Page, Set[Page]]     │
│  - Hashable pages enable direct storage     │
│  - Basic metrics: hubs, leaves, orphans     │
└─────────────────────────────────────────────┘
                    ↓
         [Ready for algorithms]
```

### Proposed Architecture

```
┌──────────────────────────────────────────────────────────┐
│ GraphAnalyzer (new)                                       │
│ ════════════════════════════════════════════════════════ │
│  High-level analysis API                                 │
│  - build_graph()                                         │
│  - get_page_rank(method='standard|personalized')         │
│  - find_communities(algorithm='louvain|label_prop')      │
│  - suggest_links(page, strategy='content|structure')     │
│  - analyze_paths(start, end)                             │
└──────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────┐
│ PageRankCalculator (new)                                 │
│ ════════════════════════════════════════════════════════ │
│  Ranking algorithms                                      │
│  - standard_page_rank(damping=0.85, iterations=100)     │
│  - personalized_page_rank(seed_pages)                   │
│  - topic_sensitive_page_rank(topics)                    │
└──────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────┐
│ CommunityDetector (new)                                  │
│ ════════════════════════════════════════════════════════ │
│  Clustering algorithms                                   │
│  - louvain_method()       # Hierarchical communities    │
│  - label_propagation()    # Fast, good for large graphs │
│  - connected_components()  # Find isolated groups       │
└──────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────┐
│ PathAnalyzer (new)                                       │
│ ════════════════════════════════════════════════════════ │
│  Navigation analysis                                     │
│  - shortest_path(start, end)                            │
│  - all_paths(start, end, max_length=5)                  │
│  - bottleneck_pages()    # Pages in many paths          │
│  - dead_ends()           # Pages with no outgoing links │
└──────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────┐
│ LinkSuggester (new)                                      │
│ ════════════════════════════════════════════════════════ │
│  Content recommendations                                 │
│  - content_similarity(page1, page2)  # Tag/text based   │
│  - structural_similarity(page1, page2)  # Graph based   │
│  - suggest_internal_links(page)                         │
└──────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────┐
│ KnowledgeGraph (existing - enhanced)                     │
│ ════════════════════════════════════════════════════════ │
│  Foundation graph data structure                         │
│  - Uses hashable pages                                   │
│  - Provides base graph access                            │
└──────────────────────────────────────────────────────────┘
```

---

## 📋 Implementation Plan

### Phase 1: PageRank (4 hours)

**Goal:** Identify most important pages in the site graph.

#### 1.1: Core PageRank Algorithm (2 hours)

**New File:** `bengal/analysis/page_rank.py`

```python
"""
PageRank implementation for Bengal SSG.

Uses the iterative power method to compute page importance scores.
Takes advantage of hashable pages for efficient graph operations.
"""

from typing import Dict, Set, List, Tuple
from bengal.core.page import Page


class PageRankCalculator:
    """
    Compute PageRank scores for pages in a site graph.
    
    PageRank assigns importance scores based on:
    - Number of incoming links
    - Importance of pages linking to it
    - Damping factor (random jump probability)
    """
    
    def __init__(self, 
                 graph: 'KnowledgeGraph',
                 damping: float = 0.85,
                 max_iterations: int = 100,
                 convergence_threshold: float = 1e-6):
        """
        Initialize PageRank calculator.
        
        Args:
            graph: KnowledgeGraph with page connections
            damping: Probability of following links (vs random jump)
            max_iterations: Maximum iterations before stopping
            convergence_threshold: Stop when scores change less than this
        """
        self.graph = graph
        self.damping = damping
        self.max_iterations = max_iterations
        self.threshold = convergence_threshold
        
        # Results
        self.scores: Dict[Page, float] = {}
        self.iterations_run: int = 0
        self.converged: bool = False
    
    def compute(self) -> Dict[Page, float]:
        """
        Compute PageRank scores for all pages.
        
        Algorithm:
        1. Initialize all pages with score 1/N
        2. Iterate: score = (1-d)/N + d * Σ(incoming_score/outgoing_count)
        3. Stop when convergence or max iterations reached
        
        Returns:
            Dictionary mapping pages to their PageRank scores
        """
        pages = list(self.graph.site.pages)
        N = len(pages)
        
        if N == 0:
            return {}
        
        # Initialize: equal probability for all pages
        scores = {page: 1.0 / N for page in pages}
        
        for iteration in range(self.max_iterations):
            new_scores = {}
            max_diff = 0.0
            
            for page in pages:
                # Base score: random jump probability
                score = (1 - self.damping) / N
                
                # Add contributions from incoming links
                incoming = self.graph.incoming_refs.get(page, 0)
                if incoming > 0:
                    # Find pages linking to this one
                    for other_page in pages:
                        if page in self.graph.outgoing_refs.get(other_page, set()):
                            # Add proportional score from linking page
                            outgoing_count = len(self.graph.outgoing_refs.get(other_page, set()))
                            if outgoing_count > 0:
                                score += self.damping * (scores[other_page] / outgoing_count)
                
                new_scores[page] = score
                max_diff = max(max_diff, abs(score - scores[page]))
            
            scores = new_scores
            self.iterations_run = iteration + 1
            
            # Check convergence
            if max_diff < self.threshold:
                self.converged = True
                break
        
        self.scores = scores
        return scores
    
    def get_top_pages(self, limit: int = 20) -> List[Tuple[Page, float]]:
        """
        Get top-ranked pages by PageRank score.
        
        Args:
            limit: Number of top pages to return
        
        Returns:
            List of (page, score) tuples, sorted by score descending
        """
        if not self.scores:
            self.compute()
        
        sorted_pages = sorted(
            self.scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_pages[:limit]
    
    def get_pages_above_percentile(self, percentile: int) -> Set[Page]:
        """
        Get pages above a certain percentile in PageRank.
        
        Args:
            percentile: Percentile threshold (0-100)
        
        Returns:
            Set of pages above the threshold
        """
        if not self.scores:
            self.compute()
        
        scores_list = sorted(self.scores.values(), reverse=True)
        threshold_idx = int(len(scores_list) * (100 - percentile) / 100)
        threshold_score = scores_list[threshold_idx] if threshold_idx < len(scores_list) else 0
        
        return {page for page, score in self.scores.items() if score >= threshold_score}
```

**Tests:** `tests/unit/analysis/test_page_rank.py`

#### 1.2: Integration with KnowledgeGraph (1 hour)

**Update:** `bengal/analysis/knowledge_graph.py`

```python
class KnowledgeGraph:
    # ... existing code ...
    
    def compute_page_rank(self, **kwargs) -> Dict['Page', float]:
        """
        Compute PageRank scores for all pages.
        
        Args:
            **kwargs: Arguments passed to PageRankCalculator
        
        Returns:
            Dictionary mapping pages to PageRank scores
        """
        from bengal.analysis.page_rank import PageRankCalculator
        
        calculator = PageRankCalculator(self, **kwargs)
        return calculator.compute()
    
    def get_most_important_pages(self, limit: int = 20) -> List[Tuple['Page', float]]:
        """
        Get most important pages by PageRank.
        
        Args:
            limit: Number of pages to return
        
        Returns:
            List of (page, score) tuples
        """
        from bengal.analysis.page_rank import PageRankCalculator
        
        calculator = PageRankCalculator(self)
        calculator.compute()
        return calculator.get_top_pages(limit)
```

#### 1.3: CLI Integration (1 hour)

**Update:** `bengal/cli.py`

```python
@app.command()
def analyze(
    site_path: Path = typer.Argument(..., help="Path to site root"),
    metric: str = typer.Option("pagerank", help="Metric: pagerank, communities, paths"),
    output: Path = typer.Option(None, help="Output file (JSON/CSV)"),
    limit: int = typer.Option(20, help="Number of results to show")
):
    """
    Analyze site structure and content relationships.
    
    Examples:
        bengal analyze . --metric pagerank --limit 20
        bengal analyze . --metric communities --output clusters.json
    """
    # Load site
    site = load_site(site_path)
    
    # Build graph
    from bengal.analysis import KnowledgeGraph
    graph = KnowledgeGraph(site)
    graph.build()
    
    if metric == "pagerank":
        top_pages = graph.get_most_important_pages(limit)
        
        print(f"\n📊 Top {limit} Pages by Importance:\n")
        for i, (page, score) in enumerate(top_pages, 1):
            print(f"  {i}. {page.title:<50} Score: {score:.4f}")
        
        if output:
            save_results(output, top_pages)
```

---

### Phase 2: Community Detection (4 hours)

**Goal:** Find natural content clusters for better organization.

#### 2.1: Label Propagation Algorithm (2 hours)

**New File:** `bengal/analysis/community_detection.py`

```python
"""
Community detection algorithms for Bengal SSG.

Identifies natural clusters of related pages based on link structure.
"""

from typing import Dict, Set, List
from collections import defaultdict
import random

from bengal.core.page import Page


class CommunityDetector:
    """
    Detect communities (clusters) of related pages.
    
    Uses label propagation algorithm - fast and effective for large graphs.
    """
    
    def __init__(self, graph: 'KnowledgeGraph'):
        """
        Initialize community detector.
        
        Args:
            graph: KnowledgeGraph with page connections
        """
        self.graph = graph
        self.communities: Dict[Page, int] = {}
        self.community_sizes: Dict[int, int] = {}
    
    def detect_communities(self, max_iterations: int = 100) -> Dict[int, Set[Page]]:
        """
        Detect communities using label propagation.
        
        Algorithm:
        1. Assign each page a unique label
        2. Iterate: each page adopts most common label among neighbors
        3. Stop when labels stabilize or max iterations reached
        
        Returns:
            Dictionary mapping community ID to set of pages
        """
        pages = list(self.graph.site.pages)
        
        # Initialize: each page is its own community
        labels = {page: i for i, page in enumerate(pages)}
        
        for iteration in range(max_iterations):
            changed = False
            
            # Process pages in random order
            random.shuffle(pages)
            
            for page in pages:
                # Find neighbors
                neighbors = set()
                
                # Incoming links
                for other in pages:
                    if page in self.graph.outgoing_refs.get(other, set()):
                        neighbors.add(other)
                
                # Outgoing links
                neighbors.update(self.graph.outgoing_refs.get(page, set()))
                
                if not neighbors:
                    continue
                
                # Count neighbor labels
                label_counts = defaultdict(int)
                for neighbor in neighbors:
                    label_counts[labels[neighbor]] += 1
                
                # Adopt most common label
                most_common_label = max(label_counts.items(), key=lambda x: x[1])[0]
                
                if labels[page] != most_common_label:
                    labels[page] = most_common_label
                    changed = True
            
            if not changed:
                break
        
        # Group pages by community
        communities = defaultdict(set)
        for page, label in labels.items():
            communities[label].add(page)
        
        self.communities = labels
        self.community_sizes = {label: len(members) for label, members in communities.items()}
        
        return dict(communities)
    
    def get_page_community(self, page: Page) -> int:
        """Get community ID for a page."""
        return self.communities.get(page, -1)
    
    def get_community_summary(self) -> List[Dict]:
        """
        Get summary of detected communities.
        
        Returns:
            List of community info dicts
        """
        communities = self.detect_communities()
        
        summaries = []
        for community_id, members in sorted(communities.items(), key=lambda x: len(x[1]), reverse=True):
            # Find most common tags in community
            all_tags = []
            for page in members:
                all_tags.extend(page.tags)
            
            tag_counts = defaultdict(int)
            for tag in all_tags:
                tag_counts[tag] += 1
            
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            summaries.append({
                'community_id': community_id,
                'size': len(members),
                'pages': [p.title for p in list(members)[:5]],  # Sample pages
                'top_tags': [tag for tag, count in top_tags]
            })
        
        return summaries
```

#### 2.2: Visualization Support (1 hour)

**Update:** `bengal/analysis/graph_visualizer.py`

Add community coloring to graph visualizations.

#### 2.3: Integration & Tests (1 hour)

---

### Phase 3: Path Analysis (2 hours)

**Goal:** Understand navigation flows and identify bottlenecks.

**New File:** `bengal/analysis/path_analyzer.py`

```python
"""
Path analysis for Bengal SSG.

Analyzes navigation paths between pages to identify:
- Bottleneck pages (in many paths)
- Dead ends (no outgoing links)
- Optimal link placement
"""

from typing import List, Set, Dict, Tuple
from collections import deque

from bengal.core.page import Page


class PathAnalyzer:
    """Analyze navigation paths in the site graph."""
    
    def __init__(self, graph: 'KnowledgeGraph'):
        self.graph = graph
    
    def shortest_path(self, start: Page, end: Page) -> List[Page]:
        """
        Find shortest path between two pages using BFS.
        
        Args:
            start: Starting page
            end: Target page
        
        Returns:
            List of pages in path, or empty list if no path exists
        """
        if start == end:
            return [start]
        
        # BFS
        queue = deque([(start, [start])])
        visited = {start}
        
        while queue:
            current, path = queue.popleft()
            
            # Explore neighbors
            neighbors = self.graph.outgoing_refs.get(current, set())
            
            for neighbor in neighbors:
                if neighbor == end:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return []  # No path found
    
    def find_bottlenecks(self, sample_size: int = 100) -> List[Tuple[Page, int]]:
        """
        Find pages that appear in many shortest paths (bottlenecks).
        
        These pages are critical for navigation and should be optimized.
        
        Args:
            sample_size: Number of random page pairs to sample
        
        Returns:
            List of (page, path_count) tuples, sorted by frequency
        """
        import random
        
        pages = list(self.graph.site.pages)
        page_counts = defaultdict(int)
        
        # Sample random page pairs
        for _ in range(sample_size):
            start, end = random.sample(pages, 2)
            path = self.shortest_path(start, end)
            
            # Count pages in path (excluding start/end)
            for page in path[1:-1]:
                page_counts[page] += 1
        
        return sorted(page_counts.items(), key=lambda x: x[1], reverse=True)
    
    def find_dead_ends(self) -> List[Page]:
        """
        Find pages with no outgoing links (dead ends).
        
        These pages may benefit from suggested links.
        """
        dead_ends = []
        
        for page in self.graph.site.pages:
            outgoing = self.graph.outgoing_refs.get(page, set())
            if len(outgoing) == 0 and not page.metadata.get('_generated'):
                dead_ends.append(page)
        
        return dead_ends
```

---

### Phase 4: Link Suggestions (2 hours)

**Goal:** Recommend internal links to improve navigation.

**New File:** `bengal/analysis/link_suggester.py`

```python
"""
Link suggestion system for Bengal SSG.

Suggests internal links based on:
- Content similarity (tags, keywords)
- Structural similarity (graph position)
- Navigation optimization (fill gaps)
"""

from typing import List, Tuple, Set
from bengal.core.page import Page


class LinkSuggester:
    """Suggest internal links to improve site navigation."""
    
    def __init__(self, graph: 'KnowledgeGraph'):
        self.graph = graph
    
    def suggest_links(self, 
                     page: Page, 
                     max_suggestions: int = 5,
                     strategy: str = 'hybrid') -> List[Tuple[Page, float]]:
        """
        Suggest internal links for a page.
        
        Args:
            page: Page to suggest links for
            max_suggestions: Maximum suggestions to return
            strategy: 'content', 'structural', or 'hybrid'
        
        Returns:
            List of (target_page, relevance_score) tuples
        """
        if strategy == 'content':
            return self._content_based_suggestions(page, max_suggestions)
        elif strategy == 'structural':
            return self._structural_suggestions(page, max_suggestions)
        else:  # hybrid
            content_suggestions = self._content_based_suggestions(page, max_suggestions * 2)
            structural_suggestions = self._structural_suggestions(page, max_suggestions * 2)
            
            # Combine and re-rank
            all_suggestions = {}
            for target, score in content_suggestions:
                all_suggestions[target] = score * 0.6
            
            for target, score in structural_suggestions:
                all_suggestions[target] = all_suggestions.get(target, 0) + score * 0.4
            
            sorted_suggestions = sorted(
                all_suggestions.items(),
                key=lambda x: x[1],
                reverse=True
            )
            return sorted_suggestions[:max_suggestions]
    
    def _content_based_suggestions(self, page: Page, limit: int) -> List[Tuple[Page, float]]:
        """Suggest links based on content similarity (tags)."""
        page_tags = set(page.tags)
        
        if not page_tags:
            return []
        
        # Already linked to
        existing_links = self.graph.outgoing_refs.get(page, set())
        
        scores = []
        for other_page in self.graph.site.pages:
            if other_page == page or other_page in existing_links:
                continue
            
            if other_page.metadata.get('_generated'):
                continue
            
            # Calculate Jaccard similarity
            other_tags = set(other_page.tags)
            if not other_tags:
                continue
            
            intersection = len(page_tags & other_tags)
            union = len(page_tags | other_tags)
            similarity = intersection / union if union > 0 else 0
            
            if similarity > 0:
                scores.append((other_page, similarity))
        
        return sorted(scores, key=lambda x: x[1], reverse=True)[:limit]
    
    def _structural_suggestions(self, page: Page, limit: int) -> List[Tuple[Page, float]]:
        """Suggest links based on graph structure."""
        # Suggest pages that:
        # 1. Are linked by pages we link to (common out-neighbors)
        # 2. Have high PageRank
        # 3. Are in the same community
        
        # For now, simple implementation: pages linked by our outgoing links
        existing_links = self.graph.outgoing_refs.get(page, set())
        
        candidate_scores = {}
        for neighbor in existing_links:
            neighbor_links = self.graph.outgoing_refs.get(neighbor, set())
            for candidate in neighbor_links:
                if candidate != page and candidate not in existing_links:
                    candidate_scores[candidate] = candidate_scores.get(candidate, 0) + 1
        
        # Normalize scores
        max_score = max(candidate_scores.values()) if candidate_scores else 1
        normalized = [(page, score / max_score) for page, score in candidate_scores.items()]
        
        return sorted(normalized, key=lambda x: x[1], reverse=True)[:limit]
```

---

## 🧪 Testing Strategy

### Unit Tests
- `test_page_rank.py` - PageRank algorithm correctness
- `test_community_detection.py` - Community detection accuracy
- `test_path_analyzer.py` - Path finding correctness
- `test_link_suggester.py` - Suggestion quality

### Integration Tests
- Test with real site graphs (showcase example)
- Performance tests with large graphs (4K+ pages)
- Consistency tests across multiple runs

### Validation
- Compare results with known graph theory results
- Manual review of top-ranked pages
- Community coherence metrics

---

## 📈 Success Metrics

**Performance:**
- PageRank: < 1s for 1K pages, < 10s for 10K pages
- Community detection: < 2s for 1K pages
- Path analysis: < 100ms per query

**Quality:**
- PageRank: Correlates with manual importance ratings
- Communities: High modularity score (> 0.3)
- Link suggestions: > 60% acceptance rate

**Usability:**
- CLI integration for easy access
- JSON/CSV export for analysis
- Clear documentation and examples

---

## 🚀 Future Enhancements

- **Temporal analysis**: Track importance changes over time
- **Personalized ranking**: Based on user segments
- **Topic-sensitive ranking**: Different rankings per topic
- **Link prediction**: ML-based link suggestions
- **Graph embeddings**: Neural network page representations

---

## 📚 References

- PageRank: Brin & Page (1998)
- Label Propagation: Raghavan et al. (2007)
- Graph Algorithms: Cormen et al. (CLRS)
- NetworkX: Python graph library (for validation)

