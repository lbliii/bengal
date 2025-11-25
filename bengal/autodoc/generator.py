"""
Documentation generator - renders DocElements to markdown using templates.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
from pathlib import Path
from typing import Any, Final

from jinja2 import TemplateNotFound

from bengal.autodoc.base import DocElement, Extractor
from bengal.autodoc.error_reporter import TemplateErrorReporter
from bengal.autodoc.template_config import TemplateSafetyConfig
from bengal.autodoc.template_safety import (
    SafeTemplateRenderer,
    TemplateValidator,
    create_safe_environment,
)
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# Template type mappings - centralized configuration
TEMPLATE_TYPE_MAP: Final[dict[str, str]] = {
    "module": "python/module.md.jinja2",
    "class": "python/class.md.jinja2",
    "function": "python/function.md.jinja2",
    "method": "python/function.md.jinja2",  # Methods use function template
    "endpoint": "openapi/endpoint.md.jinja2",
    "schema": "openapi/schema.md.jinja2",
    "command": "cli/command.md.jinja2",
    "command-group": "cli/command_group.md.jinja2",
}

# Cache configuration constants
DEFAULT_CACHE_SIZE: Final[int] = 1000
CACHE_EVICTION_PERCENTAGE: Final[float] = 0.2  # Remove 20% when full
PARALLEL_THRESHOLD: Final[int] = 3  # Use parallel processing for >3 elements

# Error message truncation
ERROR_MESSAGE_MAX_LENGTH: Final[int] = 200

# Template discovery paths
ADDITIONAL_TEMPLATE_PATHS: Final[list[str]] = [
    "openapi/api_overview.md.jinja2",
    "base/base.md.jinja2",
    "base/error_fallback.md.jinja2",
]


class TemplateCache:
    """Cache rendered templates for performance with intelligent invalidation."""

    def __init__(self, max_size: int = DEFAULT_CACHE_SIZE):
        self.cache: dict[str, str] = {}
        self.template_hashes: dict[str, str] = {}
        self.access_times: dict[str, float] = {}
        self.max_size = max_size

    def get_cache_key(self, template_name: str, element: DocElement) -> str:
        """Generate cache key from template + data."""
        try:
            template_hash = self.template_hashes.get(template_name, "")

            # More efficient hashing - avoid string conversion for metadata
            metadata_hash = ""
            if element.metadata:
                try:
                    # Use hash of metadata dict directly instead of string conversion
                    if isinstance(element.metadata, dict):
                        metadata_hash = str(hash(frozenset(element.metadata.items())))
                    else:
                        metadata_hash = str(hash(str(element.metadata)))
                except (TypeError, ValueError):
                    # Fallback for unhashable metadata
                    metadata_hash = str(abs(hash(str(element.metadata))))

            element_data = (
                element.name or "",
                element.element_type or "",
                element.qualified_name or "",
                metadata_hash,
                len(element.children) if element.children else 0,
            )
            element_hash = hashlib.sha256(str(element_data).encode()).hexdigest()[:8]

            return f"{template_name}:{element_hash}:{template_hash}"
        except Exception as e:
            # Fallback to simple key if hashing fails
            logger.warning(
                "cache_key_generation_failed",
                template=template_name,
                element=element.name,
                error=str(e),
            )
            return f"{template_name}:fallback:{abs(hash(element.name or 'unknown'))}"

    def get(self, key: str) -> str | None:
        """Get cached rendered template."""
        import time

        if key in self.cache:
            self.access_times[key] = time.time()
            return self.cache[key]
        return None

    def set(self, key: str, rendered: str) -> None:
        """Cache rendered template with LRU eviction."""
        import time

        # Evict old entries if cache is full
        if len(self.cache) >= self.max_size:
            self._evict_lru()

        self.cache[key] = rendered
        self.access_times[key] = time.time()

    def _evict_lru(self) -> None:
        """
        Evict least recently used entries when cache is full.

        Removes the configured percentage of oldest entries to make room
        for new cache entries while maintaining performance.
        """
        if not self.access_times:
            return

        # Remove configured percentage of entries (oldest first)
        num_to_remove = max(1, int(len(self.cache) * CACHE_EVICTION_PERCENTAGE))
        sorted_keys = sorted(self.access_times.keys(), key=lambda k: self.access_times[k])

        for key in sorted_keys[:num_to_remove]:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)

    def clear(self) -> None:
        """Clear all cached content."""
        self.cache.clear()
        self.template_hashes.clear()
        self.access_times.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": getattr(self, "_hit_count", 0)
            / max(getattr(self, "_total_requests", 1), 1),
            "template_count": len(set(key.split(":")[0] for key in self.cache)),
        }


class DocumentationGenerator:
    """
    Generate documentation from DocElements using templates.

    Features:
    - Template hierarchy (user templates override built-in)
    - Template caching for performance
    - Parallel generation
    - Progress tracking
    """

    def __init__(
        self,
        extractor: Extractor,
        config: dict[str, Any],
        template_cache: TemplateCache | None = None,
        max_workers: int | None = None,
    ):
        """
        Initialize generator.

        Args:
            extractor: Extractor instance for this doc type
            config: Configuration dict
            template_cache: Optional template cache
            max_workers: Max parallel workers (None = auto-detect)
        """
        logger.debug(
            "initializing_autodoc_generator",
            extractor_type=extractor.__class__.__name__,
            max_workers=max_workers,
        )

        self._initialize_core_components(extractor, config, template_cache, max_workers)
        self._initialize_template_system()
        self._configure_caching()
        self._perform_initial_validation()
        self._log_initialization_complete()

    def _initialize_core_components(
        self,
        extractor: Extractor,
        config: dict[str, Any],
        template_cache: TemplateCache | None,
        max_workers: int | None,
    ) -> None:
        """Initialize core generator components."""
        if extractor is None:
            raise ValueError("Extractor cannot be None")
        if config is None:
            raise ValueError("Config cannot be None")
        if max_workers is not None and max_workers < 1:
            raise ValueError("max_workers must be positive or None")

        self.extractor = extractor
        self.config = config
        self.template_cache = template_cache or TemplateCache()
        self.max_workers = max_workers
        self.safety_config = TemplateSafetyConfig.from_config(config)
        self.error_reporter = TemplateErrorReporter()

    def _initialize_template_system(self) -> None:
        """Initialize the template safety system."""
        template_dirs = self._get_template_directories()
        self.env = create_safe_environment(template_dirs)
        self.safe_renderer = SafeTemplateRenderer(self.env)
        self.validator = TemplateValidator(self.env)

    def _configure_caching(self) -> None:
        """Configure template caching based on safety configuration."""
        if not self.safety_config.cache_templates:
            # Disable template caching if configured
            self.template_cache = TemplateCache(max_size=0)

    def _perform_initial_validation(self) -> None:
        """Perform initial template validation if enabled."""
        if self.safety_config.validate_templates:
            self._validate_all_templates()

    def _log_initialization_complete(self) -> None:
        """Log successful initialization."""
        template_dirs = self._get_template_directories()
        logger.info(
            "autodoc_generator_initialized",
            extractor_type=self.extractor.__class__.__name__,
            template_dirs=[str(d) for d in template_dirs],
            safety_config=self.safety_config.to_dict(),
            cache_enabled=self.safety_config.cache_templates,
        )

    def _get_template_directories(self) -> list[Path]:
        """Get list of template directories in priority order."""
        template_dirs = []

        # User templates (highest priority) - unified structure
        template_dirs.extend(self._discover_user_template_directories())

        # Built-in templates - unified structure
        template_dirs.extend(self._discover_builtin_template_directories())

        logger.debug(
            "autodoc_template_dirs_discovered",
            template_dirs=[str(d) for d in template_dirs],
            dir_count=len(template_dirs),
        )

        return template_dirs

    def _discover_user_template_directories(self) -> list[Path]:
        """Discover user template directories in priority order."""
        user_dirs = []

        # Primary user template location
        primary_dir = Path("templates/autodoc")
        if primary_dir.exists():
            user_dirs.append(primary_dir)

        # Alternative user locations for backward compatibility
        for alt_dir in ["templates/api", "templates/sdk"]:
            alt_path = Path(alt_dir)
            if alt_path.exists() and alt_path not in user_dirs:
                user_dirs.append(alt_path)

        return user_dirs

    def _discover_builtin_template_directories(self) -> list[Path]:
        """Discover built-in template directories."""
        builtin_dirs = []

        builtin_dir = Path(__file__).parent / "templates"
        if builtin_dir.exists():
            builtin_dirs.append(builtin_dir)

        return builtin_dirs

    def _validate_all_templates(self) -> None:
        """Validate all templates for common issues."""
        template_names = self._discover_template_names()

        for template_name in template_names:
            issues = self.validator.validate_template(template_name)
            if issues:
                for issue in issues:
                    self.error_reporter.record_warning(template_name, issue)

        if self.error_reporter.has_warnings():
            logger.warning(
                "template_validation_issues_found", warning_count=len(self.error_reporter.warnings)
            )

    def _discover_template_names(self) -> list[str]:
        """Discover all available template names by scanning template directories."""
        template_names = set()

        # Scan actual template directories for .jinja2 files
        for template_dir in self._get_template_directories():
            if template_dir.exists():
                for template_file in template_dir.rglob("*.jinja2"):
                    # Get relative path from template directory
                    relative_path = template_file.relative_to(template_dir)
                    template_names.add(str(relative_path))

        # Add expected templates from type mapping (for validation)
        template_names.update(TEMPLATE_TYPE_MAP.values())

        # Add additional common templates
        template_names.update(ADDITIONAL_TEMPLATE_PATHS)

        return sorted(template_names)

    def _make_path_project_relative(self, path: Path | str | None) -> str:
        """
        Convert absolute or relative path to project-relative format.

        Strategy:
        1. Resolve to absolute path
        2. Walk up parents to find project root (.git, pyproject.toml, bengal.toml)
        3. Return path relative to that root
        4. Fallback: Try relative to CWD
        5. Fallback: Use heuristic markers (src, lib, etc.)

        Args:
            path: Path object or string

        Returns:
            Project-relative path string (e.g., 'bengal/core/site.py')
        """
        if not path:
            return ""

        from pathlib import Path as PathLib

        # Ensure we have an absolute path object
        try:
            path_obj = PathLib(path).resolve()
        except OSError:
            # File might not exist or be accessible, fallback to basic path
            path_obj = PathLib(path)

        # 1. Search for project root markers starting from the file's directory
        # This is the most robust method as it doesn't depend on CWD
        try:
            current = path_obj.parent
            # Go up to root, but stop reasonable limit to avoid FS scan
            for _ in range(20):  
                if (current / ".git").exists() or \
                   (current / "pyproject.toml").exists() or \
                   (current / "bengal.toml").exists():
                    try:
                        return str(path_obj.relative_to(current))
                    except ValueError:
                        pass
                
                if current.parent == current:  # Root reached
                    break
                current = current.parent
        except Exception:
            pass

        # 2. Fallback: Try relative to current working directory
        try:
            cwd = PathLib.cwd()
            return str(path_obj.relative_to(cwd))
        except ValueError:
            pass

        # 3. Fallback: Heuristic for common folder structures
        # This is a last resort for when files are outside the project or markers are missing
        parts = path_obj.parts
        for i, part in enumerate(parts):
            # If we find a common source root indicator
            if part in ("bengal", "src", "lib", "app", "backend", "frontend"):
                # Handle repo/package name collision (e.g. bengal/bengal)
                # If the next part is identical, skip the first one (repo dir)
                if i + 1 < len(parts) and parts[i+1] == part:
                    return str(PathLib(*parts[i+1:]))
                return str(PathLib(*parts[i:]))

        # Last resort: return as-is
        return str(path)

    def generate_all(
        self, elements: list[DocElement], output_dir: Path, parallel: bool = True
    ) -> list[Path]:
        """
        Generate documentation for all elements.

        Args:
            elements: List of elements to document
            output_dir: Output directory for markdown files
            parallel: Use parallel processing

        Returns:
            List of generated file paths
        """
        logger.debug(
            "generating_autodoc",
            element_count=len(elements),
            output_dir=str(output_dir),
            parallel=parallel,
        )

        output_dir.mkdir(parents=True, exist_ok=True)

        if parallel and len(elements) > PARALLEL_THRESHOLD:
            result = self._generate_parallel(elements, output_dir)
        else:
            result = self._generate_sequential(elements, output_dir)

        # Create _index.md files for parent directories that don't have them
        self._create_parent_index_files(result, output_dir)

        # Report template errors if any occurred
        if self.error_reporter.has_errors() or self.error_reporter.has_warnings():
            error_summary = self.error_reporter.get_summary_report()
            logger.warning("template_errors_during_generation", summary=error_summary)

            # In debug mode, also log detailed report
            if self.safety_config.debug_mode:
                detailed_report = self.error_reporter.get_detailed_report()
                logger.debug("detailed_template_error_report", report=detailed_report)

        logger.info(
            "autodoc_generation_complete",
            files_generated=len(result),
            output_dir=str(output_dir),
            template_errors=self.error_reporter.get_error_count(),
            success_rate=f"{self.error_reporter.get_success_rate():.1f}%",
        )

        return result

    def _generate_sequential(self, elements: list[DocElement], output_dir: Path) -> list[Path]:
        """Generate documentation sequentially."""
        logger.debug("autodoc_sequential_generation", element_count=len(elements))

        generated = []

        for element in elements:
            try:
                # Check if element should be skipped (e.g., stripped prefix packages)
                output_path = self.extractor.get_output_path(element)
                if output_path is None:
                    continue

                path = self.generate_single(element, output_dir)
                generated.append(path)
            except Exception as e:
                logger.error(
                    "autodoc_generation_failed",
                    element=element.qualified_name,
                    error=str(e)[:ERROR_MESSAGE_MAX_LENGTH],
                )

        return generated

    def _generate_parallel(self, elements: list[DocElement], output_dir: Path) -> list[Path]:
        """Generate documentation in parallel."""
        logger.debug(
            "autodoc_parallel_generation", element_count=len(elements), max_workers=self.max_workers
        )

        # Filter out elements marked for skipping
        elements_to_generate = [
            e for e in elements if self.extractor.get_output_path(e) is not None
        ]

        generated = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.generate_single, element, output_dir): element
                for element in elements_to_generate
            }

            for future in concurrent.futures.as_completed(futures):
                element = futures[future]
                try:
                    path = future.result()
                    generated.append(path)
                except Exception as e:
                    logger.error(
                        "autodoc_parallel_generation_failed",
                        element=element.qualified_name,
                        error=str(e)[:ERROR_MESSAGE_MAX_LENGTH],
                    )

        return generated

    def generate_single(self, element: DocElement, output_dir: Path) -> Path:
        """
        Generate documentation for a single element.

        Args:
            element: Element to document
            output_dir: Output directory

        Returns:
            Path to generated file
        """
        logger.debug(
            "generating_autodoc_element",
            element=element.qualified_name,
            element_type=element.element_type,
        )

        # Get template name based on element type
        template_name = self._get_template_name(element)

        # Check cache if enabled
        content = None
        cache_key = None

        if self.safety_config.cache_rendered_content:
            cache_key = self.template_cache.get_cache_key(template_name, element)
            content = self.template_cache.get(cache_key)

            if content:
                logger.debug(
                    "autodoc_template_cache_hit",
                    element=element.qualified_name,
                    template=template_name,
                )
            else:
                logger.debug(
                    "autodoc_template_cache_miss",
                    element=element.qualified_name,
                    template=template_name,
                )

        if content is None:
            # Render template
            logger.debug(
                "autodoc_rendering_template", element=element.qualified_name, template=template_name
            )
            content = self._render_template(template_name, element)

            # Cache result if enabled and cache key exists
            if self.safety_config.cache_rendered_content and cache_key:
                self.template_cache.set(cache_key, content)

        # Determine output path
        relative_path = self.extractor.get_output_path(element)
        if relative_path is None:
            raise ValueError(
                f"Extractor returned None for output path of element: {element.qualified_name}"
            )

        output_path = output_dir / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        output_path.write_text(content, encoding="utf-8")

        logger.debug(
            "autodoc_element_generated",
            element=element.qualified_name,
            output_path=str(output_path),
            size_kb=len(content) / 1024,
        )

        return output_path

    def _get_template_name(self, element: DocElement) -> str:
        """
        Get template filename for element type.

        Args:
            element: DocElement to get template for

        Returns:
            Template name/path

        Raises:
            TemplateNotFound: If no suitable template exists
        """
        template_name = TEMPLATE_TYPE_MAP.get(
            element.element_type,
            f"generic/{element.element_type}.md.jinja2",  # Better fallback path
        )

        # Validate template exists (SafeTemplateRenderer will handle missing templates gracefully)
        try:
            self.env.get_template(template_name)
            return template_name
        except TemplateNotFound:
            logger.warning(
                "template_not_found_using_fallback",
                template=template_name,
                element_type=element.element_type,
                element_name=element.name,
            )
            # SafeTemplateRenderer will provide fallback content
            return template_name

    def _render_template(self, template_name: str, element: DocElement) -> str:
        """Render template with element data using safe rendering."""
        # Build template context
        # Note: self.config is already the autodoc config dict (from load_autodoc_config)
        # It contains github_repo, github_branch, python, cli, etc. at the top level
        context = {
            "element": element,
            "config": self.config,
            "autodoc_config": self.config,  # Same as config - autodoc config is already loaded
        }

        # Use safe renderer with error boundaries
        try:
            content = self.safe_renderer.render_with_boundaries(template_name, context)

            # Check if SafeTemplateRenderer had any errors during rendering
            if self.safe_renderer.error_count > 0:
                # Copy errors from SafeTemplateRenderer to our error reporter
                for error_record in self.safe_renderer.errors:
                    self.error_reporter.record_error(
                        error_record["template"],
                        Exception(error_record["error"]),
                        context,
                        error_record["error_type"],
                        used_fallback=True,
                    )
                # Clear SafeTemplateRenderer errors after copying
                self.safe_renderer.clear_errors()
            else:
                # Record successful render
                self.error_reporter.record_success(
                    template_name, getattr(element, "name", "Unknown")
                )

            return content

        except Exception as e:
            # This should rarely happen since SafeTemplateRenderer handles most errors
            self.error_reporter.record_error(
                template_name, e, context, "critical_failure", used_fallback=False
            )
            # Generate emergency fallback
            return self._generate_emergency_fallback(template_name, element, e)

    def _generate_emergency_fallback(
        self, template_name: str, element: DocElement, error: Exception
    ) -> str:
        """Generate emergency fallback content when safe renderer fails."""
        element_name = getattr(element, "name", "Unknown")
        element_type = getattr(element, "element_type", "Unknown")
        source_file = self._make_path_project_relative(getattr(element, "source_file", None))

        return f"""# {element_name}

```{{error}}
Critical Template System Failure
Template: {template_name}
Error Type: {type(error).__name__}
Error: {str(error)[:ERROR_MESSAGE_MAX_LENGTH]}{"..." if len(str(error)) > ERROR_MESSAGE_MAX_LENGTH else ""}
```

**Element Information:**
- Name: {element_name}
- Type: {element_type}
- Qualified Name: {getattr(element, "qualified_name", "Unknown")}
- Source: {source_file or "Unknown"}
- Line: {getattr(element, "line_number", "Unknown")}

**Troubleshooting:**
1. Check template syntax in `{template_name}`
2. Verify template directory structure
3. Review template safety configuration
4. Check element data completeness

*This is emergency fallback content. The template system should handle this gracefully.*
"""

    def get_error_report(self) -> str:
        """Get comprehensive error report from template rendering."""
        return self.error_reporter.get_summary_report()

    def get_detailed_error_report(self) -> str:
        """Get detailed error report for debugging."""
        return self.error_reporter.get_detailed_report()

    def has_template_errors(self) -> bool:
        """Check if any template errors occurred during generation."""
        return self.error_reporter.has_errors()

    def clear_errors(self) -> None:
        """Clear all recorded template errors."""
        self.error_reporter.clear()
        self.safe_renderer.clear_errors()

    def get_template_config(self) -> dict[str, Any]:
        """Get current template configuration for debugging."""
        return {
            "safety_config": self.safety_config.to_dict(),
            "template_directories": [str(d) for d in self._get_template_directories()],
            "cache_stats": self.template_cache.get_stats(),
            "error_stats": {
                "total_errors": self.error_reporter.get_error_count(),
                "success_rate": self.error_reporter.get_success_rate(),
                "has_warnings": self.error_reporter.has_warnings(),
            },
        }

    def export_error_report(self, output_path: Path) -> None:
        """
        Export comprehensive error report to file.

        Args:
            output_path: Path to write the error report
        """
        if self.safety_config.export_error_reports:
            self.error_reporter.export_errors_json(output_path)
            logger.info("template_error_report_exported", path=str(output_path))

    def validate_template_syntax(self, template_name: str) -> list[str]:
        """
        Validate a specific template for syntax issues.

        Args:
            template_name: Name of template to validate

        Returns:
            List of validation issues (empty if valid)
        """
        return self.validator.validate_template(template_name)

    def reload_templates(self) -> None:
        """
        Reload template environment and clear caches.
        Useful for development with hot-reloading.
        """
        logger.info("reloading_templates")

        # Clear caches
        self.template_cache.clear()
        self.safe_renderer.clear_errors()

        # Recreate environment
        template_dirs = self._get_template_directories()
        self.env = create_safe_environment(template_dirs)
        self.safe_renderer = SafeTemplateRenderer(self.env)
        self.validator = TemplateValidator(self.env)

        # Re-validate if enabled
        if self.safety_config.validate_templates:
            self._validate_all_templates()

        logger.info("templates_reloaded", template_dirs=[str(d) for d in template_dirs])

    def _create_parent_index_files(self, generated_paths: list[Path], output_dir: Path) -> None:
        """
        Create _index.md files for parent directories that don't have them.

        When generating nested documentation (e.g., cli/templates/base.md),
        we need to ensure parent directories have index files (e.g., cli/templates/_index.md).

        Args:
            generated_paths: List of paths to generated files
            output_dir: Root output directory
        """
        # Collect all parent directories
        parent_dirs: set[Path] = set()

        for path in generated_paths:
            # Get relative path from output_dir
            try:
                rel_path = path.relative_to(output_dir)
            except ValueError:
                # Path is not under output_dir, skip
                continue

            # Add all parent directories
            parent = rel_path.parent
            while parent != Path(".") and parent != Path():
                parent_dirs.add(output_dir / parent)
                parent = parent.parent

        # Create _index.md for each parent directory that doesn't have one
        for parent_dir in parent_dirs:
            index_file = parent_dir / "_index.md"
            if not index_file.exists():
                # Create a simple index file
                # Use the directory name as the title
                dir_name = parent_dir.name or "Documentation"
                content = f"""---
title: {dir_name.title()}
---

# {dir_name.title()}

This section contains documentation for {dir_name}.
"""
                index_file.write_text(content, encoding="utf-8")
                logger.debug(
                    "autodoc_parent_index_created",
                    path=str(index_file),
                    parent_dir=str(parent_dir),
                )
