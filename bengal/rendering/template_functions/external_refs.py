"""
External reference template functions for Bengal SSG.

Provides ext() and ext_exists() template functions for cross-project
documentation linking in Kida templates.

Usage in Templates:
    ```kida
    {# Basic external reference #}
    {{ ext('python', 'pathlib.Path') }}

    {# With custom text #}
    {{ ext('python', 'pathlib.Path', text='Path class') }}

    {# Conditional rendering #}
    {% if ext_exists('kida', 'Markup') %}
      See {{ ext('kida', 'Markup') }} for template escaping.
    {% end %}
    ```

Configuration:
External references are configured in bengal.toml:

    ```toml
    [external_refs]
    enabled = true

    [external_refs.templates]
    python = "https://docs.python.org/3/library/{module}.html#{name}"

    [[external_refs.indexes]]
    name = "kida"
    url = "https://lbliii.github.io/kida/xref.json"
    ```

See: plan/rfc-external-references.md

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from markupsafe import Markup

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.protocols import TemplateEnvironment
    from bengal.rendering.external_refs import ExternalRefResolver

logger = get_logger(__name__)


def register(
    env: TemplateEnvironment, site: Site, resolver: ExternalRefResolver | None = None
) -> None:
    """
    Register external reference template functions.
    
    Args:
        env: Kida template environment
        site: Site instance
        resolver: Optional pre-created resolver (creates one if not provided)
        
    """
    # Create resolver if not provided
    if resolver is None:
        from bengal.rendering.external_refs import ExternalRefResolver

        resolver = ExternalRefResolver(site.config)

    def ext(project: str, target: str, text: str | None = None) -> Markup:
        """
        Render an external reference link.

        Args:
            project: Project identifier (e.g., "python", "kida")
            target: Target within project (e.g., "pathlib.Path", "Markup")
            text: Optional custom link text

        Returns:
            Markup object with HTML link (safe for template rendering)

        Example:
            >>> ext('python', 'pathlib.Path')
            Markup('<a href="..." class="extref">Path</a>')

            >>> ext('python', 'pathlib.Path', text='Path class')
            Markup('<a href="..." class="extref">Path class</a>')
        """
        html = resolver.resolve(project, target, text)
        return Markup(html)

    def ext_exists(project: str, target: str) -> bool:
        """
        Check if an external reference can be resolved.

        Useful for conditional rendering when you're not sure if
        a reference exists.

        Args:
            project: Project identifier
            target: Target within project

        Returns:
            True if the reference can be resolved

        Example:
            ```kida
            {% if ext_exists('numpy', 'ndarray') %}
              See {{ ext('numpy', 'ndarray') }} for array operations.
            {% end %}
            ```
        """
        return resolver.can_resolve(project, target)

    # Register functions
    env.globals["ext"] = ext
    env.globals["ext_exists"] = ext_exists

    logger.debug(
        "external_ref_functions_registered",
        templates=len(resolver.templates),
    )
