"""
Notebook to Markdown converter for Bengal.

Converts Jupyter notebook (.ipynb) JSON to (markdown_content, metadata)
in the same shape as Markdown files with frontmatter. Extracts metadata
from notebook.metadata (Jupyter Book / JupyterLab conventions) and
converts cells to Markdown with fenced code blocks and output rendering.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import nbformat

from bengal.utils.io.file_io import read_text_file
from bengal.utils.observability.logger import get_logger
from bengal.utils.primitives.text import humanize_slug

logger = get_logger(__name__)


class NotebookConverter:
    """
    Converts Jupyter notebooks to Markdown content and metadata.

    Produces (content, metadata) compatible with ContentParser output,
    suitable for downstream Markdown parsing and rendering.
    """

    @classmethod
    def convert(cls, file_path: Path, file_content: str | None = None) -> tuple[str, dict[str, Any]]:
        """
        Convert a notebook file to Markdown content and metadata.

        Args:
            file_path: Path to .ipynb file
            file_content: Optional pre-read content (avoids double read when caching)

        Returns:
            Tuple of (markdown_content, metadata_dict)

        Raises:
            OSError: If file cannot be read
        """
        if file_content is None:
            file_content = read_text_file(
                file_path, fallback_encoding="utf-8", on_error="raise", caller="notebook_converter"
            )

        nb = nbformat.reads(file_content, as_version=4)

        metadata = cls._extract_metadata(nb, file_path)
        content = cls._cells_to_markdown(nb)

        return content, metadata

    @classmethod
    def _extract_metadata(cls, nb: Any, file_path: Path) -> dict[str, Any]:
        """Extract metadata from notebook for frontmatter-like use."""
        nb_meta = nb.get("metadata", {})

        # Jupyter Book / JupyterLab conventions
        title = (
            nb_meta.get("title")
            or nb_meta.get("jupytext", {}).get("text_representation", {}).get("display_name")
            or humanize_slug(file_path.stem)
        )
        if isinstance(title, dict):
            title = title.get("display_name", humanize_slug(file_path.stem))

        metadata: dict[str, Any] = {
            "title": title,
            "type": "notebook",
            "notebook": {
                "cell_count": len(nb.get("cells", [])),
                "kernel_name": nb_meta.get("kernelspec", {}).get("name", ""),
                "language_version": nb_meta.get("kernelspec", {}).get("language", ""),
            },
        }

        # Copy common frontmatter fields from notebook metadata
        for key in ("date", "tags", "authors", "summary", "description"):
            if key in nb_meta and nb_meta[key] is not None:
                metadata[key] = nb_meta[key]

        # Jupyter Book specific
        if "jupytext" in nb_meta:
            jt = nb_meta["jupytext"]
            if isinstance(jt, dict) and "formats" in jt:
                metadata.setdefault("format", "ipynb")

        return metadata

    @classmethod
    def _cells_to_markdown(cls, nb: Any) -> str:
        """Convert notebook cells to Markdown string."""
        parts: list[str] = []
        cells = nb.get("cells", [])

        for cell in cells:
            cell_type = cell.get("cell_type", "code")
            source = cell.get("source", [])
            if isinstance(source, str):
                source = [source]
            text = "".join(source).rstrip()

            if cell_type == "markdown":
                if text:
                    parts.append(text)
                    parts.append("\n\n")
            elif cell_type == "code":
                lang = _infer_code_language(cell)
                parts.append(f"```{lang}\n{text}\n```\n\n")
                # Append outputs
                for output in cell.get("outputs", []):
                    out_md = cls._output_to_markdown(output)
                    if out_md:
                        parts.append(out_md)
                        parts.append("\n\n")
            elif cell_type == "raw":
                if text:
                    parts.append(text)
                    parts.append("\n\n")

        return "".join(parts).rstrip()

    @classmethod
    def _output_to_markdown(cls, output: dict[str, Any]) -> str:
        """Convert a single output to Markdown/HTML."""
        output_type = output.get("output_type", "")
        data = output.get("data", {})
        text = output.get("text", [])

        if output_type == "stream":
            if isinstance(text, str):
                content = text
            else:
                content = "".join(text) if text else ""
            if content.strip():
                return f"<pre>{_escape_html(content)}</pre>"
            return ""

        if output_type == "execute_result" or output_type == "display_data":
            # Prefer image outputs
            for mime in ("image/png", "image/jpeg", "image/gif", "image/svg+xml"):
                if mime in data:
                    b64 = data[mime]
                    if isinstance(b64, list):
                        b64 = "".join(b64)
                    return f'<img src="data:{mime};base64,{b64}" alt="output" />'

            # Text/plain fallback
            if "text/plain" in data:
                plain = data["text/plain"]
                if isinstance(plain, list):
                    plain = "".join(plain)
                if plain.strip():
                    return f"<pre>{_escape_html(plain)}</pre>"
            return ""

        if output_type == "error":
            ename = output.get("ename", "Error")
            evalue = output.get("evalue", "")
            traceback = output.get("traceback", [])
            tb_text = "\n".join(traceback) if traceback else f"{ename}: {evalue}"
            return f"<pre class=\"notebook-error\">{_escape_html(tb_text)}</pre>"

        return ""


def _infer_code_language(cell: dict[str, Any]) -> str:
    """Infer language for code cell from metadata."""
    meta = cell.get("metadata", {})
    lang = meta.get("language", "") or meta.get("jupytext", {}).get("language_id", "")
    if isinstance(lang, str) and lang:
        return lang
    return "python"


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
