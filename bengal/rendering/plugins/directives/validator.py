"""
Pre-parse validation for directives.

Validates directive syntax before parsing to catch errors early with
helpful messages.
"""

import re
from pathlib import Path
from typing import Any


class DirectiveSyntaxValidator:
    """
    Validates directive syntax before parsing.
    
    Catches common errors early with helpful messages before expensive
    parsing and recursive markdown processing.
    """
    
    # Known directive types
    KNOWN_DIRECTIVES = {
        'tabs', 'note', 'tip', 'warning', 'danger', 'error',
        'info', 'example', 'success', 'caution', 'dropdown',
        'details', 'code-tabs', 'code_tabs'
    }
    
    # Admonition types (subset of known directives)
    ADMONITION_TYPES = {
        'note', 'tip', 'warning', 'danger', 'error',
        'info', 'example', 'success', 'caution'
    }
    
    @staticmethod
    def validate_tabs_directive(content: str, file_path: Path | None = None, line_number: int | None = None) -> list[str]:
        """
        Validate tabs directive content.
        
        Args:
            content: Directive content (between opening and closing backticks)
            file_path: Optional file path for error messages
            line_number: Optional line number for error messages
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not content or not content.strip():
            errors.append("Tabs directive has no content")
            return errors
        
        # Check for tab markers: ### Tab: Title
        tab_markers = re.findall(r'^### Tab: (.+)$', content, re.MULTILINE)
        
        if len(tab_markers) == 0:
            # Check for common typos
            bad_markers = re.findall(r'^###\s*Ta[^b]', content, re.MULTILINE)
            if bad_markers:
                errors.append(
                    "Malformed tab marker found. "
                    "Use format: ### Tab: Title (note the space after colon)"
                )
            else:
                errors.append(
                    "Tabs directive has no tab markers. "
                    "Use ### Tab: Title to create tabs"
                )
        
        elif len(tab_markers) == 1:
            errors.append(
                "Tabs directive has only 1 tab. "
                "For single items, use an admonition (note, tip, etc.) instead"
            )
        
        # Check for excessive tabs (performance warning)
        if len(tab_markers) > 10:
            errors.append(
                f"Tabs directive has {len(tab_markers)} tabs (>10). "
                "Consider splitting into multiple tabs blocks or separate pages for better performance"
            )
        
        return errors
    
    @staticmethod
    def validate_code_tabs_directive(content: str, file_path: Path | None = None, line_number: int | None = None) -> list[str]:
        """
        Validate code-tabs directive content.
        
        Args:
            content: Directive content
            file_path: Optional file path
            line_number: Optional line number
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not content or not content.strip():
            errors.append("Code-tabs directive has no content")
            return errors
        
        # Check for tab markers
        tab_markers = re.findall(r'^### Tab: (.+)$', content, re.MULTILINE)
        
        if len(tab_markers) == 0:
            errors.append(
                "Code-tabs directive has no tab markers. "
                "Use ### Tab: Language to create code tabs"
            )
        
        return errors
    
    @staticmethod
    def validate_dropdown_directive(content: str, title: str = "", file_path: Path | None = None, line_number: int | None = None) -> list[str]:
        """
        Validate dropdown directive content.
        
        Args:
            content: Directive content
            title: Directive title
            file_path: Optional file path
            line_number: Optional line number
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not content or not content.strip():
            errors.append("Dropdown directive has no content")
        
        # Title is optional but recommended
        if not title:
            # This is a warning, not an error
            pass
        
        return errors
    
    @staticmethod
    def validate_admonition_directive(admon_type: str, content: str, file_path: Path | None = None, line_number: int | None = None) -> list[str]:
        """
        Validate admonition directive content.
        
        Args:
            admon_type: Type of admonition (note, tip, warning, etc.)
            content: Directive content
            file_path: Optional file path
            line_number: Optional line number
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not content or not content.strip():
            errors.append(f"{admon_type.capitalize()} admonition has no content")
        
        return errors
    
    @classmethod
    def validate_directive(cls, directive_type: str, content: str, title: str = "", options: dict[str, Any] | None = None, file_path: Path | None = None, line_number: int | None = None) -> list[str]:
        """
        Validate any directive type.
        
        Args:
            directive_type: Type of directive (tabs, note, dropdown, etc.)
            content: Directive content
            title: Directive title (if any)
            options: Directive options dictionary
            file_path: Optional file path
            line_number: Optional line number
            
        Returns:
            List of validation errors (empty if valid)
        """
        options = options or {}
        errors = []
        
        # Check if directive type is known
        if directive_type not in cls.KNOWN_DIRECTIVES:
            errors.append(
                f"Unknown directive type: {directive_type}. "
                f"Known directives: {', '.join(sorted(cls.KNOWN_DIRECTIVES))}"
            )
            return errors  # Don't validate further if type is unknown
        
        # Validate based on type
        if directive_type == 'tabs':
            errors.extend(cls.validate_tabs_directive(content, file_path, line_number))
        
        elif directive_type in ('code-tabs', 'code_tabs'):
            errors.extend(cls.validate_code_tabs_directive(content, file_path, line_number))
        
        elif directive_type in ('dropdown', 'details'):
            errors.extend(cls.validate_dropdown_directive(content, title, file_path, line_number))
        
        elif directive_type in cls.ADMONITION_TYPES:
            errors.extend(cls.validate_admonition_directive(directive_type, content, file_path, line_number))
        
        return errors
    
    @classmethod
    def validate_directive_block(cls, directive_block: str, file_path: Path | None = None, start_line: int | None = None) -> dict[str, Any]:
        """
        Validate a complete directive block from markdown.
        
        Args:
            directive_block: Full directive block including opening/closing backticks
            file_path: Optional file path
            start_line: Optional starting line number
            
        Returns:
            Dictionary with validation results:
            {
                'valid': bool,
                'errors': List[str],
                'directive_type': str,
                'content': str,
                'title': str,
                'options': Dict[str, Any]
            }
        """
        result = {
            'valid': True,
            'errors': [],
            'directive_type': None,
            'content': '',
            'title': '',
            'options': {}
        }
        
        # Parse directive block
        # Pattern: ```{directive_type} title
        #          :option: value
        #          
        #          content
        #          ```
        pattern = r'```\{(\w+(?:-\w+)?)\}([^\n]*)\n(.*?)```'
        match = re.search(pattern, directive_block, re.DOTALL)
        
        if not match:
            result['valid'] = False
            result['errors'].append("Malformed directive block: could not parse")
            return result
        
        directive_type = match.group(1)
        title = match.group(2).strip()
        content = match.group(3)
        
        result['directive_type'] = directive_type
        result['title'] = title
        result['content'] = content
        
        # Parse options (lines starting with :key:)
        options = {}
        option_pattern = r'^:(\w+):\s*(.*)$'
        for line in content.split('\n'):
            opt_match = re.match(option_pattern, line.strip())
            if opt_match:
                key = opt_match.group(1)
                value = opt_match.group(2).strip()
                options[key] = value
        result['options'] = options
        
        # Validate the directive
        errors = cls.validate_directive(
            directive_type=directive_type,
            content=content,
            title=title,
            options=options,
            file_path=file_path,
            line_number=start_line
        )
        
        if errors:
            result['valid'] = False
            result['errors'] = errors
        
        return result


def validate_markdown_directives(markdown_content: str, file_path: Path | None = None) -> list[dict[str, Any]]:
    """
    Validate all directive blocks in a markdown file.
    
    Args:
        markdown_content: Full markdown content
        file_path: Optional file path for error reporting
        
    Returns:
        List of validation results, one per directive block
    """
    results = []
    validator = DirectiveSyntaxValidator()
    
    # Find all directive blocks
    pattern = r'```\{(\w+(?:-\w+)?)\}[^\n]*\n.*?```'
    
    for match in re.finditer(pattern, markdown_content, re.DOTALL):
        directive_block = match.group(0)
        start_pos = match.start()
        
        # Calculate line number
        line_number = markdown_content[:start_pos].count('\n') + 1
        
        # Validate the block
        result = validator.validate_directive_block(
            directive_block=directive_block,
            file_path=file_path,
            start_line=line_number
        )
        
        results.append(result)
    
    return results


def get_directive_validation_summary(validation_results: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Get a summary of directive validation results.
    
    Args:
        validation_results: List of validation result dictionaries
        
    Returns:
        Summary dictionary with counts and error lists
    """
    total = len(validation_results)
    valid = sum(1 for r in validation_results if r['valid'])
    invalid = total - valid
    
    all_errors = []
    for result in validation_results:
        if not result['valid']:
            for error in result['errors']:
                all_errors.append({
                    'directive_type': result['directive_type'],
                    'error': error
                })
    
    return {
        'total_directives': total,
        'valid': valid,
        'invalid': invalid,
        'errors': all_errors,
        'has_errors': invalid > 0
    }

