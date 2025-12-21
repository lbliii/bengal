"""
Marimo directive for Mistune.

Provides executable Python code blocks with output rendering using Marimo's
reactive notebook system.
"""

from __future__ import annotations

from typing import Any

from mistune.directives import DirectivePlugin

from bengal.utils.logger import get_logger

__all__ = ["MarimoCellDirective", "render_marimo_cell"]

logger = get_logger(__name__)


class MarimoCellDirective(DirectivePlugin):
    """
    Marimo cell directive for executable Python code blocks.

    Syntax:
        ```{marimo}
        import pandas as pd
        pd.DataFrame({"x": [1, 2, 3]})
        ```

    Options:
        :show-code: true/false - Display source code (default: true)
        :cache: true/false - Cache execution results (default: true)
        :label: str - Cell identifier for caching and cross-references

    Features:
    - Execute Python code at build time
    - Render outputs (text, tables, plots, etc.)
    - Cache results for fast rebuilds
    - Show/hide source code
    - Graceful error handling

    Example:
        ```{marimo}
        :show-code: false
        :label: sales-data

        import pandas as pd
        data = pd.read_csv("sales.csv")
        data.head()
        ```
    """

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ["marimo"]

    def __init__(self) -> None:
        """Initialize Marimo directive."""
        self.cell_counter = 0
        self.generators: dict[str, Any] = {}  # Per-page generators
        self._marimo_available: bool | None = None  # Lazy check

    def _check_marimo_available(self) -> bool:
        """Check if Marimo is installed."""
        if self._marimo_available is None:
            try:
                import marimo  # noqa: F401

                self._marimo_available = True
            except ImportError:
                self._marimo_available = False
                logger.warning(
                    "marimo_not_installed",
                    info="Marimo not installed. Install with: pip install marimo",
                )
        return self._marimo_available

    def parse(self, block: Any, m: Any, state: Any) -> dict[str, Any]:
        """
        Parse Marimo cell directive.

        Args:
            block: Block parser
            m: Regex match
            state: Parser state

        Returns:
            Token dict with type and attributes
        """
        # Get code content
        code = self.parse_content(m)

        # Parse options (parse_options returns list of tuples, convert to dict)
        options = dict(self.parse_options(m))
        show_code = options.get("show-code", "true").lower() == "true"
        use_cache = options.get("cache", "true").lower() == "true"
        label = options.get("label", "")

        # Get page identifier from state (for per-page generators)
        page_id = str(state.env.get("page_id", "main"))

        # Execute cell and get HTML
        html = self._execute_cell(
            code=code, show_code=show_code, page_id=page_id, use_cache=use_cache, label=label
        )

        self.cell_counter += 1

        return {
            "type": "marimo_cell",
            "attrs": {
                "html": html,
                "cell_id": self.cell_counter,
                "label": label,
            },
        }

    def _execute_cell(
        self, code: str, show_code: bool, page_id: str, use_cache: bool = True, label: str = ""
    ) -> str:
        """
        Execute Python code using Marimo and return HTML output.

        Args:
            code: Python code to execute
            show_code: Whether to display source code
            page_id: Page identifier for generator caching
            use_cache: Whether to use cached results
            label: Optional label for the cell

        Returns:
            HTML representation of cell execution
        """
        # Check if Marimo is available
        if not self._check_marimo_available():
            return self._render_error(
                "Marimo Not Installed",
                "Install Marimo to use executable code blocks: <code>pip install marimo</code>",
                code,
            )

        # TODO: Implement caching
        # if use_cache and label:
        #     cached = self._get_from_cache(label, code)
        #     if cached:
        #         return cached

        try:
            from marimo import MarimoIslandGenerator

            # Get or create generator for this page
            # Each page gets its own generator to maintain execution context
            if page_id not in self.generators:
                self.generators[page_id] = MarimoIslandGenerator(app_id=page_id)

            generator = self.generators[page_id]

            # Add code cell to generator
            generator.add_code(
                code=code,
                display_code=show_code,
                display_output=True,
            )

            # Build the app and render to HTML
            generator.build()
            html: str = generator.render_html()

            # TODO: Store in cache
            # if use_cache and label:
            #     self._store_in_cache(label, code, html)

            return html

        except Exception as e:
            logger.error(
                "marimo_execution_error",
                error=str(e),
                error_type=type(e).__name__,
                code_preview=code[:100],
            )
            return self._render_error("Execution Error", str(e), code)

    def _render_error(self, title: str, message: str, code: str) -> str:
        """
        Render user-friendly error message.

        Args:
            title: Error title
            message: Error message
            code: Source code that caused the error

        Returns:
            HTML error display
        """
        # Escape HTML in code
        code_escaped = (
            code.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

        return f"""
        <div class="marimo-error admonition danger">
            <p class="admonition-title">{title}</p>
            <p>{message}</p>
            <details>
                <summary>Show code</summary>
                <pre><code class="language-python">{code_escaped}</code></pre>
            </details>
        </div>
        """

    def __call__(self, directive: Any, md: Any) -> Any:
        """
        Register directive with Mistune.

        Args:
            directive: FencedDirective instance
            md: Mistune Markdown instance

        Returns:
            Result of directive registration
        """
        directive.register("marimo", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("marimo_cell", render_marimo_cell)


def render_marimo_cell(renderer: Any, html: str, cell_id: int, label: str = "") -> str:
    """
    Render Marimo cell HTML output.

    Args:
        renderer: Mistune HTML renderer
        html: Cell HTML content
        cell_id: Numeric cell identifier
        label: Optional cell label

    Returns:
        Wrapped HTML with cell container
    """
    label_attr = f' data-label="{label}"' if label else ""
    return f'<div class="marimo-cell" data-cell-id="{cell_id}"{label_attr}>\n{html}\n</div>'
