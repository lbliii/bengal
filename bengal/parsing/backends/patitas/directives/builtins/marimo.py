"""Marimo reactive notebook directive for executable Python code blocks.

Provides:
- marimo: Executable Python code blocks using Marimo's reactive notebook system

Use cases:
- Interactive code examples in documentation
- Live Python computations with reactive outputs
- Executable tutorials and guides

Thread Safety:
Cell ID generation is protected by a threading lock for safe concurrent use.

HTML Output:
Renders Marimo island HTML when available, or a styled error fallback
with the source code in a collapsible details element.

"""

from __future__ import annotations

import threading
from collections.abc import Sequence
from dataclasses import dataclass, replace
from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from patitas.directives.options import DirectiveOptions
from patitas.nodes import Directive

from bengal.parsing.backends.patitas.directives.contracts import DirectiveContract
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Block
    from patitas.stringbuilder import StringBuilder

__all__ = ["MarimoDirective"]

logger = get_logger(__name__)

# Thread-safe cell ID counter
_cell_lock = threading.Lock()
_cell_counter = 0


def _next_cell_id() -> int:
    """Generate a unique cell ID (thread-safe)."""
    global _cell_counter
    with _cell_lock:
        _cell_counter += 1
        return _cell_counter


@dataclass(frozen=True, slots=True)
class MarimoOptions(DirectiveOptions):
    """Options for Marimo executable code block."""

    _aliases: ClassVar[dict[str, str]] = {"show-code": "show_code"}

    show_code: bool = True
    cache: bool = True
    label: str = ""

    # Computed attributes (populated during parse)
    code: str = ""
    cell_id: int = 0
    error: str = ""


class MarimoDirective:
    """
    Marimo reactive notebook directive for executable Python code blocks.

    Syntax:
        :::{marimo}
        :show-code: true
        :label: my-cell

        import pandas as pd
        df = pd.DataFrame({"a": [1, 2, 3]})
        df
        :::

    Output:
        <div class="marimo-cell" data-cell-id="1" data-label="my-cell">
          <!-- Marimo rendered output -->
        </div>

    Thread Safety:
        Cell ID counter is protected by threading.Lock.

    """

    names: ClassVar[tuple[str, ...]] = ("marimo",)
    token_type: ClassVar[str] = "marimo_cell"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[MarimoOptions]] = MarimoOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: MarimoOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build Marimo cell AST node."""
        code = content.strip() if content else ""
        cell_id = _next_cell_id()

        computed_opts = replace(
            options,
            code=code,
            cell_id=cell_id,
        )

        return Directive(
            location=location,
            name=name,
            title=title,
            options=computed_opts,
            children=tuple(children),
        )

    def render(
        self,
        node: Directive[MarimoOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render Marimo cell to HTML."""
        opts = node.options
        code = opts.code
        cell_id = opts.cell_id
        label = opts.label
        label_attr = f' data-label="{html_escape(label)}"' if label else ""

        try:
            from marimo import MarimoIslandGenerator

            generator = MarimoIslandGenerator()
            generator.add_code(
                code=code,
                display_code=opts.show_code,
                display_output=True,
            )
            generator.build()
            html = generator.render_html()

            sb.append(
                f'<div class="marimo-cell"'
                f' data-cell-id="{cell_id}"{label_attr}>\n'
            )
            sb.append(html)
            sb.append("\n</div>\n")

        except ImportError:
            self._render_error(
                sb,
                cell_id=cell_id,
                label_attr=label_attr,
                title="Marimo Not Installed",
                message=(
                    "Install Marimo to use executable code blocks: "
                    "<code>pip install marimo</code>"
                ),
                code=code,
            )

        except Exception as exc:
            logger.error(
                "marimo_execution_error",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            self._render_error(
                sb,
                cell_id=cell_id,
                label_attr=label_attr,
                title="Execution Error",
                message=html_escape(str(exc)),
                code=code,
            )

    def _render_error(
        self,
        sb: StringBuilder,
        *,
        cell_id: int,
        label_attr: str,
        title: str,
        message: str,
        code: str,
    ) -> None:
        """Render an error fallback for a Marimo cell."""
        code_escaped = html_escape(code)
        sb.append(
            f'<div class="marimo-cell marimo-error"'
            f' data-cell-id="{cell_id}"{label_attr}>\n'
        )
        sb.append('  <div class="admonition danger">\n')
        sb.append(f'    <p class="admonition-title">{title}</p>\n')
        sb.append(f"    <p>{message}</p>\n")
        sb.append("    <details>\n")
        sb.append("      <summary>Show code</summary>\n")
        sb.append(
            f'      <pre><code class="language-python">'
            f"{code_escaped}</code></pre>\n"
        )
        sb.append("    </details>\n")
        sb.append("  </div>\n")
        sb.append("</div>\n")
