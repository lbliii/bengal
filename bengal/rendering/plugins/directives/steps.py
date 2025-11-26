"""
Steps directive for Mistune.

Provides visual step-by-step guides using a container div.
Syntax:
    ```{steps}
    :::{step}
    Step 1 content
    :::

    :::{step}
    Step 2 content
    :::
    ```

Or with numbered list syntax (backward compatibility):
    ```{steps}
    1. Step 1
    2. Step 2
    ```
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from mistune.directives import DirectivePlugin

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    pass

__all__ = ["StepsDirective", "render_steps", "StepDirective", "render_step"]

logger = get_logger(__name__)


class StepDirective(DirectivePlugin):
    """
    Individual step directive (nested in steps).

    Syntax:
        :::{step} Optional Title
        :class: custom-class
        Step content with **markdown** and nested directives.
        :::

    Supports options:
        :class: Custom CSS class for the step
    """

    def parse(self, block, m, state):
        """
        Parse step directive.

        Follows the same pattern as other directives (AdmonitionDirective, DropdownDirective):
        - Extract title, options, and content using base class methods
        - Parse nested content with parse_tokens (handles nested directives automatically)
        - No manual content manipulation - let mistune handle it
        """
        title = self.parse_title(m)
        options = dict(self.parse_options(m))
        content = self.parse_content(m)

        # Parse nested markdown content - this allows nested directives
        # to work properly since we're parsing each step independently
        # parse_tokens handles all nested directives automatically
        children = self.parse_tokens(block, content, state)

        return {
            "type": "step",
            "attrs": {
                "title": title,
                **options,
            }
            if title or options
            else {},
            "children": children,
        }

    def __call__(self, directive, md):
        """Register step directive."""
        directive.register("step", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("step", render_step)


class StepsDirective(DirectivePlugin):
    """
    Steps directive for visual step-by-step guides.

    Syntax (preferred - supports nested directives):
        ::::{steps}
        :class: custom-class
        :style: compact
        :::{step}
        Step 1 content with nested :::{tip} directives
        :::

        :::{step}
        Step 2 content
        :::
        ::::

    Note: Parent container (steps) uses 4 colons, nested steps use 3 colons
    (one less fence item as per MyST nesting rules).

    Syntax (backward compatibility - limited nested directive support):
        ```{steps}
        1. Step 1
        2. Step 2
        ```

    Supports options:
        :class: Custom CSS class for the steps container
        :style: Step style (compact, default)

    Renders as:
        <div class="steps">
            <ol>...</ol>
        </div>
    """

    def parse(self, block, m, state):
        """
        Parse steps directive.

        Follows the same pattern as other container directives:
        - Extract options and content using base class methods
        - Parse nested content with parse_tokens (handles step directives automatically)
        - Detect heading level from state for semantic HTML
        """
        options = dict(self.parse_options(m))
        content = self.parse_content(m)

        # Detect parent heading level for semantic step titles
        heading_level = self._detect_heading_level(state)

        # Parse nested content - parse_tokens automatically recognizes :::{step} directives
        # No need to check for syntax manually - mistune handles it
        children = self.parse_tokens(block, content, state)

        # Inject heading_level into step tokens for proper semantic HTML
        children = self._inject_heading_level(children, heading_level)

        return {
            "type": "steps",
            "attrs": {**options, "heading_level": heading_level},
            "children": children,
        }

    def _inject_heading_level(self, children, heading_level: int):
        """
        Inject heading_level into step tokens.

        This allows step titles to render as proper headings (h2/h3/h4)
        based on the document structure.
        """
        if not isinstance(children, (list, tuple)):
            return children

        result = []
        for child in children:
            if isinstance(child, dict) and child.get("type") == "step":
                # Add heading_level to step attrs
                child.setdefault("attrs", {})["heading_level"] = heading_level
            result.append(child)
        return result

    def _detect_heading_level(self, state) -> int:
        """
        Detect the current heading level from parser state.

        Steps should render step titles as headings one level deeper than
        the parent heading (h1 -> h2, h2 -> h3, etc.).

        Returns the heading level (2-6) that steps should use.
        Defaults to h2 if no heading context found.
        """
        # Try to access state to find recent headings
        # This is a best-effort approach - if state structure changes, we gracefully default
        try:
            if hasattr(state, "tokens") and state.tokens:
                # Look backwards through tokens for the most recent heading
                for token in reversed(state.tokens):
                    if isinstance(token, dict) and token.get("type") == "heading":
                        level = token.get("attrs", {}).get("level", 2)
                        # Steps should be one level deeper than parent heading
                        return min(level + 1, 6)
        except (AttributeError, TypeError):
            # State structure may vary - gracefully handle
            pass

        # Default to h2 if no heading context found
        return 2

    def __call__(self, directive, md):
        """Register steps directive."""
        directive.register("steps", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("steps", render_steps)


def render_step(renderer, text: str, **attrs) -> str:
    """
    Render individual step to HTML.

    Step titles are rendered as headings (h2/h3/h4) based on parent heading level.
    The heading level is passed from the parent steps directive.
    """
    title = attrs.get("title", "")
    css_class = attrs.get("class", "").strip()
    heading_level = attrs.get("heading_level", 2)  # Default to h2

    # Parse title as inline markdown if present
    # Use mistune's inline parser if available, fallback to simple regex
    if title:
        title_html = _parse_inline_markdown(renderer, title)

        # Render title as heading based on detected level
        # heading_level comes from parent steps directive
        heading_tag = f"h{heading_level}"
        class_attr = f' class="{css_class}"' if css_class else ""
        return f'<li{class_attr}><{heading_tag} class="step-title">{title_html}</{heading_tag}>{text}</li>\n'

    class_attr = f' class="{css_class}"' if css_class else ""
    return f"<li{class_attr}>{text}</li>\n"


def _parse_inline_markdown(renderer, text: str) -> str:
    """
    Parse inline markdown in step titles.

    Tries to use mistune's inline parser first (proper way),
    falls back to simple regex for basic markdown if not available.
    """
    # Try to use mistune's inline parser (proper way)
    if hasattr(renderer, "_md"):
        md_instance = renderer._md
        if hasattr(md_instance, "inline"):
            try:
                return md_instance.inline(text)
            except Exception:
                pass
    elif hasattr(renderer, "md"):
        md_instance = renderer.md
        if hasattr(md_instance, "inline"):
            try:
                return md_instance.inline(text)
            except Exception:
                pass

    # Fallback to simple regex for basic markdown
    # **bold** -> <strong>bold</strong>
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # *italic* -> <em>italic</em> (but not if it's part of **bold**)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", text)
    # `code` -> <code>code</code>
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


def render_steps(renderer, text: str, **attrs) -> str:
    """Render steps container."""
    css_class = attrs.get("class", "").strip()
    style = attrs.get("style", "default").strip()

    # Build class string
    classes = ["steps"]
    if css_class:
        classes.append(css_class)
    if style and style != "default":
        classes.append(f"steps-{style}")

    class_str = " ".join(classes)

    # If text already contains <li> tags (from step directives or list parsing),
    # wrap in <ol>, otherwise wrap as-is
    if "<li>" in text:
        return f'<div class="{class_str}">\n<ol>\n{text}</ol>\n</div>\n'
    return f'<div class="{class_str}">\n{text}</div>\n'
