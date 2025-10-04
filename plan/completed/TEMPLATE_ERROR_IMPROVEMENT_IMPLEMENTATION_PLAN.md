# Template Error Reporting - Implementation Plan

**Date:** October 3, 2025  
**Status:** Ready for Implementation  
**Priority:** High (Developer Experience)

---

## Executive Summary

This plan implements **enhanced template error reporting** for Bengal SSG based on AI assistant feedback during Phase 2-3 theme development. The improvements will provide:

- **Line numbers and file paths** in error messages
- **Template inclusion chains** for debugging recursive includes
- **Multiple error collection** (fix all at once, not one-by-one)
- **Available filters listing** when unknown filters are encountered
- **Pre-build validation** to catch errors before rendering

---

## 🎯 Goals

### Primary Goals
1. **Reduce debugging time** from 4+ rebuilds to 1 rebuild
2. **Provide actionable error messages** with line numbers and context
3. **Show template inclusion chains** for complex template hierarchies
4. **List available filters** when unknown filters are used
5. **Enable pre-build validation** to catch all errors upfront

### Success Metrics
- Error messages include file name + line number
- Template inclusion chains shown for nested includes
- All template errors collected (not just first one)
- Available filters listed on "unknown filter" errors
- `bengal build --validate` catches all errors before rendering

---

## 📐 Current Architecture Analysis

### Component Overview

```
bengal/
├── rendering/
│   ├── renderer.py           ← Main error catching (line 75-100)
│   ├── template_engine.py    ← Jinja2 environment setup
│   ├── pipeline.py            ← Content preprocessing
│   └── template_functions/   ← 75+ registered functions
├── utils/
│   └── build_stats.py         ← Warning collection (BuildWarning class)
├── cli.py                     ← CLI with --strict and --debug flags
└── orchestration/
    └── build.py               ← Build coordination
```

### Error Handling Flow (Current)

```python
# renderer.py:75-100
try:
    return self.template_engine.render(template_name, context)
except Exception as e:
    # Simple error message
    print(f"⚠️  Warning: Failed to render {page.source_path} with template {template_name}: {e}")
    
    # Fallback rendering
    return self._render_fallback(page, content)
```

**Problems:**
1. ❌ No line numbers from Jinja2
2. ❌ No template inclusion chain
3. ❌ Only shows first error (stops at first exception)
4. ❌ No context or suggestions
5. ❌ Generic exception handling (loses Jinja2 metadata)

---

## 🏗️ Proposed Architecture

### New Components

```
bengal/
├── rendering/
│   ├── errors.py              ← NEW: Rich error objects
│   ├── validator.py           ← NEW: Template validator
│   └── error_formatter.py     ← NEW: Pretty error display
├── utils/
│   └── build_stats.py         ← ENHANCED: Rich warnings
└── cli.py                     ← ENHANCED: Add --validate flag
```

### Enhanced Error Flow

```python
# renderer.py (enhanced)
try:
    return self.template_engine.render(template_name, context)
except TemplateError as e:
    # Extract rich error information
    error = TemplateRenderError.from_jinja2_error(
        e, 
        template_name, 
        page.source_path,
        self.template_engine
    )
    
    # Collect error (don't stop)
    if self.build_stats:
        self.build_stats.add_template_error(error)
    
    # Display rich error
    if not strict_mode:
        display_template_error(error)
        return self._render_fallback(page, content)
    else:
        raise
```

---

## 📦 Phase 1: Rich Error Objects (High Priority)

### 1.1 Create `bengal/rendering/errors.py`

**New file** containing rich error classes:

```python
"""
Rich template error objects with line numbers, context, and suggestions.
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple
from pathlib import Path
from jinja2 import TemplateError, TemplateSyntaxError, UndefinedError
from jinja2.exceptions import TemplateRuntimeError


@dataclass
class TemplateErrorContext:
    """Context around an error in a template."""
    
    template_name: str
    line_number: Optional[int]
    column: Optional[int]
    source_line: Optional[str]
    surrounding_lines: List[Tuple[int, str]]  # (line_num, line_content)
    template_path: Optional[Path]


@dataclass
class InclusionChain:
    """Represents the template inclusion chain."""
    
    entries: List[Tuple[str, Optional[int]]]  # [(template_name, line_num), ...]
    
    def __str__(self) -> str:
        """Format as readable chain."""
        chain = []
        for i, (template, line) in enumerate(self.entries):
            indent = "  " * i
            arrow = "└─" if i == len(self.entries) - 1 else "├─"
            if line:
                chain.append(f"{indent}{arrow} {template}:{line}")
            else:
                chain.append(f"{indent}{arrow} {template}")
        return "\n".join(chain)


@dataclass
class TemplateRenderError:
    """
    Rich template error with all debugging information.
    
    This replaces the simple string error messages with structured data
    that can be displayed beautifully and used for IDE integration.
    """
    
    error_type: str  # 'syntax', 'undefined', 'filter', 'runtime'
    message: str
    template_context: TemplateErrorContext
    inclusion_chain: Optional[InclusionChain]
    page_source: Optional[Path]
    suggestion: Optional[str]
    available_alternatives: List[str]  # For unknown filters/variables
    
    @classmethod
    def from_jinja2_error(
        cls,
        error: Exception,
        template_name: str,
        page_source: Optional[Path],
        template_engine: Any
    ) -> 'TemplateRenderError':
        """
        Extract rich error information from Jinja2 exception.
        
        Args:
            error: Jinja2 exception
            template_name: Template being rendered
            page_source: Source content file (if applicable)
            template_engine: Template engine instance
            
        Returns:
            Rich error object
        """
        # Determine error type
        error_type = cls._classify_error(error)
        
        # Extract context
        context = cls._extract_context(error, template_name, template_engine)
        
        # Build inclusion chain
        inclusion_chain = cls._build_inclusion_chain(error, template_engine)
        
        # Generate suggestion
        suggestion = cls._generate_suggestion(error, error_type, template_engine)
        
        # Find alternatives (for unknown filters/variables)
        alternatives = cls._find_alternatives(error, error_type, template_engine)
        
        return cls(
            error_type=error_type,
            message=str(error),
            template_context=context,
            inclusion_chain=inclusion_chain,
            page_source=page_source,
            suggestion=suggestion,
            available_alternatives=alternatives
        )
    
    @staticmethod
    def _classify_error(error: Exception) -> str:
        """Classify Jinja2 error type."""
        if isinstance(error, TemplateSyntaxError):
            return 'syntax'
        elif isinstance(error, UndefinedError):
            # Check if it's an unknown filter
            if 'filter' in str(error).lower():
                return 'filter'
            return 'undefined'
        elif isinstance(error, TemplateRuntimeError):
            return 'runtime'
        return 'other'
    
    @staticmethod
    def _extract_context(
        error: Exception,
        template_name: str,
        template_engine: Any
    ) -> TemplateErrorContext:
        """Extract template context from error."""
        # Jinja2 provides: error.lineno, error.filename, error.source
        line_number = getattr(error, 'lineno', None)
        filename = getattr(error, 'filename', None) or template_name
        
        # Find template path
        template_path = template_engine._find_template_path(filename)
        
        # Get source lines
        source_line = None
        surrounding_lines = []
        
        if template_path and template_path.exists():
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                if line_number and 1 <= line_number <= len(lines):
                    # Get the error line
                    source_line = lines[line_number - 1].rstrip()
                    
                    # Get surrounding context (3 lines before, 3 after)
                    start = max(0, line_number - 4)
                    end = min(len(lines), line_number + 3)
                    
                    for i in range(start, end):
                        surrounding_lines.append((i + 1, lines[i].rstrip()))
            except (IOError, IndexError):
                pass
        
        return TemplateErrorContext(
            template_name=filename,
            line_number=line_number,
            column=None,  # Jinja2 doesn't provide column consistently
            source_line=source_line,
            surrounding_lines=surrounding_lines,
            template_path=template_path
        )
    
    @staticmethod
    def _build_inclusion_chain(
        error: Exception,
        template_engine: Any
    ) -> Optional[InclusionChain]:
        """Build template inclusion chain from traceback."""
        # Parse Python traceback to find template includes
        import traceback
        tb = traceback.extract_tb(error.__traceback__)
        
        entries = []
        for frame in tb:
            # Look for template file paths
            if 'templates/' in frame.filename:
                template_name = Path(frame.filename).name
                entries.append((template_name, frame.lineno))
        
        return InclusionChain(entries) if entries else None
    
    @staticmethod
    def _generate_suggestion(
        error: Exception,
        error_type: str,
        template_engine: Any
    ) -> Optional[str]:
        """Generate helpful suggestion based on error."""
        error_str = str(error).lower()
        
        if error_type == 'filter':
            if 'in_section' in error_str:
                return "Bengal doesn't have 'in_section' filter. Check if the page is in a section using: {% if page.parent %}"
            elif 'is_ancestor' in error_str:
                return "Use page comparison instead: {% if page.url == other_page.url %}"
        
        elif error_type == 'undefined':
            if 'metadata.weight' in error_str:
                return "Use safe access: {{ page.metadata.get('weight', 0) }}"
        
        elif error_type == 'syntax':
            if 'with' in error_str:
                return "Jinja2 doesn't support 'with' in include. Use {% set %} before {% include %}"
            elif 'default=' in error_str:
                return "The 'default' parameter in sort() is not supported. Remove it or use a custom filter."
        
        return None
    
    @staticmethod
    def _find_alternatives(
        error: Exception,
        error_type: str,
        template_engine: Any
    ) -> List[str]:
        """Find alternative filters/variables that might work."""
        if error_type != 'filter':
            return []
        
        # Extract filter name from error
        import re
        match = re.search(r"No filter named ['\"](\w+)['\"]", str(error))
        if not match:
            return []
        
        unknown_filter = match.group(1)
        
        # Get all available filters
        available_filters = sorted(template_engine.env.filters.keys())
        
        # Find similar filters (Levenshtein distance or simple matching)
        from difflib import get_close_matches
        suggestions = get_close_matches(unknown_filter, available_filters, n=3, cutoff=0.6)
        
        return suggestions


def display_template_error(error: TemplateRenderError, use_color: bool = True) -> None:
    """
    Display a rich template error in the terminal.
    
    Args:
        error: Rich error object
        use_color: Whether to use terminal colors
    """
    import click
    
    # Header
    error_type_names = {
        'syntax': 'Template Syntax Error',
        'filter': 'Unknown Filter',
        'undefined': 'Undefined Variable',
        'runtime': 'Template Runtime Error',
        'other': 'Template Error'
    }
    
    header = error_type_names.get(error.error_type, 'Template Error')
    click.echo(click.style(f"\n⚠️  {header}", fg='red', bold=True))
    
    # File and line
    ctx = error.template_context
    if ctx.template_path:
        click.echo(click.style(f"\n  File: ", fg='cyan') + str(ctx.template_path))
    else:
        click.echo(click.style(f"\n  Template: ", fg='cyan') + ctx.template_name)
    
    if ctx.line_number:
        click.echo(click.style(f"  Line: ", fg='cyan') + str(ctx.line_number))
    
    # Source code context
    if ctx.surrounding_lines:
        click.echo(click.style("\n  Code:", fg='cyan'))
        for line_num, line_content in ctx.surrounding_lines:
            is_error_line = line_num == ctx.line_number
            prefix = ">" if is_error_line else " "
            line_style = {'fg': 'red', 'bold': True} if is_error_line else {'fg': 'white'}
            
            click.echo(click.style(f"  {prefix} {line_num:4d} | ", fg='cyan') + 
                      click.style(line_content, **line_style))
            
            # Add pointer to error location
            if is_error_line and ctx.source_line:
                # Simple pointer (could be enhanced with column info)
                pointer = " " * (len(f"  {prefix} {line_num:4d} | ") + 5) + "^" * len(ctx.source_line.strip())
                click.echo(click.style(pointer, fg='red', bold=True))
    
    # Error message
    click.echo(click.style(f"\n  Error: ", fg='red', bold=True) + error.message)
    
    # Suggestion
    if error.suggestion:
        click.echo(click.style(f"\n  Suggestion: ", fg='yellow', bold=True) + error.suggestion)
    
    # Alternatives
    if error.available_alternatives:
        click.echo(click.style(f"\n  Did you mean: ", fg='yellow', bold=True) + 
                  ", ".join(f"'{alt}'" for alt in error.available_alternatives))
    
    # All available filters (for filter errors)
    if error.error_type == 'filter' and error.available_alternatives:
        # Don't list all filters here, just show close matches above
        pass
    
    # Inclusion chain
    if error.inclusion_chain:
        click.echo(click.style(f"\n  Template Chain:", fg='cyan'))
        for line in str(error.inclusion_chain).split('\n'):
            click.echo(f"  {line}")
    
    # Page source
    if error.page_source:
        click.echo(click.style(f"\n  Used by page: ", fg='cyan') + str(error.page_source))
    
    click.echo()
```

**Key Features:**
- Extracts line numbers from Jinja2 exceptions
- Shows code context (3 lines before/after)
- Builds template inclusion chains
- Generates helpful suggestions
- Finds similar filters using difflib
- Beautiful terminal output with colors

---

## 📦 Phase 2: Multiple Error Collection (High Priority)

### 2.1 Enhance `BuildStats` in `bengal/utils/build_stats.py`

**Modify:**

```python
@dataclass
class BuildStats:
    """Container for build statistics."""
    
    # ... existing fields ...
    
    # Enhanced warnings
    warnings: list = None
    template_errors: list = None  # NEW: Rich template errors
    
    def __post_init__(self):
        """Initialize mutable defaults."""
        if self.warnings is None:
            self.warnings = []
        if self.template_errors is None:
            self.template_errors = []
    
    def add_template_error(self, error: 'TemplateRenderError') -> None:
        """Add a rich template error."""
        self.template_errors.append(error)
    
    @property
    def has_errors(self) -> bool:
        """Check if build has any errors."""
        return len(self.template_errors) > 0 or len(self.warnings) > 0


def display_template_errors(stats: BuildStats) -> None:
    """
    Display all collected template errors.
    
    Args:
        stats: Build statistics with template errors
    """
    if not stats.template_errors:
        return
    
    from bengal.rendering.errors import display_template_error
    
    error_count = len(stats.template_errors)
    click.echo(click.style(f"\n❌ Template Errors ({error_count}):\n", fg='red', bold=True))
    
    for i, error in enumerate(stats.template_errors, 1):
        click.echo(click.style(f"Error {i}/{error_count}:", fg='red', bold=True))
        display_template_error(error, use_color=True)
        
        if i < error_count:
            click.echo(click.style("─" * 80, fg='cyan'))
```

### 2.2 Modify `Renderer.render_page()` in `bengal/rendering/renderer.py`

**Replace lines 75-100:**

```python
def render_page(self, page: Page, content: Optional[str] = None) -> str:
    # ... existing setup code ...
    
    # Render with template
    try:
        return self.template_engine.render(template_name, context)
    
    except Exception as e:
        from bengal.rendering.errors import TemplateRenderError, display_template_error
        
        # Create rich error object
        rich_error = TemplateRenderError.from_jinja2_error(
            e,
            template_name,
            page.source_path,
            self.template_engine
        )
        
        # In strict mode, display and fail immediately
        strict_mode = self.site.config.get("strict_mode", False)
        debug_mode = self.site.config.get("debug", False)
        
        if strict_mode:
            display_template_error(rich_error)
            if debug_mode:
                import traceback
                traceback.print_exc()
            raise
        
        # In production mode, collect error and continue
        if self.build_stats:
            self.build_stats.add_template_error(rich_error)
        else:
            # No build stats available, display immediately
            display_template_error(rich_error)
        
        if debug_mode:
            import traceback
            traceback.print_exc()
        
        # Fallback to simple HTML
        return self._render_fallback(page, content)
```

**Key Change:** Instead of stopping at first error, errors are collected in `BuildStats` and rendering continues.

---

## 📦 Phase 3: Template Validation (Medium Priority)

### 3.1 Create `bengal/rendering/validator.py`

**New file:**

```python
"""
Template validation before rendering.
"""

from typing import List, Tuple, Optional
from pathlib import Path
from jinja2 import Environment, TemplateSyntaxError
import click


class TemplateValidator:
    """
    Validates templates for syntax errors and missing dependencies.
    """
    
    def __init__(self, template_engine: Any):
        """
        Initialize validator.
        
        Args:
            template_engine: TemplateEngine instance
        """
        self.template_engine = template_engine
        self.env = template_engine.env
    
    def validate_all(self) -> List['TemplateRenderError']:
        """
        Validate all templates in the theme.
        
        Returns:
            List of errors found
        """
        errors = []
        
        for template_dir in self.template_engine.template_dirs:
            if not template_dir.exists():
                continue
            
            # Find all template files
            for template_file in template_dir.rglob('*.html'):
                template_name = str(template_file.relative_to(template_dir))
                
                # Validate syntax
                syntax_errors = self._validate_syntax(template_name, template_file)
                errors.extend(syntax_errors)
                
                # Validate includes (check if included templates exist)
                include_errors = self._validate_includes(template_name, template_file)
                errors.extend(include_errors)
        
        return errors
    
    def _validate_syntax(
        self,
        template_name: str,
        template_path: Path
    ) -> List['TemplateRenderError']:
        """Validate template syntax."""
        from bengal.rendering.errors import TemplateRenderError
        
        try:
            # Try to compile the template
            with open(template_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            self.env.parse(source, template_name, template_path)
            return []
        
        except TemplateSyntaxError as e:
            # Create error object
            error = TemplateRenderError.from_jinja2_error(
                e,
                template_name,
                None,
                self.template_engine
            )
            return [error]
        
        except Exception as e:
            # Other parsing errors
            error = TemplateRenderError(
                error_type='other',
                message=str(e),
                template_context=TemplateErrorContext(
                    template_name=template_name,
                    line_number=None,
                    column=None,
                    source_line=None,
                    surrounding_lines=[],
                    template_path=template_path
                ),
                inclusion_chain=None,
                page_source=None,
                suggestion=None,
                available_alternatives=[]
            )
            return [error]
    
    def _validate_includes(
        self,
        template_name: str,
        template_path: Path
    ) -> List['TemplateRenderError']:
        """Check if all included templates exist."""
        errors = []
        
        # Parse template to find includes
        with open(template_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Simple regex to find includes (not perfect but good enough)
        import re
        includes = re.findall(r"{%\s*include\s+['\"]([^'\"]+)['\"]", source)
        
        for include_name in includes:
            try:
                self.env.get_template(include_name)
            except Exception as e:
                # Include not found
                from bengal.rendering.errors import TemplateRenderError, TemplateErrorContext
                
                error = TemplateRenderError(
                    error_type='other',
                    message=f"Included template not found: {include_name}",
                    template_context=TemplateErrorContext(
                        template_name=template_name,
                        line_number=None,
                        column=None,
                        source_line=None,
                        surrounding_lines=[],
                        template_path=template_path
                    ),
                    inclusion_chain=None,
                    page_source=None,
                    suggestion=f"Create {include_name} or fix the include path",
                    available_alternatives=[]
                )
                errors.append(error)
        
        return errors


def validate_templates(template_engine: Any) -> int:
    """
    Validate all templates and display results.
    
    Args:
        template_engine: TemplateEngine instance
        
    Returns:
        Number of errors found
    """
    click.echo(click.style("\n🔍 Validating templates...\n", fg='cyan', bold=True))
    
    validator = TemplateValidator(template_engine)
    errors = validator.validate_all()
    
    if not errors:
        click.echo(click.style("✓ All templates valid!", fg='green', bold=True))
        return 0
    
    # Display errors
    from bengal.rendering.errors import display_template_error
    
    click.echo(click.style(f"❌ Found {len(errors)} template error(s):\n", fg='red', bold=True))
    
    for i, error in enumerate(errors, 1):
        click.echo(click.style(f"Error {i}/{len(errors)}:", fg='red', bold=True))
        display_template_error(error)
        
        if i < len(errors):
            click.echo(click.style("─" * 80, fg='cyan'))
    
    return len(errors)
```

### 3.2 Add `--validate` flag to `bengal/cli.py`

**Modify `build` command:**

```python
@main.command()
@click.option('--parallel/--no-parallel', default=True, help='Enable parallel processing')
@click.option('--incremental', is_flag=True, help='Incremental build')
@click.option('--verbose', '-v', is_flag=True, help='Detailed output')
@click.option('--strict', is_flag=True, help='Fail on template errors')
@click.option('--debug', is_flag=True, help='Show debug output')
@click.option('--validate', is_flag=True, help='Validate templates before building')  # NEW
@click.option('--config', type=click.Path(exists=True), help='Config file path')
@click.option('--quiet', '-q', is_flag=True, help='Minimal output')
@click.argument('source', type=click.Path(exists=True), default='.')
def build(parallel: bool, incremental: bool, verbose: bool, strict: bool, debug: bool, 
         validate: bool, config: str, quiet: bool, source: str) -> None:
    """Build the static site."""
    
    # ... existing setup ...
    
    site = Site.from_config(root_path, config_path)
    
    # Validate templates if requested
    if validate:
        from bengal.rendering.validator import validate_templates
        
        # Create template engine (without building)
        from bengal.rendering.template_engine import TemplateEngine
        template_engine = TemplateEngine(site)
        
        error_count = validate_templates(template_engine)
        
        if error_count > 0:
            click.echo(click.style(f"\n❌ Validation failed with {error_count} error(s).", 
                                  fg='red', bold=True))
            click.echo(click.style("Fix errors above, then run 'bengal build'", fg='yellow'))
            raise click.Abort()
        
        click.echo()  # Blank line before build
    
    # Continue with normal build
    stats = site.build(parallel=parallel, incremental=incremental, verbose=verbose)
    
    # ... rest of build command ...
```

---

## 📦 Phase 4: Enhanced Error Display (Low Priority)

### 4.1 Create `bengal/rendering/error_formatter.py`

**New file for advanced formatting:**

```python
"""
Advanced template error formatters.
"""

from typing import List
import click
from bengal.rendering.errors import TemplateRenderError


class TemplateErrorFormatter:
    """
    Advanced formatting for template errors.
    """
    
    @staticmethod
    def format_for_ide(errors: List[TemplateRenderError]) -> str:
        """
        Format errors for IDE integration (JSON).
        
        Returns:
            JSON string for IDEs to parse
        """
        import json
        
        ide_errors = []
        for error in errors:
            ctx = error.template_context
            ide_errors.append({
                'file': str(ctx.template_path) if ctx.template_path else ctx.template_name,
                'line': ctx.line_number,
                'column': ctx.column,
                'severity': 'error',
                'message': error.message,
                'type': error.error_type,
                'suggestion': error.suggestion,
            })
        
        return json.dumps({'errors': ide_errors}, indent=2)
    
    @staticmethod
    def format_summary(errors: List[TemplateRenderError]) -> str:
        """
        Format brief summary of errors.
        
        Returns:
            Summary string
        """
        lines = [f"\n❌ {len(errors)} template error(s) found:\n"]
        
        for i, error in enumerate(errors, 1):
            ctx = error.template_context
            location = f"{ctx.template_name}:{ctx.line_number}" if ctx.line_number else ctx.template_name
            lines.append(f"  {i}. {location}")
            lines.append(f"     └─ {error.message}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_with_code_snippet(error: TemplateRenderError) -> str:
        """
        Format error with syntax-highlighted code snippet.
        
        This could be enhanced with pygments for syntax highlighting.
        """
        # For now, use the basic display_template_error
        # Future enhancement: Add syntax highlighting
        pass
```

---

## 📦 Phase 5: Additional Commands (Optional)

### 5.1 Add `bengal lint` command

**Add to `bengal/cli.py`:**

```python
@main.command()
@click.option('--fix', is_flag=True, help='Auto-fix common issues')
@click.option('--format', type=click.Choice(['text', 'json']), default='text', 
             help='Output format')
@click.option('--config', type=click.Path(exists=True), help='Config file path')
@click.argument('source', type=click.Path(exists=True), default='.')
def lint(fix: bool, format: str, config: str, source: str) -> None:
    """
    🔍 Lint templates for common issues.
    
    Validates template syntax, checks for missing includes,
    and suggests improvements.
    """
    from bengal.rendering.validator import validate_templates
    from bengal.rendering.error_formatter import TemplateErrorFormatter
    from bengal.core.site import Site
    
    try:
        root_path = Path(source).resolve()
        config_path = Path(config).resolve() if config else None
        
        # Load site (lightweight, no build)
        site = Site.from_config(root_path, config_path)
        
        # Create template engine
        from bengal.rendering.template_engine import TemplateEngine
        template_engine = TemplateEngine(site)
        
        # Validate
        from bengal.rendering.validator import TemplateValidator
        validator = TemplateValidator(template_engine)
        errors = validator.validate_all()
        
        # Display results
        if format == 'json':
            output = TemplateErrorFormatter.format_for_ide(errors)
            click.echo(output)
        else:
            if errors:
                for error in errors:
                    from bengal.rendering.errors import display_template_error
                    display_template_error(error)
                
                click.echo(click.style(f"\n✗ {len(errors)} error(s) found", 
                                      fg='red', bold=True))
                raise click.Abort()
            else:
                click.echo(click.style("✓ All templates valid!", fg='green', bold=True))
    
    except Exception as e:
        click.echo(click.style(f"❌ Lint failed: {e}", fg='red', bold=True))
        raise click.Abort()
```

---

## 🧪 Testing Strategy

### Unit Tests

Create `tests/rendering/test_template_errors.py`:

```python
import pytest
from bengal.rendering.errors import (
    TemplateRenderError,
    TemplateErrorContext,
    InclusionChain
)
from jinja2 import TemplateSyntaxError, UndefinedError


def test_error_classification():
    """Test error type classification."""
    error = TemplateSyntaxError("Unexpected token", lineno=10)
    assert TemplateRenderError._classify_error(error) == 'syntax'


def test_context_extraction():
    """Test context extraction from Jinja2 errors."""
    # Test with mock error and template engine
    pass


def test_inclusion_chain():
    """Test template inclusion chain building."""
    chain = InclusionChain([
        ('base.html', None),
        ('page.html', 20),
        ('partials/nav.html', 15)
    ])
    
    output = str(chain)
    assert 'base.html' in output
    assert 'page.html:20' in output


def test_suggestion_generation():
    """Test helpful suggestion generation."""
    # Test for known error patterns
    pass


def test_alternative_finding():
    """Test finding similar filters."""
    # Test with mock template engine
    pass
```

### Integration Tests

Create `tests/integration/test_error_reporting.py`:

```python
def test_build_with_template_errors(tmp_path):
    """Test that build collects multiple template errors."""
    # Create site with broken templates
    # Run build
    # Assert all errors collected
    pass


def test_strict_mode_fails_on_error(tmp_path):
    """Test that strict mode raises on first error."""
    # Run build with --strict
    # Assert it fails
    pass


def test_validate_flag(tmp_path):
    """Test --validate flag catches errors before build."""
    # Run bengal build --validate
    # Assert errors found
    pass
```

---

## 📅 Implementation Timeline

### Week 1: Foundation (Phase 1-2)
- **Day 1-2:** Create `errors.py` with rich error objects
- **Day 3-4:** Modify `Renderer` to use rich errors
- **Day 5:** Enhance `BuildStats` for error collection
- **Day 6-7:** Testing and refinement

### Week 2: Validation (Phase 3)
- **Day 1-2:** Create `validator.py`
- **Day 3:** Add `--validate` flag to CLI
- **Day 4-5:** Testing
- **Day 6-7:** Documentation

### Week 3: Polish (Phase 4-5)
- **Day 1-2:** Create `error_formatter.py`
- **Day 3-4:** Add `bengal lint` command
- **Day 5-6:** Final testing
- **Day 7:** Release preparation

---

## 🔄 Migration Path

### Backward Compatibility

1. **Old error handling still works** - New system wraps existing behavior
2. **No breaking changes** to API
3. **Graceful degradation** if new features not used

### Rollout Plan

1. **v1.0:** Implement Phase 1-2 (rich errors, collection)
2. **v1.1:** Add Phase 3 (validation)
3. **v1.2:** Add Phase 4-5 (formatting, lint command)

---

## 📊 Success Metrics

### Before
- ❌ No line numbers in errors
- ❌ 4+ rebuild cycles to find all issues
- ❌ Generic "template error" messages
- ❌ No context or suggestions

### After
- ✅ Line numbers + file paths
- ✅ 1 rebuild (all errors shown)
- ✅ Rich error messages with context
- ✅ Helpful suggestions
- ✅ Pre-build validation available
- ✅ IDE integration ready (JSON format)

---

## 🎯 Acceptance Criteria

- [ ] Error messages include file path and line number
- [ ] Template inclusion chains displayed for nested templates
- [ ] All template errors collected (not just first one)
- [ ] Available filters listed when unknown filter encountered
- [ ] `bengal build --validate` catches all errors upfront
- [ ] `bengal lint` command validates without building
- [ ] Error display uses colors and formatting
- [ ] Suggestions provided for common mistakes
- [ ] 100% backward compatible
- [ ] Full test coverage (unit + integration)
- [ ] Documentation updated

---

## 📝 Documentation Requirements

1. **User Guide:** Error message interpretation
2. **Developer Guide:** Adding custom error suggestions
3. **CLI Reference:** New flags and commands
4. **Architecture Doc:** Error handling flow

---

## 🚀 Quick Start (For Implementation)

1. Create `bengal/rendering/errors.py`
2. Modify `bengal/rendering/renderer.py` (lines 75-100)
3. Enhance `bengal/utils/build_stats.py`
4. Test with existing broken templates
5. Iterate on error display formatting

That's it! The architecture is designed to be incremental - each phase builds on the previous one.

