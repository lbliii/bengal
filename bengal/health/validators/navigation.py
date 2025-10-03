"""
Navigation validator - checks page navigation integrity.

Validates:
- next/prev chains work correctly
- Breadcrumb paths are valid
- Section navigation is consistent
- No broken navigation references
"""

from typing import List, TYPE_CHECKING, Set

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.core.page import Page


class NavigationValidator(BaseValidator):
    """
    Validates page navigation integrity.
    
    Checks:
    - next/prev links form valid chains
    - Breadcrumbs (ancestors) are valid
    - Section navigation is consistent
    - No orphaned pages in navigation
    """
    
    name = "Navigation"
    description = "Validates page navigation (next/prev, breadcrumbs, sections)"
    enabled_by_default = True
    
    def validate(self, site: 'Site') -> List[CheckResult]:
        """Run navigation validation checks."""
        results = []
        
        # Check 1: Next/prev chain integrity
        results.extend(self._check_next_prev_chains(site))
        
        # Check 2: Breadcrumb validity
        results.extend(self._check_breadcrumbs(site))
        
        # Check 3: Section navigation
        results.extend(self._check_section_navigation(site))
        
        # Check 4: Navigation coverage
        results.extend(self._check_navigation_coverage(site))
        
        return results
    
    def _check_next_prev_chains(self, site: 'Site') -> List[CheckResult]:
        """Check that next/prev links form valid chains."""
        results = []
        issues = []
        
        # Skip generated pages (they don't have next/prev in site collection)
        regular_pages = [p for p in site.pages if not p.metadata.get('_generated')]
        
        for page in regular_pages:
            # Check if next exists and points to valid page
            if hasattr(page, 'next') and page.next:
                if page.next not in site.pages:
                    issues.append(f"{page.source_path.name}: page.next points to non-existent page")
                elif not page.next.output_path or not page.next.output_path.exists():
                    issues.append(f"{page.source_path.name}: page.next points to page without output")
            
            # Check if prev exists and points to valid page
            if hasattr(page, 'prev') and page.prev:
                if page.prev not in site.pages:
                    issues.append(f"{page.source_path.name}: page.prev points to non-existent page")
                elif not page.prev.output_path or not page.prev.output_path.exists():
                    issues.append(f"{page.source_path.name}: page.prev points to page without output")
        
        if issues:
            results.append(CheckResult.error(
                f"{len(issues)} page(s) have broken next/prev links",
                recommendation="Check page navigation setup. This may indicate a bug in navigation system.",
                details=issues[:5]
            ))
        else:
            results.append(CheckResult.success(
                f"Next/prev navigation validated ({len(regular_pages)} pages)"
            ))
        
        return results
    
    def _check_breadcrumbs(self, site: 'Site') -> List[CheckResult]:
        """Check that breadcrumb trails (ancestors) are valid."""
        results = []
        issues = []
        
        for page in site.pages:
            # Skip pages without ancestors
            if not hasattr(page, 'ancestors') or not page.ancestors:
                continue
            
            # Check each ancestor in the breadcrumb trail
            for i, ancestor in enumerate(page.ancestors):
                # Verify ancestor is a valid page/section
                if not hasattr(ancestor, 'output_path'):
                    issues.append(f"{page.source_path.name}: ancestor {i} is not a valid page/section")
                    continue
                
                # Check if ancestor has output
                if ancestor.output_path and not ancestor.output_path.exists():
                    issues.append(f"{page.source_path.name}: ancestor '{ancestor.title}' has no output")
        
        if issues:
            results.append(CheckResult.warning(
                f"{len(issues)} page(s) have invalid breadcrumb trails",
                recommendation="Check section hierarchy and index pages.",
                details=issues[:5]
            ))
        else:
            pages_with_breadcrumbs = sum(1 for p in site.pages if hasattr(p, 'ancestors') and p.ancestors)
            results.append(CheckResult.success(
                f"Breadcrumbs validated ({pages_with_breadcrumbs} pages with breadcrumbs)"
            ))
        
        return results
    
    def _check_section_navigation(self, site: 'Site') -> List[CheckResult]:
        """Check section-level navigation consistency."""
        results = []
        issues = []
        
        for section in site.sections:
            # Check if section has an index page or generated archive
            has_index = section.index_page is not None
            has_archive = any(
                p.metadata.get('_generated') and 
                p.metadata.get('type') == 'archive' and
                p.metadata.get('_section') == section
                for p in site.pages
            )
            
            if not has_index and not has_archive and section.pages:
                issues.append(f"Section '{section.name}' has {len(section.pages)} pages but no index/archive")
            
            # Check if section pages have proper parent reference
            for page in section.pages:
                if hasattr(page, '_section') and page._section != section:
                    issues.append(f"Page {page.source_path.name} has wrong section reference")
        
        if issues:
            results.append(CheckResult.warning(
                f"{len(issues)} section navigation issue(s)",
                recommendation="Sections with pages should have an _index.md or auto-generated archive page.",
                details=issues[:5]
            ))
        else:
            results.append(CheckResult.success(
                f"Section navigation validated ({len(site.sections)} sections)"
            ))
        
        return results
    
    def _check_navigation_coverage(self, site: 'Site') -> List[CheckResult]:
        """Check how many pages are reachable through navigation."""
        results = []
        
        # Count pages with navigation features
        regular_pages = [p for p in site.pages if not p.metadata.get('_generated')]
        
        with_next_prev = sum(1 for p in regular_pages if (hasattr(p, 'next') and p.next) or (hasattr(p, 'prev') and p.prev))
        with_breadcrumbs = sum(1 for p in regular_pages if hasattr(p, 'ancestors') and p.ancestors)
        in_sections = sum(1 for p in regular_pages if hasattr(p, '_section') and p._section)
        
        # Calculate coverage
        total = len(regular_pages)
        if total > 0:
            next_prev_pct = (with_next_prev / total) * 100
            breadcrumb_pct = (with_breadcrumbs / total) * 100
            section_pct = (in_sections / total) * 100
            
            results.append(CheckResult.info(
                f"Navigation coverage: {next_prev_pct:.0f}% next/prev, {breadcrumb_pct:.0f}% breadcrumbs, {section_pct:.0f}% in sections",
                recommendation="High navigation coverage improves site usability." if next_prev_pct < 80 else None
            ))
        else:
            results.append(CheckResult.info("No regular pages to validate navigation coverage"))
        
        return results

