"""
Code tabs directive for Mistune.

Provides multi-language code examples with tabbed interface for easy
comparison across programming languages.

"""

from __future__ import annotations

import html as html_lib
import re
from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.options import DirectiveOptions
from bengal.utils.hashing import hash_str
from bengal.utils.logger import get_logger

__all__ = ["CodeTabsDirective", "CodeTabsOptions"]

logger = get_logger(__name__)

# Pre-compiled regex patterns
_CODE_TAB_SPLIT_PATTERN = re.compile(r"^### (?:Tab: )?(.+)$", re.MULTILINE)
_CODE_BLOCK_EXTRACT_PATTERN = re.compile(r"```\w*\n(.*?)```", re.DOTALL)
_CODE_TAB_ITEM_PATTERN = re.compile(
    r'<div class="code-tab-item" data-lang="(.*?)" data-code="(.*?)"></div>', re.DOTALL
)


@dataclass
class CodeTabsOptions(DirectiveOptions):
    """Options for code-tabs directive (currently none)."""

    pass


class CodeTabsDirective(BengalDirective):
    """
    Code tabs for multi-language examples.

    Syntax:
        ````{code-tabs}

        ### Tab: Python
        ```python
        # Example code here
        ```

        ### Tab: JavaScript
        ```javascript
        console.log("hello")
        ```
        ````

    Aliases: code-tabs, code_tabs
    """

    NAMES: ClassVar[list[str]] = ["code-tabs", "code_tabs"]
    TOKEN_TYPE: ClassVar[str] = "code_tabs"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = CodeTabsOptions

    DIRECTIVE_NAMES: ClassVar[list[str]] = ["code-tabs", "code_tabs"]

    def parse_directive(
        self,
        title: str,
        options: CodeTabsOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> dict[str, Any]:
        """
        Build code tabs token by parsing tab markers in content.

        Note: Returns dict instead of DirectiveToken because children
        are custom code_tab_item tokens, not parsed markdown.
        """
        # Split by tab markers
        parts = _CODE_TAB_SPLIT_PATTERN.split(content)

        tabs: list[dict[str, Any]] = []
        if len(parts) > 1:
            start_idx = 1 if not parts[0].strip() else 0

            for i in range(start_idx, len(parts), 2):
                if i + 1 < len(parts):
                    lang = parts[i].strip()
                    code_content = parts[i + 1].strip()

                    # Extract code from fenced block if present
                    code_match = _CODE_BLOCK_EXTRACT_PATTERN.search(code_content)
                    code = code_match.group(1).strip() if code_match else code_content

                    tabs.append(
                        {
                            "type": "code_tab_item",
                            "attrs": {"lang": lang, "code": code},
                        }
                    )

        return {"type": "code_tabs", "children": tabs}

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render code tabs to HTML."""
        # Stable IDs are critical for deterministic builds and output diffs.
        # Previous behavior used `id(text)` which varies between runs/processes.
        tab_id = f"code-tabs-{hash_str(text or '', truncate=12)}"

        # Extract code blocks from rendered text
        matches = _CODE_TAB_ITEM_PATTERN.findall(text)

        if not matches:
            return f'<div class="code-tabs" data-bengal="tabs">{text}</div>'

        # Build navigation
        nav_html = (
            f'<div class="code-tabs" id="{tab_id}" data-bengal="tabs">\n  <ul class="tab-nav">\n'
        )
        for i, (lang, _) in enumerate(matches):
            active = ' class="active"' if i == 0 else ""
            nav_html += (
                f'    <li{active}><a href="#" data-tab-target="{tab_id}-{i}">{lang}</a></li>\n'
            )
        nav_html += "  </ul>\n"

        # Build content
        content_html = '  <div class="tab-content">\n'
        for i, (lang, code) in enumerate(matches):
            active = " active" if i == 0 else ""
            code = html_lib.unescape(code)
            content_html += (
                f'    <div id="{tab_id}-{i}" class="tab-pane{active}">\n'
                f'      <pre><code class="language-{lang}">{code}</code></pre>\n'
                f"    </div>\n"
            )
        content_html += "  </div>\n</div>\n"

        return nav_html + content_html


# Backward compatibility render functions


def render_code_tab_item(renderer: Any, **attrs: Any) -> str:
    """Render code tab item marker (used internally)."""
    lang = attrs.get("lang", "text")
    code = attrs.get("code", "")
    code_escaped = html_lib.escape(code)
    return f'<div class="code-tab-item" data-lang="{lang}" data-code="{code_escaped}"></div>'
