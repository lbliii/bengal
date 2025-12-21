"""
Target directive for explicit anchor targets.

Provides the {target} directive for creating anchor targets at arbitrary
locations in content, enabling stable cross-references that survive content
restructuring.

Architecture:
    Part of the explicit anchor system (RFC-explicit-anchor-targets):
    - Heading {#id} syntax: Custom IDs on headings
    - {target} directive: Anchors anywhere in content (this module)
    - :name: option: Anchors on existing directives (Phase 3)

Syntax:
    :::{target} my-anchor-id
    :::

    The target renders as an invisible anchor element (<span id="...">)
    that can be referenced via [[#my-anchor-id]] cross-reference syntax.

Use Cases:
    - Anchor before a note/warning that users should link to
    - Stable anchor that survives heading text changes
    - Anchor in middle of content (not tied to heading)
    - Migration from Sphinx (.. _label:) or MyST ((target)=) syntax

Related:
    - bengal/rendering/parsers/mistune.py: Heading {#id} syntax
    - bengal/rendering/plugins/cross_references.py: [[#anchor]] resolution
    - bengal/orchestration/content.py: xref_index["by_anchor"]
    - RFC: plan/active/rfc-explicit-anchor-targets.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.options import DirectiveOptions
from bengal.directives.tokens import DirectiveToken

__all__ = ["TargetDirective", "TargetOptions"]


@dataclass
class TargetOptions(DirectiveOptions):
    """
    Options for target directive.

    The target directive is intentionally simple - no options by default.
    The anchor ID is specified as the directive title.

    Example:
        :::{target} important-note
        :::
    """

    pass


class TargetDirective(BengalDirective):
    """
    Create an explicit anchor target at any location.

    Syntax:
        :::{target} my-anchor-id
        :::

    The target renders as an invisible anchor element that can be
    referenced via [[#my-anchor-id]] cross-reference syntax.

    Anchor ID Requirements:
        - Must start with a letter (a-z, A-Z)
        - May contain letters, numbers, hyphens, underscores
        - Case-sensitive in output, case-insensitive for resolution

    Use Cases:
        - Anchor before a note/warning that users should link to
        - Stable anchor that survives content restructuring
        - Migration from Sphinx's ``.. _label:`` syntax

    Example:
        :::{target} important-caveat
        :::

        :::{warning}
        This caveat is critical for production use.
        :::

        See [[#important-caveat|the caveat]] for details.

    Note:
        The anchor is invisible - it renders as an empty <span> element.
        Any content inside the directive is ignored (anchors are point targets).
    """

    NAMES: ClassVar[list[str]] = ["target", "anchor"]
    TOKEN_TYPE: ClassVar[str] = "target"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = TargetOptions

    # For backward compatibility with health check introspection
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["target", "anchor"]

    # Validation pattern for anchor IDs
    # Must start with letter, contain only letters, numbers, hyphens, underscores
    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")

    def validate_id(self, anchor_id: str) -> str | None:
        """
        Validate anchor ID format.

        Args:
            anchor_id: The anchor ID to validate

        Returns:
            Error message if invalid, None if valid
        """
        if not anchor_id:
            return "Target directive requires an ID"
        if not self.ID_PATTERN.match(anchor_id):
            return (
                f"Invalid anchor ID: {anchor_id!r}. "
                f"Must start with letter, contain only letters, numbers, hyphens, underscores."
            )
        return None

    def parse_directive(
        self,
        title: str,
        options: TargetOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """
        Build target token from parsed components.

        The anchor ID is taken from the title. Content is ignored
        since targets are point anchors, not containers.

        Args:
            title: The anchor ID (from directive title)
            options: Parsed options (unused for target)
            content: Raw content inside directive (ignored)
            children: Parsed children (ignored)
            state: Parser state

        Returns:
            DirectiveToken with anchor ID in attrs
        """
        anchor_id = title.strip()

        error = self.validate_id(anchor_id)
        if error:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={"error": error, "id": anchor_id},
                children=[],
            )

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={"id": anchor_id},
            children=[],  # Targets never have children
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """
        Render target as invisible anchor element.

        The anchor renders as an empty <span> with the target ID.
        CSS class "target-anchor" allows styling if needed (e.g., scroll offset).

        Args:
            renderer: Mistune renderer instance
            text: Rendered children (empty for targets)
            **attrs: Attributes from token (id, error)

        Returns:
            HTML anchor element (invisible by default)
        """
        error = attrs.get("error")
        if error:
            return (
                f'<span class="directive-error" '
                f'title="{self.escape_html(error)}">[target error]</span>\n'
            )

        anchor_id = attrs.get("id", "")
        # Invisible anchor element - no visual output
        # The class allows CSS to add scroll-margin-top for fixed headers
        return f'<span id="{self.escape_html(anchor_id)}" class="target-anchor"></span>\n'
