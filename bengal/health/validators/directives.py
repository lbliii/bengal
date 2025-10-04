"""
Directive validator - checks directive syntax, usage, and performance.

Validates:
- Directive syntax is well-formed
- Required directive options present
- Tab markers properly formatted
- Nesting depth reasonable
- Performance warnings for directive-heavy pages
"""

import re
from typing import List, Dict, Any, Tuple, Optional, TYPE_CHECKING
from pathlib import Path
from collections import defaultdict

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.core.page import Page


class DirectiveValidator(BaseValidator):
    """
    Validates directive syntax and usage across the site.
    
    Checks:
    - Directive blocks are well-formed (opening and closing)
    - Required options are present
    - Tab markers are properly formatted
    - Nesting depth is reasonable
    - Performance warnings for heavy directive usage
    """
    
    name = "Directives"
    description = "Validates directive syntax, completeness, and performance"
    enabled_by_default = True
    
    # Directive types we know about
    KNOWN_DIRECTIVES = {
        'tabs', 'note', 'tip', 'warning', 'danger', 'error', 
        'info', 'example', 'success', 'caution', 'dropdown', 
        'details', 'code-tabs', 'code_tabs'
    }
    
    # Performance thresholds
    MAX_DIRECTIVES_PER_PAGE = 10  # Warn if page has more than this
    MAX_NESTING_DEPTH = 5  # Warn if nesting deeper than this
    MAX_TABS_PER_BLOCK = 10  # Warn if single tabs block has more than this
    
    def validate(self, site: 'Site') -> List[CheckResult]:
        """Run directive validation checks."""
        results = []
        
        # Gather all directive data from source files
        directive_data = self._analyze_directives(site)
        
        # Check 1: Syntax validation
        results.extend(self._check_directive_syntax(directive_data))
        
        # Check 2: Completeness validation
        results.extend(self._check_directive_completeness(directive_data))
        
        # Check 3: Performance warnings
        results.extend(self._check_directive_performance(directive_data))
        
        # Check 4: Rendering validation (check output HTML)
        results.extend(self._check_directive_rendering(site, directive_data))
        
        return results
    
    def _analyze_directives(self, site: 'Site') -> Dict[str, Any]:
        """
        Analyze all directives in site source files.
        
        Returns:
            Dictionary with directive statistics and issues
        """
        data = {
            'total_directives': 0,
            'by_type': defaultdict(int),
            'by_page': defaultdict(list),
            'syntax_errors': [],
            'completeness_errors': [],
            'performance_warnings': [],
            'fence_nesting_warnings': [],
        }
        
        # Analyze each page's source content
        for page in site.pages:
            if not page.source_path or not page.source_path.exists():
                continue
            
            # Skip generated pages (they don't have markdown source)
            if page.metadata.get('_generated'):
                continue
            
            try:
                content = page.source_path.read_text(encoding='utf-8')
                page_directives = self._extract_directives(content, page.source_path)
                
                for directive in page_directives:
                    data['total_directives'] += 1
                    data['by_type'][directive['type']] += 1
                    data['by_page'][str(page.source_path)].append(directive)
                    
                    # Check for syntax errors
                    if directive.get('syntax_error'):
                        data['syntax_errors'].append({
                            'page': page.source_path,
                            'line': directive['line_number'],
                            'type': directive['type'],
                            'error': directive['syntax_error']
                        })
                    
                    # Check for completeness errors
                    if directive.get('completeness_error'):
                        data['completeness_errors'].append({
                            'page': page.source_path,
                            'line': directive['line_number'],
                            'type': directive['type'],
                            'error': directive['completeness_error']
                        })
                    
                    # Check for fence nesting warnings
                    if directive.get('fence_nesting_warning'):
                        data['fence_nesting_warnings'].append({
                            'page': page.source_path,
                            'line': directive['line_number'],
                            'type': directive['type'],
                            'warning': directive['fence_nesting_warning']
                        })
                    
            except Exception as e:
                # Skip files we can't read
                pass
        
        # Check for performance issues
        for page_path, directives in data['by_page'].items():
            # Too many directives on one page?
            if len(directives) > self.MAX_DIRECTIVES_PER_PAGE:
                data['performance_warnings'].append({
                    'page': Path(page_path),
                    'issue': 'heavy_directive_usage',
                    'count': len(directives),
                    'message': f'{len(directives)} directives on one page (>{self.MAX_DIRECTIVES_PER_PAGE})'
                })
            
            # Check individual directive issues
            for directive in directives:
                # Too many tabs in a tabs block?
                if directive['type'] == 'tabs' and directive.get('tab_count', 0) > self.MAX_TABS_PER_BLOCK:
                    data['performance_warnings'].append({
                        'page': Path(page_path),
                        'issue': 'too_many_tabs',
                        'line': directive['line_number'],
                        'count': directive['tab_count'],
                        'message': f'Tabs block has {directive["tab_count"]} tabs (>{self.MAX_TABS_PER_BLOCK})'
                    })
        
        return data
    
    def _extract_directives(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        """
        Extract all directive blocks from markdown content.
        
        Args:
            content: Markdown content
            file_path: Path to file (for error reporting)
            
        Returns:
            List of directive dictionaries with metadata
        """
        directives = []
        
        # Pattern: `{3,}\{directive_type} optional_title
        #          :option: value
        #          
        #          content
        #          `{3,}
        # Capture fence markers to detect nesting issues
        pattern = r'(`{3,})\{(\w+(?:-\w+)?)\}([^\n]*)\n(.*?)\1'
        
        lines = content.split('\n')
        
        for match in re.finditer(pattern, content, re.DOTALL):
            fence_marker = match.group(1)  # e.g., ``` or ````
            directive_type = match.group(2)
            title = match.group(3).strip()
            directive_content = match.group(4)
            
            # Find line number
            start_pos = match.start()
            line_number = content[:start_pos].count('\n') + 1
            
            directive_info = {
                'type': directive_type,
                'title': title,
                'content': directive_content,
                'line_number': line_number,
                'file_path': file_path,
                'fence_depth': len(fence_marker),  # Track fence depth
            }
            
            # Check for fence nesting issues
            self._check_fence_nesting(directive_info)
            
            # Check if directive type is known
            if directive_type not in self.KNOWN_DIRECTIVES:
                directive_info['syntax_error'] = f'Unknown directive type: {directive_type}'
            
            # Validate specific directive types
            if directive_type == 'tabs':
                self._validate_tabs_directive(directive_info)
            elif directive_type in ('code-tabs', 'code_tabs'):
                self._validate_code_tabs_directive(directive_info)
            elif directive_type in ('dropdown', 'details'):
                self._validate_dropdown_directive(directive_info)
            
            directives.append(directive_info)
        
        return directives
    
    def _validate_tabs_directive(self, directive: Dict[str, Any]) -> None:
        """Validate tabs directive content."""
        content = directive['content']
        
        # Check for tab markers: ### Tab: Title
        tab_markers = re.findall(r'^### Tab: (.+)$', content, re.MULTILINE)
        directive['tab_count'] = len(tab_markers)
        
        if len(tab_markers) == 0:
            # Check if there's a malformed marker
            bad_markers = re.findall(r'^###\s*Ta[^b]', content, re.MULTILINE)
            if bad_markers:
                directive['syntax_error'] = f'Malformed tab marker (use "### Tab: Title")'
            else:
                # Single tab or no tabs - might be intentional, just note it
                directive['completeness_error'] = 'Tabs directive has no tab markers (### Tab: Title)'
        elif len(tab_markers) == 1:
            directive['completeness_error'] = 'Tabs directive has only 1 tab (consider using admonition instead)'
        
        # Check if content is empty
        if not content.strip():
            directive['completeness_error'] = 'Tabs directive has no content'
    
    def _validate_code_tabs_directive(self, directive: Dict[str, Any]) -> None:
        """Validate code-tabs directive content."""
        content = directive['content']
        
        # Check for tab markers
        tab_markers = re.findall(r'^### Tab: (.+)$', content, re.MULTILINE)
        directive['tab_count'] = len(tab_markers)
        
        if len(tab_markers) == 0:
            directive['completeness_error'] = 'Code-tabs directive has no tab markers (### Tab: Language)'
        
        # Check if content is empty
        if not content.strip():
            directive['completeness_error'] = 'Code-tabs directive has no content'
    
    def _validate_dropdown_directive(self, directive: Dict[str, Any]) -> None:
        """Validate dropdown directive content."""
        content = directive['content']
        
        # Check if content is empty
        if not content.strip():
            directive['completeness_error'] = 'Dropdown directive has no content'
        
        # Check if title is missing
        if not directive['title']:
            # Title is optional but recommended
            pass
    
    def _check_fence_nesting(self, directive: Dict[str, Any]) -> None:
        """
        Check for fence nesting issues - when a directive uses 3 backticks
        but contains code blocks that also use 3 backticks.
        
        This checks if:
        1. The directive uses exactly 3 backticks
        2. The content appears truncated (suspiciously short) OR
        3. The content contains code block markers
        
        Args:
            directive: Directive info dict with 'fence_depth' and 'content'
        """
        content = directive['content']
        fence_depth = directive['fence_depth']
        
        # Only check if using exactly 3 backticks for the directive
        if fence_depth != 3:
            return
        
        # Check 1: Look for code blocks in the extracted content
        # Match both ``` and ~~~ fenced code blocks
        code_block_pattern = r'^(`{3,}|~{3,})[a-zA-Z0-9_-]*\s*$'
        
        lines = content.split('\n')
        has_code_blocks = False
        for line in lines:
            match = re.match(code_block_pattern, line.strip())
            if match:
                fence_marker = match.group(1)
                # If we find a 3-backtick code block inside a 3-backtick directive
                if fence_marker.startswith('`') and len(fence_marker) == 3:
                    has_code_blocks = True
                    break
        
        if has_code_blocks:
            directive['fence_nesting_warning'] = (
                f'Directive uses 3 backticks (```) but contains 3-backtick code blocks. '
                f'Use 4+ backticks (````) for the directive to avoid parsing issues.'
            )
            return
        
        # Check 2: Detect suspiciously short content for tabs/code-tabs directives
        # These directives typically have substantial content; if truncated, it's a red flag
        directive_type = directive['type']
        if directive_type in ('tabs', 'code-tabs', 'code_tabs'):
            # Count tab markers
            tab_count = len(re.findall(r'^### Tab:', content, re.MULTILINE))
            content_lines = len([l for l in lines if l.strip()])
            
            # If we have tab markers but very little content, might be truncated
            if tab_count > 0 and content_lines < (tab_count * 3):
                # Probably truncated - warn about potential nesting
                directive['fence_nesting_warning'] = (
                    f'Directive content appears incomplete ({content_lines} lines, {tab_count} tabs). '
                    f'If tabs contain code blocks, use 4+ backticks (````) for the directive fence.'
                )
    
    def _check_directive_syntax(self, data: Dict[str, Any]) -> List[CheckResult]:
        """Check directive syntax is valid."""
        results = []
        errors = data['syntax_errors']
        fence_warnings = data['fence_nesting_warnings']
        
        # Check for syntax errors
        if errors:
            results.append(CheckResult.error(
                f"{len(errors)} directive(s) have syntax errors",
                recommendation="Fix directive syntax. Check directive names and closing backticks.",
                details=[
                    f"{e['page'].name}:{e['line']} - {e['type']}: {e['error']}"
                    for e in errors[:5]
                ]
            ))
        elif data['total_directives'] > 0:
            results.append(CheckResult.success(
                f"All {data['total_directives']} directive(s) syntactically valid"
            ))
        else:
            # No directives found
            results.append(CheckResult.success(
                "No directives found in site (validation skipped)"
            ))
        
        # Check for fence nesting warnings
        if fence_warnings:
            results.append(CheckResult.warning(
                f"{len(fence_warnings)} directive(s) may have fence nesting issues",
                recommendation="Use 4+ backticks (````) for directive fences when content contains 3-backtick code blocks.",
                details=[
                    f"{w['page'].name}:{w['line']} - {w['type']}: {w['warning']}"
                    for w in fence_warnings[:5]
                ]
            ))
        
        return results
    
    def _check_directive_completeness(self, data: Dict[str, Any]) -> List[CheckResult]:
        """Check directives are complete (have required content, options, etc)."""
        results = []
        errors = data['completeness_errors']
        
        if errors:
            # Separate warnings from errors
            # Single-tab or empty content are warnings, not hard errors
            warning_keywords = ['only 1 tab', 'consider using', 'has no tab markers']
            warnings = [e for e in errors if any(kw in e['error'] for kw in warning_keywords)]
            hard_errors = [e for e in errors if e not in warnings]
            
            if hard_errors:
                results.append(CheckResult.error(
                    f"{len(hard_errors)} directive(s) incomplete",
                    recommendation="Fix incomplete directives. Add required content and options.",
                    details=[
                        f"{e['page'].name}:{e['line']} - {e['type']}: {e['error']}"
                        for e in hard_errors[:5]
                    ]
                ))
            
            if warnings:
                results.append(CheckResult.warning(
                    f"{len(warnings)} directive(s) could be improved",
                    recommendation="Review directive usage. Consider simpler alternatives for single-item directives.",
                    details=[
                        f"{e['page'].name}:{e['line']} - {e['type']}: {e['error']}"
                        for e in warnings[:5]
                    ]
                ))
        
        if not errors and data['total_directives'] > 0:
            results.append(CheckResult.success(
                f"All {data['total_directives']} directive(s) complete"
            ))
        
        return results
    
    def _check_directive_performance(self, data: Dict[str, Any]) -> List[CheckResult]:
        """Check for performance issues with directive usage."""
        results = []
        warnings = data['performance_warnings']
        
        if warnings:
            # Group by issue type
            heavy_pages = [w for w in warnings if w['issue'] == 'heavy_directive_usage']
            too_many_tabs = [w for w in warnings if w['issue'] == 'too_many_tabs']
            
            if heavy_pages:
                results.append(CheckResult.warning(
                    f"{len(heavy_pages)} page(s) have heavy directive usage (>{self.MAX_DIRECTIVES_PER_PAGE} directives)",
                    recommendation="Consider splitting large pages or reducing directive nesting. Each directive adds ~20-50ms build time.",
                    details=[
                        f"{w['page'].name}: {w['count']} directives"
                        for w in sorted(heavy_pages, key=lambda x: x['count'], reverse=True)[:5]
                    ]
                ))
            
            if too_many_tabs:
                results.append(CheckResult.warning(
                    f"{len(too_many_tabs)} tabs block(s) have many tabs (>{self.MAX_TABS_PER_BLOCK})",
                    recommendation="Consider splitting into multiple tabs blocks or separate pages. Large tabs blocks slow rendering.",
                    details=[
                        f"{w['page'].name}:{w['line']}: {w['count']} tabs"
                        for w in sorted(too_many_tabs, key=lambda x: x['count'], reverse=True)[:5]
                    ]
                ))
        
        # Always show statistics if there are directives
        if data['total_directives'] > 0:
            top_types = sorted(data['by_type'].items(), key=lambda x: x[1], reverse=True)[:3]
            type_summary = ', '.join([f"{t}({c})" for t, c in top_types])
            avg_per_page = data['total_directives'] / max(len(data['by_page']), 1)
            
            results.append(CheckResult.info(
                f"Directive usage: {data['total_directives']} total across {len(data['by_page'])} pages. "
                f"Most used: {type_summary}. Average per page: {avg_per_page:.1f}"
            ))
        
        return results
    
    def _check_directive_rendering(self, site: 'Site', data: Dict[str, Any]) -> List[CheckResult]:
        """Check that directives rendered properly in output HTML."""
        results = []
        issues = []
        
        # Sample pages (check all non-generated pages)
        pages_to_check = [
            p for p in site.pages 
            if p.output_path and p.output_path.exists() and not p.metadata.get('_generated')
        ]
        
        for page in pages_to_check:
            try:
                content = page.output_path.read_text(encoding='utf-8')
                
                # Check for unrendered directive markers (outside code blocks)
                if self._has_unrendered_directives(content):
                    issues.append(f"{page.output_path.name}: Unrendered directive block found")
                
                # Check for directive parsing error markers
                if 'class="markdown-error"' in content:
                    issues.append(f"{page.output_path.name}: Directive parsing error in output")
                
            except Exception:
                pass
        
        if issues:
            results.append(CheckResult.error(
                f"{len(issues)} page(s) have directive rendering issues",
                recommendation="Check for directive syntax errors or missing directive plugins.",
                details=issues[:5]
            ))
        else:
            if data['total_directives'] > 0:
                results.append(CheckResult.success(
                    f"All directive(s) rendered successfully (checked {len(pages_to_check)} pages)"
                ))
        
        return results
    
    def _has_unrendered_directives(self, html_content: str) -> bool:
        """
        Check if HTML has unrendered directive blocks (outside code blocks).
        
        Distinguishes between:
        - Actual unrendered directives (bad)
        - Documented/escaped directive syntax in code examples (ok)
        
        Args:
            html_content: HTML content to check
            
        Returns:
            True if unrendered directives found (not in code blocks)
        """
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove all code blocks first (they're allowed to show directive syntax)
            for code_block in soup.find_all(['code', 'pre']):
                code_block.decompose()
            
            # Now check the remaining HTML for directive markers
            remaining_text = soup.get_text()
            
            # Check for unrendered directive blocks: ```{type}
            if re.search(r'```\{(\w+)', remaining_text):
                return True
            
            return False
            
        except ImportError:
            # BeautifulSoup not available, fall back to simple check
            # (will have false positives for docs with code examples)
            return re.search(r'```\{(\w+)', html_content) is not None
        except Exception:
            # On any parsing error, assume it's ok to avoid false positives
            return False

