# Advanced Analysis Tools - Implementation Roadmap

**Date:** October 9, 2025  
**Status:** Planning  
**Prerequisites:** ✅ Hashable Pages (completed), Graph Algorithms (planned)  
**Estimated Effort:** 10-12 hours  

---

## 🎯 Executive Summary

Build a comprehensive analytics suite for Bengal SSG that provides actionable insights about site structure, content quality, and user experience.

**Tools:**
1. **Site Health Dashboard** - Visual overview of site quality
2. **Content Gap Analysis** - Find missing topics and links
3. **SEO Recommendations** - Data-driven optimization suggestions
4. **Build Analytics** - Track and optimize build performance
5. **Content Lifecycle Tracking** - Monitor freshness and staleness

**Business Value:**
- 📊 Data-driven content decisions
- 🎯 Identify high-ROI improvements
- 🔍 Automated SEO audits
- ⚡ Continuous performance monitoring
- 📈 Track site growth over time

---

## 🛠️ Tool Suite Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ AnalyticsDashboard                                           │
│ ═══════════════════════════════════════════════════════════ │
│  Main entry point for all analytics                         │
│  - generate_dashboard()                                      │
│  - export_report(format='html|json|pdf')                    │
│  - track_over_time()                                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
        ┌─────────────────────┴─────────────────────┐
        ↓                     ↓                     ↓
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ SiteHealth   │    │ ContentGap   │    │ SEOAnalyzer  │
│ Analyzer     │    │ Analyzer     │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
        ↓                     ↓                     ↓
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ BuildPerf    │    │ ContentLife  │    │ LinkAnalyzer │
│ Tracker      │    │ Tracker      │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
```

---

## 📋 Tool #1: Site Health Dashboard

### Overview

Comprehensive visual dashboard showing site quality metrics.

### Metrics Tracked

```python
@dataclass
class SiteHealthMetrics:
    """Overall site health metrics."""
    
    # Content Quality
    total_pages: int
    average_word_count: float
    pages_below_word_threshold: int  # < 300 words
    pages_with_no_tags: int
    orphaned_pages: int  # No incoming links
    
    # Navigation
    average_links_per_page: float
    dead_end_pages: int  # No outgoing links
    broken_internal_links: int
    navigation_depth: float  # Avg clicks from home
    
    # Structure
    community_count: int  # Content clusters
    modularity_score: float  # How well-clustered
    hub_page_count: int
    leaf_page_count: int
    
    # SEO
    pages_missing_description: int
    pages_missing_title: int
    duplicate_titles: int
    pages_with_long_urls: int
    
    # Freshness
    pages_not_updated_1year: int
    average_content_age_days: float
    stale_content_ratio: float
    
    # Overall Score
    health_score: float  # 0-100
```

### Implementation

**New File:** `bengal/analysis/site_health.py`

```python
"""
Site health analyzer for Bengal SSG.

Provides comprehensive health metrics and recommendations.
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from bengal.core.site import Site
from bengal.core.page import Page
from bengal.analysis.knowledge_graph import KnowledgeGraph


@dataclass
class HealthIssue:
    """An identified health issue."""
    severity: str  # 'critical', 'warning', 'info'
    category: str  # 'content', 'navigation', 'seo', etc.
    title: str
    description: str
    affected_pages: List[Page]
    recommendation: str


class SiteHealthAnalyzer:
    """
    Analyze overall site health.
    
    Provides:
    - Health score (0-100)
    - Categorized issues
    - Actionable recommendations
    - Trend tracking
    """
    
    def __init__(self, site: Site):
        self.site = site
        self.graph = KnowledgeGraph(site)
        self.graph.build()
        
        self.metrics = None
        self.issues: List[HealthIssue] = []
    
    def analyze(self) -> SiteHealthMetrics:
        """
        Perform comprehensive site health analysis.
        
        Returns:
            SiteHealthMetrics with all computed values
        """
        self.issues = []
        
        # Content quality checks
        content_metrics = self._analyze_content_quality()
        
        # Navigation checks
        nav_metrics = self._analyze_navigation()
        
        # Structure checks
        structure_metrics = self._analyze_structure()
        
        # SEO checks
        seo_metrics = self._analyze_seo()
        
        # Freshness checks
        freshness_metrics = self._analyze_freshness()
        
        # Compute overall health score
        health_score = self._compute_health_score(
            content_metrics,
            nav_metrics,
            structure_metrics,
            seo_metrics,
            freshness_metrics
        )
        
        self.metrics = SiteHealthMetrics(
            **content_metrics,
            **nav_metrics,
            **structure_metrics,
            **seo_metrics,
            **freshness_metrics,
            health_score=health_score
        )
        
        return self.metrics
    
    def _analyze_content_quality(self) -> Dict:
        """Analyze content quality metrics."""
        word_counts = []
        no_tags = []
        short_content = []
        
        for page in self.site.pages:
            if page.metadata.get('_generated'):
                continue
            
            # Word count
            word_count = len(page.content.split()) if page.content else 0
            word_counts.append(word_count)
            
            if word_count < 300:
                short_content.append(page)
            
            # Tags
            if not page.tags:
                no_tags.append(page)
        
        # Create issues
        if short_content:
            self.issues.append(HealthIssue(
                severity='warning',
                category='content',
                title='Short Content',
                description=f'{len(short_content)} pages have less than 300 words',
                affected_pages=short_content[:10],
                recommendation='Add more detailed content to improve SEO and user value'
            ))
        
        if no_tags:
            self.issues.append(HealthIssue(
                severity='warning',
                category='content',
                title='Missing Tags',
                description=f'{len(no_tags)} pages have no tags',
                affected_pages=no_tags[:10],
                recommendation='Add tags to improve discoverability and related posts'
            ))
        
        return {
            'total_pages': len([p for p in self.site.pages if not p.metadata.get('_generated')]),
            'average_word_count': sum(word_counts) / len(word_counts) if word_counts else 0,
            'pages_below_word_threshold': len(short_content),
            'pages_with_no_tags': len(no_tags)
        }
    
    def _analyze_navigation(self) -> Dict:
        """Analyze navigation structure."""
        total_links = 0
        dead_ends = []
        orphans = self.graph.get_orphans()
        
        for page in self.site.pages:
            if page.metadata.get('_generated'):
                continue
            
            outgoing = len(self.graph.outgoing_refs.get(page, set()))
            total_links += outgoing
            
            if outgoing == 0:
                dead_ends.append(page)
        
        regular_pages = [p for p in self.site.pages if not p.metadata.get('_generated')]
        avg_links = total_links / len(regular_pages) if regular_pages else 0
        
        # Create issues
        if orphans:
            self.issues.append(HealthIssue(
                severity='critical',
                category='navigation',
                title='Orphaned Pages',
                description=f'{len(orphans)} pages have no incoming links',
                affected_pages=orphans[:10],
                recommendation='Add internal links to these pages from related content'
            ))
        
        if dead_ends:
            self.issues.append(HealthIssue(
                severity='warning',
                category='navigation',
                title='Dead End Pages',
                description=f'{len(dead_ends)} pages have no outgoing links',
                affected_pages=dead_ends[:10],
                recommendation='Add "See Also" or "Related" sections with internal links'
            ))
        
        return {
            'average_links_per_page': avg_links,
            'dead_end_pages': len(dead_ends),
            'orphaned_pages': len(orphans),
            'broken_internal_links': 0  # TODO: implement link validation
        }
    
    def _analyze_structure(self) -> Dict:
        """Analyze site structure."""
        from bengal.analysis.community_detection import CommunityDetector
        
        detector = CommunityDetector(self.graph)
        communities = detector.detect_communities()
        
        hubs = self.graph.get_hubs()
        leaves = self.graph.get_leaves()
        
        # Calculate modularity (measure of clustering quality)
        modularity = self._calculate_modularity(communities)
        
        return {
            'community_count': len(communities),
            'modularity_score': modularity,
            'hub_page_count': len(hubs),
            'leaf_page_count': len(leaves)
        }
    
    def _analyze_seo(self) -> Dict:
        """Analyze SEO factors."""
        missing_description = []
        missing_title = []
        long_urls = []
        
        titles_seen = {}
        
        for page in self.site.pages:
            if page.metadata.get('_generated'):
                continue
            
            # Description
            if not page.description:
                missing_description.append(page)
            
            # Title
            title = page.metadata.get('title', '')
            if not title:
                missing_title.append(page)
            else:
                if title in titles_seen:
                    titles_seen[title].append(page)
                else:
                    titles_seen[title] = [page]
            
            # URL length
            if page.output_path:
                url = str(page.output_path)
                if len(url) > 100:
                    long_urls.append(page)
        
        # Find duplicates
        duplicate_titles = {title: pages for title, pages in titles_seen.items() if len(pages) > 1}
        
        # Create issues
        if missing_description:
            self.issues.append(HealthIssue(
                severity='warning',
                category='seo',
                title='Missing Meta Descriptions',
                description=f'{len(missing_description)} pages lack meta descriptions',
                affected_pages=missing_description[:10],
                recommendation='Add description field to frontmatter for better search visibility'
            ))
        
        if duplicate_titles:
            self.issues.append(HealthIssue(
                severity='warning',
                category='seo',
                title='Duplicate Titles',
                description=f'{len(duplicate_titles)} titles are used multiple times',
                affected_pages=[],
                recommendation='Ensure each page has a unique, descriptive title'
            ))
        
        return {
            'pages_missing_description': len(missing_description),
            'pages_missing_title': len(missing_title),
            'duplicate_titles': len(duplicate_titles),
            'pages_with_long_urls': len(long_urls)
        }
    
    def _analyze_freshness(self) -> Dict:
        """Analyze content freshness."""
        now = datetime.now()
        one_year_ago = now - timedelta(days=365)
        
        stale_pages = []
        ages = []
        
        for page in self.site.pages:
            if page.metadata.get('_generated'):
                continue
            
            date = page.date
            if date:
                age_days = (now - date).days
                ages.append(age_days)
                
                if date < one_year_ago:
                    stale_pages.append(page)
        
        avg_age = sum(ages) / len(ages) if ages else 0
        stale_ratio = len(stale_pages) / len(ages) if ages else 0
        
        if stale_pages and stale_ratio > 0.3:
            self.issues.append(HealthIssue(
                severity='info',
                category='freshness',
                title='Stale Content',
                description=f'{len(stale_pages)} pages not updated in over a year',
                affected_pages=stale_pages[:10],
                recommendation='Review and update old content or add "last updated" dates'
            ))
        
        return {
            'pages_not_updated_1year': len(stale_pages),
            'average_content_age_days': avg_age,
            'stale_content_ratio': stale_ratio
        }
    
    def _compute_health_score(self, *metric_dicts) -> float:
        """
        Compute overall health score (0-100).
        
        Weighted combination of all metrics.
        """
        score = 100.0
        
        # Deduct points for issues
        for issue in self.issues:
            if issue.severity == 'critical':
                score -= 10
            elif issue.severity == 'warning':
                score -= 5
            elif issue.severity == 'info':
                score -= 2
        
        return max(0, min(100, score))
    
    def generate_report(self, format: str = 'html') -> str:
        """
        Generate health report.
        
        Args:
            format: 'html', 'markdown', or 'json'
        
        Returns:
            Formatted report string
        """
        if not self.metrics:
            self.analyze()
        
        if format == 'html':
            return self._generate_html_report()
        elif format == 'markdown':
            return self._generate_markdown_report()
        else:
            return self._generate_json_report()
    
    def _generate_markdown_report(self) -> str:
        """Generate Markdown report."""
        lines = [
            "# Site Health Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Health Score:** {self.metrics.health_score:.1f}/100",
            "",
            "## Summary",
            "",
            f"- **Total Pages:** {self.metrics.total_pages}",
            f"- **Average Word Count:** {self.metrics.average_word_count:.0f}",
            f"- **Orphaned Pages:** {self.metrics.orphaned_pages}",
            f"- **Community Count:** {self.metrics.community_count}",
            "",
            "## Issues",
            ""
        ]
        
        # Group issues by severity
        critical = [i for i in self.issues if i.severity == 'critical']
        warnings = [i for i in self.issues if i.severity == 'warning']
        info = [i for i in self.issues if i.severity == 'info']
        
        if critical:
            lines.append("### 🔴 Critical Issues")
            lines.append("")
            for issue in critical:
                lines.append(f"#### {issue.title}")
                lines.append(f"{issue.description}")
                lines.append(f"**Recommendation:** {issue.recommendation}")
                lines.append("")
        
        if warnings:
            lines.append("### ⚠️ Warnings")
            lines.append("")
            for issue in warnings:
                lines.append(f"#### {issue.title}")
                lines.append(f"{issue.description}")
                lines.append(f"**Recommendation:** {issue.recommendation}")
                lines.append("")
        
        if info:
            lines.append("### ℹ️ Info")
            lines.append("")
            for issue in info:
                lines.append(f"#### {issue.title}")
                lines.append(f"{issue.description}")
                lines.append("")
        
        return "\n".join(lines)
```

### Dashboard Visualization

**New File:** `bengal/analysis/dashboard_generator.py`

Generate beautiful HTML dashboards with charts using Chart.js or similar.

---

## 📋 Tool #2: Content Gap Analysis

### Overview

Identify missing topics, underrepresented areas, and link opportunities.

### Features

```python
class ContentGapAnalyzer:
    """
    Find gaps in content coverage.
    
    Identifies:
    - Topics mentioned but not covered
    - Weak content clusters
    - Missing connections between related topics
    - Underrepresented tags
    """
    
    def find_missing_topics(self) -> List[Tuple[str, int]]:
        """
        Find topics mentioned in content but not as main topics.
        
        Returns:
            List of (topic, mention_count) tuples
        """
        # Extract all mentioned terms from content
        # Compare with existing page topics
        # Return frequently mentioned but uncovered topics
    
    def find_weak_clusters(self) -> List[Dict]:
        """
        Find content clusters with few pages.
        
        These might need more content or better organization.
        """
    
    def suggest_hub_pages(self) -> List[Dict]:
        """
        Suggest topics that would benefit from hub pages.
        
        Based on:
        - Multiple pages on similar topics
        - No clear hub page exists
        - High link potential
        """
```

---

## 📋 Tool #3: SEO Analyzer

### Overview

Automated SEO audit and recommendations.

### Checks

- Title optimization
- Meta description quality
- Heading structure (H1-H6)
- Image alt tags
- Internal linking
- URL structure
- Mobile-friendliness indicators
- Page speed indicators

---

## 📋 Tool #4: Build Performance Tracker

### Overview

Track and optimize build performance over time.

### Metrics

```python
@dataclass
class BuildPerformanceMetrics:
    """Build performance tracking."""
    
    # Timing
    total_build_time_ms: float
    discovery_time_ms: float
    parsing_time_ms: float
    rendering_time_ms: float
    writing_time_ms: float
    
    # Throughput
    pages_per_second: float
    mb_per_second: float
    
    # Resources
    peak_memory_mb: float
    cpu_percent: float
    disk_io_mb: float
    
    # Cache
    cache_hit_rate: float
    incremental_skip_rate: float
```

### Features

- Performance regression detection
- Bottleneck identification
- Optimization suggestions
- Trend analysis over time

---

## 📋 Tool #5: Content Lifecycle Tracker

### Overview

Monitor content age, updates, and lifecycle stages.

### Features

```python
class ContentLifecycleTracker:
    """
    Track content through its lifecycle.
    
    Stages:
    - New (< 30 days)
    - Active (30-180 days, regular updates)
    - Stable (180-365 days, occasional updates)
    - Aging (1-2 years, rare updates)
    - Stale (> 2 years, no updates)
    """
    
    def classify_pages(self) -> Dict[str, List[Page]]:
        """Classify pages by lifecycle stage."""
    
    def find_update_candidates(self) -> List[Page]:
        """Find pages that should be updated."""
    
    def track_content_velocity(self) -> Dict:
        """Track rate of content creation/updates."""
```

---

## 🎨 CLI Integration

```bash
# Generate site health dashboard
bengal analyze health --output health-report.html

# Find content gaps
bengal analyze gaps --format markdown > gaps.md

# SEO audit
bengal analyze seo --detailed

# Track build performance
bengal analyze perf --compare-with last-week

# Content lifecycle
bengal analyze lifecycle --show stale --limit 20
```

---

## 📊 Dashboard Features

### Interactive HTML Dashboard

- **Overview**: Health score, key metrics
- **Charts**: Trend lines, distribution graphs
- **Issues List**: Sortable, filterable
- **Page Explorer**: Drill down into specific pages
- **Recommendations**: Prioritized action items
- **Export**: PDF, JSON, CSV

### Example Dashboard Sections

```html
<!-- Health Score -->
<div class="score-card">
    <h2>Health Score</h2>
    <div class="score">87/100</div>
    <div class="trend">+5 from last week</div>
</div>

<!-- Content Quality -->
<div class="metric-card">
    <h3>Content Quality</h3>
    <div class="chart" id="content-quality-chart"></div>
    <ul>
        <li>Average: 1,250 words</li>
        <li>15 pages below threshold</li>
        <li>23 pages missing tags</li>
    </ul>
</div>

<!-- Issues -->
<div class="issues-panel">
    <h3>Critical Issues (3)</h3>
    <div class="issue">
        <span class="badge critical">CRITICAL</span>
        <strong>12 Orphaned Pages</strong>
        <p>These pages have no incoming links...</p>
        <button>View Pages</button>
    </div>
</div>
```

---

## 📈 Success Metrics

**Adoption:**
- 80%+ of sites run analysis monthly
- Average of 5 issues fixed per analysis

**Impact:**
- 20%+ improvement in health scores
- 30%+ reduction in orphaned pages
- 50%+ increase in internal links

**Performance:**
- Analysis completes in < 30s for 10K pages
- Dashboard loads in < 2s

---

## 🚀 Implementation Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| 1. Site Health | 3 hours | Core analyzer, basic metrics |
| 2. Dashboard | 2 hours | HTML report generation |
| 3. Content Gaps | 2 hours | Gap analysis algorithms |
| 4. SEO Analyzer | 2 hours | SEO checks and recommendations |
| 5. Build Perf | 1 hour | Performance tracking |
| 6. Lifecycle | 1 hour | Content age analysis |
| 7. CLI | 1 hour | Command integration |
| **Total** | **12 hours** | Complete analytics suite |

---

## 📚 Future Enhancements

- **ML-based recommendations**: Learn from successful sites
- **A/B testing support**: Track content experiments
- **User analytics integration**: Combine with Google Analytics
- **Competitive analysis**: Compare with similar sites
- **Auto-fix**: Automatically fix simple issues
- **Scheduled reports**: Email weekly health reports
- **Slack/Discord integration**: Alert on critical issues

---

## 🎯 Quick Wins

**Week 1:**
- Basic health analyzer
- Markdown reports
- CLI integration

**Week 2:**
- HTML dashboard
- Content gap analysis

**Week 3:**
- SEO analyzer
- Performance tracking

**Week 4:**
- Polish, documentation, examples

