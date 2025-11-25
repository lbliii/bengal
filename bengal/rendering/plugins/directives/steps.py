"""
Steps directive for Mistune.

Provides visual step-by-step guides using a container div.
Syntax:
    ```{steps}
    1. Step 1
    2. Step 2
    ```
"""

from __future__ import annotations

from mistune.directives import DirectivePlugin

from bengal.utils.logger import get_logger

__all__ = ["StepsDirective", "render_steps"]

logger = get_logger(__name__)


class StepsDirective(DirectivePlugin):
    """
    Steps directive for visual step-by-step guides.

    Syntax:
        ```{steps}
        1. First step
        2. Second step
        ```

    Renders as:
        <div class="steps">
            <ol>...</ol>
        </div>
    """

    def parse(self, block, m, state):
        """Parse steps directive."""
        content = self.parse_content(m)

        # Parse nested markdown content
        children = self.parse_tokens(block, content, state)

        return {
            "type": "steps",
            "children": children,
        }

    def __call__(self, directive, md):
        """Register steps directive."""
        directive.register("steps", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("steps", render_steps)


def render_steps(renderer, text: str) -> str:
    """Render steps container."""
    return f'<div class="steps">\n{text}</div>\n'

