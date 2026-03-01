"""
Link skip rules for validation.

Determines which links should be skipped during validation (treated as valid).
Extracted from bengal/health/validators/links.py.

Used by: bengal/health/validators/links.py
"""


def should_skip_link(link: str) -> bool:
    """
    Return True if link should be skipped during validation (external, template syntax, etc.).

    Skipped links are treated as valid without checking against the page URL index.
    Includes: external (http/https/mailto/tel), data URLs, template syntax,
    and .py source file references.

    Args:
        link: Link URL to check

    Returns:
        True if link should be skipped (treat as valid), False otherwise
    """
    # External links - validated separately by async link checker
    if link.startswith(("http://", "https://", "mailto:", "tel:")):
        return True

    # Data URLs
    if link.startswith("data:"):
        return True

    # Template syntax (Jinja2, JavaScript template literals, etc.)
    # Appears in documentation code examples, not real links
    if "{{" in link or "}}" in link or "${" in link:
        return True

    # Source file references (common in autodoc-generated content)
    # "View Source" links pointing to Python files, not doc pages
    return ".py" in link and (link.endswith(".py") or ".py#" in link)
