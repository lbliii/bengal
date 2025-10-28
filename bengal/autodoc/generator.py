"""
Documentation generator - renders DocElements to markdown using templates.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from bengal.autodoc.base import DocElement, Extractor
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class TemplateCache:
    """Cache rendered templates for performance."""

    def __init__(self):
        self.cache: dict[str, str] = {}
        self.template_hashes: dict[str, str] = {}

    def get_cache_key(self, template_name: str, element: DocElement) -> str:
        """Generate cache key from template + data."""
        template_hash = self.template_hashes.get(template_name, "")
        element_hash = hashlib.sha256(
            json.dumps(element.to_dict(), sort_keys=True).encode()
        ).hexdigest()[:8]

        return f"{template_name}:{element_hash}:{template_hash}"

    def get(self, key: str) -> str | None:
        """Get cached rendered template."""
        return self.cache.get(key)

    def set(self, key: str, rendered: str):
        """Cache rendered template."""
        self.cache[key] = rendered


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

        self.extractor = extractor
        self.config = config
        self.template_cache = template_cache or TemplateCache()
        self.max_workers = max_workers

        # Setup Jinja2 environment with template directories
        self.env = self._setup_template_env()

    def _setup_template_env(self) -> Environment:
        """Setup Jinja2 environment with template loaders."""
        template_dirs = []

        # User templates (highest priority)
        user_template_dir = Path("templates/autodoc") / self.extractor.get_template_dir()
        if user_template_dir.exists():
            template_dirs.append(str(user_template_dir))

        # Alternative user locations
        for alt_dir in ["templates/api", "templates/sdk"]:
            alt_path = Path(alt_dir)
            if alt_path.exists():
                template_dirs.append(str(alt_path))

        # Built-in templates (fallback)
        builtin_dir = Path(__file__).parent / "templates" / self.extractor.get_template_dir()
        if builtin_dir.exists():
            template_dirs.append(str(builtin_dir))

        logger.debug(
            "autodoc_template_env_setup", template_dirs=template_dirs, dir_count=len(template_dirs)
        )

        # Create Jinja2 environment
        env = Environment(
            loader=FileSystemLoader(template_dirs) if template_dirs else None,
            autoescape=False,  # We're generating markdown, not HTML
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters for autodoc
        env.filters["project_relative"] = self._make_path_project_relative

        return env

    def _make_path_project_relative(self, path: Path | str | None) -> str:
        """
        Convert absolute or relative path to project-relative format.

        Args:
            path: Path object or string

        Returns:
            Project-relative path string (e.g., 'bengal/core/site.py')
        """
        if not path:
            return ""

        from pathlib import Path as PathLib

        path_obj = PathLib(path) if not isinstance(path, PathLib) else path

        # Try to make it relative to current working directory (project root)
        try:
            cwd = PathLib.cwd()
            relative = path_obj.relative_to(cwd)
            return str(relative)
        except ValueError:
            # Path is not relative to cwd, try parent directories
            pass

        # Fallback: return just the filename or the path as-is
        # Look for common project root indicators
        parts = path_obj.parts
        for i, part in enumerate(parts):
            # If we find a project root indicator, return from there
            if part in ("bengal", "src", "lib", "app", "backend", "frontend"):
                return str(PathLib(*parts[i:]))

        # Last resort: return the path as a string
        return str(path_obj)

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

        if parallel and len(elements) > 3:
            result = self._generate_parallel(elements, output_dir)
        else:
            result = self._generate_sequential(elements, output_dir)

        logger.info(
            "autodoc_generation_complete", files_generated=len(result), output_dir=str(output_dir)
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
                if output_path.name == ".skip":
                    continue

                path = self.generate_single(element, output_dir)
                generated.append(path)
            except Exception as e:
                logger.error(
                    "autodoc_generation_failed", element=element.qualified_name, error=str(e)[:200]
                )

        return generated

    def _generate_parallel(self, elements: list[DocElement], output_dir: Path) -> list[Path]:
        """Generate documentation in parallel."""
        logger.debug(
            "autodoc_parallel_generation", element_count=len(elements), max_workers=self.max_workers
        )

        # Filter out elements marked for skipping
        elements_to_generate = [
            e for e in elements if self.extractor.get_output_path(e).name != ".skip"
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
                        error=str(e)[:200],
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

        # Check cache
        cache_key = self.template_cache.get_cache_key(template_name, element)
        cached = self.template_cache.get(cache_key)

        if cached:
            logger.debug(
                "autodoc_template_cache_hit", element=element.qualified_name, template=template_name
            )
            content = cached
        else:
            # Render template
            logger.debug(
                "autodoc_rendering_template", element=element.qualified_name, template=template_name
            )
            content = self._render_template(template_name, element)

            # Cache result
            self.template_cache.set(cache_key, content)

        # Determine output path
        output_path = output_dir / self.extractor.get_output_path(element)
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
        """Get template filename for element type."""
        # Map element types to template files
        type_map = {
            "module": "module.md.jinja2",
            "class": "class.md.jinja2",
            "function": "function.md.jinja2",
            "method": "function.md.jinja2",  # Methods use function template
            "endpoint": "endpoint.md.jinja2",
            "schema": "schema.md.jinja2",
            "command": "command.md.jinja2",
            "command-group": "command-group.md.jinja2",
        }

        template_name = type_map.get(element.element_type, f"{element.element_type}.md.jinja2")

        # Try with .jinja2 extension, fall back to .md
        try:
            self.env.get_template(template_name)
            return template_name
        except TemplateNotFound:
            # Try without .jinja2
            alt_name = template_name.replace(".jinja2", "")
            try:
                self.env.get_template(alt_name)
                return alt_name
            except TemplateNotFound:
                raise TemplateNotFound(
                    f"Template not found: {template_name} or {alt_name}. "
                    f"Create template in templates/autodoc/{self.extractor.get_template_dir()}/"
                ) from None

    def _render_template(self, template_name: str, element: DocElement) -> str:
        """Render template with element data."""
        template = self.env.get_template(template_name)

        # Build template context
        context = {
            "element": element,
            "config": self.config,
            "autodoc_config": self.config.get("autodoc", {}),
        }

        # Render
        return template.render(**context)
