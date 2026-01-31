"""Shared utilities for scaffold templates.

Provides common functions used across all template modules to reduce
code duplication and centralize file loading logic.
"""

from datetime import datetime
from pathlib import Path

# Date format used for template variable substitution
DATE_FORMAT = "%Y-%m-%d"

# Template variable placeholder for current date
DATE_PLACEHOLDER = "{{date}}"


def load_template_file(
    template_module_file: str,
    relative_path: str,
    *,
    subdir: str = "pages",
    replace_date: bool = False,
) -> str:
    """Load a file from a template directory with optional date substitution.

    This is the unified file loading function for all scaffold templates.
    It handles both content pages (from ``pages/``) and data files (from
    ``data/``), with optional ``{{date}}`` placeholder replacement.

    Args:
        template_module_file: Pass ``__file__`` from the calling template module.
            Used to resolve the template's directory.
        relative_path: File path relative to the subdir (e.g. ``"index.md"``
            or ``"posts/first-post.md"``).
        subdir: Subdirectory under the template dir. Common values are
            ``"pages"`` (default) and ``"data"``.
        replace_date: If ``True``, replaces ``{{date}}`` placeholders with
            the current date in ``YYYY-MM-DD`` format.

    Returns:
        The file contents as a string, with date substitution applied if
        requested.

    Example:
        >>> # In blog/template.py
        >>> content = load_template_file(__file__, "index.md", replace_date=True)
        >>> data = load_template_file(__file__, "config.yaml", subdir="data")

    """
    template_dir = Path(template_module_file).parent
    file_path = template_dir / subdir / relative_path

    content = file_path.read_text(encoding="utf-8")

    if replace_date:
        current_date = datetime.now().strftime(DATE_FORMAT)
        content = content.replace(DATE_PLACEHOLDER, current_date)

    return content


def get_current_date() -> str:
    """Return the current date formatted for template substitution.

    Returns:
        Current date as ``YYYY-MM-DD`` string.
    """
    return datetime.now().strftime(DATE_FORMAT)


def replace_date_placeholder(content: str) -> str:
    """Replace ``{{date}}`` placeholders with the current date.

    Args:
        content: String content potentially containing ``{{date}}`` placeholders.

    Returns:
        Content with all ``{{date}}`` occurrences replaced with current date.
    """
    return content.replace(DATE_PLACEHOLDER, get_current_date())
