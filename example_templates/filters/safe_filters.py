# Custom Jinja2 filters for safer template rendering


def safe_description(text):
    """Safely format description text for YAML frontmatter."""
    if not text:
        return "Python module documentation"

    # Remove problematic characters for YAML
    lines = text.split("\n")
    clean_lines = [line for line in lines if not line.strip().startswith("#")]
    result = " ".join(clean_lines)

    # Truncate and escape
    result = result[:200]
    if len(result) == 200:
        result += "..."

    # Escape quotes for YAML
    return result.replace('"', '\\"')


def code_or_dash(value):
    """Wrap in code backticks if not dash."""
    if value == "-" or not value:
        return "-"
    return f"`{value}`"


def safe_anchor(text):
    """Generate safe anchor links."""
    if not text:
        return ""
    return text.lower().replace(" ", "-").replace(".", "-")


# Register filters
SAFE_FILTERS = {
    "safe_description": safe_description,
    "code_or_dash": code_or_dash,
    "safe_anchor": safe_anchor,
}
