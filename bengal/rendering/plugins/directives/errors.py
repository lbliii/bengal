"""
Rich error reporting for directive parsing.

Provides detailed, helpful error messages when directives fail to parse.
"""

from pathlib import Path
from typing import Optional


class DirectiveError(Exception):
    """
    Rich error for directive parsing failures.
    
    Provides detailed context including:
    - Directive type that failed
    - File path and line number
    - Content snippet showing the problem
    - Helpful suggestions for fixing
    """
    
    def __init__(
        self,
        directive_type: str,
        error_message: str,
        file_path: Optional[Path] = None,
        line_number: Optional[int] = None,
        content_snippet: Optional[str] = None,
        suggestion: Optional[str] = None
    ):
        """
        Initialize directive error.
        
        Args:
            directive_type: Type of directive that failed (e.g., 'tabs', 'note')
            error_message: Human-readable error description
            file_path: Path to file containing the directive
            line_number: Line number where directive starts
            content_snippet: Snippet of content showing the problem
            suggestion: Helpful suggestion for fixing the issue
        """
        self.directive_type = directive_type
        self.error_message = error_message
        self.file_path = file_path
        self.line_number = line_number
        self.content_snippet = content_snippet
        self.suggestion = suggestion
        
        # Build the full error message
        super().__init__(self._format_error())
    
    def _format_error(self) -> str:
        """Format a rich error message for display."""
        lines = []
        
        # Header with emoji
        lines.append(f"\n❌ Directive Error: {self.directive_type}")
        
        # Location info
        if self.file_path:
            location = str(self.file_path)
            if self.line_number:
                location += f":{self.line_number}"
            lines.append(f"   File: {location}")
        
        # Error message
        lines.append(f"   Error: {self.error_message}")
        
        # Content snippet
        if self.content_snippet:
            lines.append("\n   Context:")
            # Indent each line of the snippet
            for line in self.content_snippet.split('\n'):
                lines.append(f"   │ {line}")
        
        # Suggestion
        if self.suggestion:
            lines.append(f"\n   💡 Suggestion: {self.suggestion}")
        
        return '\n'.join(lines)
    
    def display(self) -> str:
        """Get formatted error message (same as __str__)."""
        return self._format_error()


def format_directive_error(
    directive_type: str,
    error_message: str,
    file_path: Optional[Path] = None,
    line_number: Optional[int] = None,
    content_lines: Optional[list] = None,
    error_line_offset: int = 0,
    suggestion: Optional[str] = None
) -> str:
    """
    Format a directive error message.
    
    Args:
        directive_type: Type of directive
        error_message: Error description
        file_path: File containing the error
        line_number: Line number of directive
        content_lines: Lines of content around the error
        error_line_offset: Which line in content_lines has the error (for highlighting)
        suggestion: Helpful suggestion
        
    Returns:
        Formatted error message
    """
    lines = []
    
    # Header
    lines.append(f"\n❌ Directive Error: {{{directive_type}}}")
    
    # Location
    if file_path:
        location = str(file_path)
        if line_number:
            location += f":{line_number}"
        lines.append(f"   File: {location}")
    
    # Error message
    lines.append(f"   Error: {error_message}")
    
    # Content with highlighting
    if content_lines:
        lines.append("\n   Context:")
        for i, line in enumerate(content_lines):
            if i == error_line_offset:
                # Highlight error line
                lines.append(f"   │ {line}  ← ERROR")
            else:
                lines.append(f"   │ {line}")
    
    # Suggestion
    if suggestion:
        lines.append(f"\n   💡 Suggestion: {suggestion}")
    
    return '\n'.join(lines)


# Common directive error messages and suggestions

DIRECTIVE_SUGGESTIONS = {
    'unknown_type': "Check the directive name. Known directives: tabs, note, tip, warning, danger, error, info, example, success, caution, dropdown, details, code-tabs",
    'missing_closing': "Make sure your directive has closing backticks (```) on their own line",
    'malformed_tab_marker': "Tab markers should be: ### Tab: Title (note the space after colon)",
    'empty_tabs': "Tabs directive needs at least 2 tabs. Use ### Tab: Name to create tabs",
    'single_tab': "For single items, use an admonition (note, tip) instead of tabs",
    'empty_content': "Directive content cannot be empty. Add some markdown content between the opening and closing backticks",
    'too_many_tabs': "Consider splitting large tabs blocks into separate sections or pages. Each tab adds rendering overhead",
    'deep_nesting': "Avoid nesting directives more than 3-4 levels deep. This impacts build performance",
}


def get_suggestion(error_key: str) -> Optional[str]:
    """Get a helpful suggestion for a common error type."""
    return DIRECTIVE_SUGGESTIONS.get(error_key)

