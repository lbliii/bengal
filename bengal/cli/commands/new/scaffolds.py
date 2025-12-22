"""
Scaffold generation commands for pages, layouts, partials, and themes.

Provides CLI commands for creating new content and template scaffolds.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import click

from bengal.cli.helpers import command_metadata, get_cli_output, handle_cli_errors
from bengal.utils.atomic_write import atomic_write_text

from .site import slugify


@click.command("page")
@command_metadata(
    category="content",
    description="Create a new page",
    examples=[
        "bengal new page my-page",
        "bengal new page 'My Page' --section blog",
    ],
    requires_site=True,
    tags=["content", "quick"],
)
@handle_cli_errors(show_art=False)
@click.argument("name")
@click.option("--section", default="", help="Section to create page in")
def page_command(name: str, section: str) -> None:
    """
    📄 Create a new page.

    The page name will be automatically slugified for the filename.
    Example: "My Awesome Page" → my-awesome-page.md
    """
    cli = get_cli_output()

    # Ensure we're in a Bengal site
    content_dir = Path("content")
    if not content_dir.exists():
        cli.error("Not in a Bengal site directory!")
        raise click.Abort()

    # Slugify the name for filename
    slug = slugify(name)

    # Use original name for title (capitalize properly)
    title = name.replace("-", " ").title()

    # Determine page path
    if section:
        page_dir = content_dir / section
        page_dir.mkdir(parents=True, exist_ok=True)
    else:
        page_dir = content_dir

    # Create page file with slugified name
    page_path = page_dir / f"{slug}.md"

    if page_path.exists():
        cli.error(f"Page {page_path} already exists!")
        raise click.Abort()

    # Create page content with current timestamp
    page_content = f"""---
title: {title}
date: {datetime.now().isoformat()}
---

# {title}

Your content goes here.
"""
    atomic_write_text(page_path, page_content)

    cli.blank()
    cli.success(f"✨ Created new page: {page_path}")
    cli.blank()


@click.command("layout")
@command_metadata(
    category="templates",
    description="Create a new layout template",
    examples=[
        "bengal new layout article",
        "bengal new layout post",
    ],
    requires_site=True,
    tags=["templates", "theming"],
)
@handle_cli_errors(show_art=False)
@click.argument("name", required=False)
def layout_command(name: str) -> None:
    """
    📋 Create a new layout template.

    Layouts are reusable HTML templates used by pages.
    Example: "article" → templates/layouts/article.html

    See also:
        bengal new partial - Create a partial template
        bengal new theme - Create a theme scaffold
    """
    cli = get_cli_output()

    # Ensure we're in a Bengal site
    templates_dir = Path("templates")
    if not templates_dir.exists():
        cli.error("Not in a Bengal site directory!")
        raise click.Abort()

    if not name:
        name = cli.prompt("Enter layout name")
        if not name:
            cli.warning("✨ Cancelled.")
            raise click.Abort()

    # Slugify the name for filename
    slug = slugify(name)
    layout_dir = templates_dir / "layouts"
    layout_dir.mkdir(parents=True, exist_ok=True)
    layout_path = layout_dir / f"{slug}.html"

    if layout_path.exists():
        cli.error(f"Layout {layout_path} already exists!")
        raise click.Abort()

    # Create layout template
    layout_content = """{% extends "base.html" %}

{% block content %}
{# Your layout content here #}
{{ page.content | safe }}
{% endblock %}
"""
    atomic_write_text(layout_path, layout_content)

    cli.blank()
    cli.success(f"✨ Created new layout: {layout_path}")
    cli.info(f"   └─ Extend this in pages with: layout: {slug}")
    cli.blank()


@click.command("partial")
@command_metadata(
    category="templates",
    description="Create a new partial template",
    examples=[
        "bengal new partial header",
        "bengal new partial footer",
    ],
    requires_site=True,
    tags=["templates", "theming"],
)
@handle_cli_errors(show_art=False)
@click.argument("name", required=False)
def partial_command(name: str) -> None:
    """
    🧩 Create a new partial template.

    Partials are reusable template fragments included in other templates.
    Example: "sidebar" → templates/partials/sidebar.html

    See also:
        bengal new layout - Create a layout template
        bengal new theme - Create a theme scaffold
    """
    cli = get_cli_output()

    # Ensure we're in a Bengal site
    templates_dir = Path("templates")
    if not templates_dir.exists():
        cli.error("Not in a Bengal site directory!")
        raise click.Abort()

    if not name:
        name = cli.prompt("Enter partial name")
        if not name:
            cli.warning("✨ Cancelled.")
            raise click.Abort()

    # Slugify the name for filename
    slug = slugify(name)
    partial_dir = templates_dir / "partials"
    partial_dir.mkdir(parents=True, exist_ok=True)
    partial_path = partial_dir / f"{slug}.html"

    if partial_path.exists():
        cli.error(f"Partial {partial_path} already exists!")
        raise click.Abort()

    # Create partial template
    partial_content = f"""{{# Partial: {slug} #}}
{{# Include in templates with: {{% include "partials/{slug}.html" %}} #}}

<div class="partial partial-{slug}">
  {{# Your partial content here #}}
</div>
"""
    atomic_write_text(partial_path, partial_content)

    cli.blank()
    cli.success(f"✨ Created new partial: {partial_path}")
    cli.info(f'   └─ Include in templates with: {{% include "partials/{slug}.html" %}}')
    cli.blank()


@click.command("theme")
@command_metadata(
    category="templates",
    description="Create a new theme scaffold with templates and assets",
    examples=[
        "bengal new theme my-theme",
    ],
    requires_site=False,
    tags=["templates", "theming", "setup"],
)
@handle_cli_errors(show_art=False)
@click.argument("name", required=False)
def theme_command(name: str) -> None:
    """
    Create a new theme scaffold.

    Themes are self-contained template and asset packages.
    Example: "my-theme" → themes/my-theme/ with templates, partials, and assets

    See also:
        bengal new layout - Create a layout template
        bengal new partial - Create a partial template
    """
    cli = get_cli_output()

    if not name:
        name = cli.prompt("Enter theme name")
        if not name:
            cli.warning("✨ Cancelled.")
            raise click.Abort()

    # Slugify the name for directory
    slug = slugify(name)

    # Determine if we're in a site or creating standalone
    in_site = Path("content").exists() and Path("bengal.toml").exists()

    theme_path = (Path("themes") / slug) if in_site else Path(slug)

    if theme_path.exists():
        cli.error(f"Theme directory {theme_path} already exists!")
        raise click.Abort()

    # Create theme directory structure
    _create_theme_structure(theme_path)

    cli.blank()
    cli.header(f"🎨 Creating new theme: {name}")
    cli.info(f"   → {theme_path}")
    cli.info("   ├─ Created directory structure")

    # Create templates
    _create_theme_templates(theme_path, name)
    cli.info("   ├─ Created 4 templates")
    cli.info("   ├─ Created 2 partials")

    # Create assets
    _create_theme_assets(theme_path, name)
    cli.info("   ├─ Created CSS stylesheet")
    cli.info("   └─ Created JavaScript")

    cli.blank()
    cli.success("✅ Theme created successfully!")

    # Show next steps
    cli.subheader("Next steps:", icon="📚")
    if in_site:
        cli.tip(f'Update bengal.toml: theme = "{slug}"')
        cli.tip("Run 'bengal serve'")
    else:
        cli.tip(f"Package as: bengal-theme-{slug}")
        cli.tip("Add to pyproject.toml for distribution")
        cli.tip("pip install -e .")
    cli.blank()


def _create_theme_structure(theme_path: Path) -> None:
    """Create theme directory structure."""
    theme_path.mkdir(parents=True)
    (theme_path / "templates").mkdir()
    (theme_path / "templates" / "partials").mkdir()
    (theme_path / "assets" / "css").mkdir(parents=True)
    (theme_path / "assets" / "js").mkdir(parents=True)
    (theme_path / "assets" / "images").mkdir(parents=True)


def _create_theme_templates(theme_path: Path, name: str) -> None:
    """Create theme template files."""
    # Base template
    base_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{{ site.config.title }}{% endblock %}</title>
    <meta name="description" content="{% block description %}{{ site.config.description | default('', true) }}{% endblock %}">
    <link rel="stylesheet" href="{{ url_for('assets/css/style.css') }}">
    {% block extra_head %}{% endblock %}
</head>
<body>
    {% include "partials/header.html" %}

    <main>
        {% block content %}{% endblock %}
    </main>

    {% include "partials/footer.html" %}

    <script src="{{ url_for('assets/js/main.js') }}"></script>
    {% block extra_scripts %}{% endblock %}
</body>
</html>
"""
    atomic_write_text(theme_path / "templates" / "base.html", base_template)

    # Header partial
    header_partial = """<header class="site-header">
    <div class="container">
        <div class="site-title">
            <h1><a href="{{ site.config.baseurl }}">{{ site.config.title }}</a></h1>
        </div>
        <nav class="site-nav">
            {% for menu_item in site.menu.get('main', []) %}
                <a href="{{ menu_item.url }}">{{ menu_item.name }}</a>
            {% endfor %}
        </nav>
    </div>
</header>
"""
    atomic_write_text(theme_path / "templates" / "partials" / "header.html", header_partial)

    # Footer partial
    footer_partial = """<footer class="site-footer">
    <div class="container">
        <p>&copy; {{ get_current_year() }} {{ site.config.title }}</p>
    </div>
</footer>
"""
    atomic_write_text(theme_path / "templates" / "partials" / "footer.html", footer_partial)

    # Home template
    home_template = """{% extends "base.html" %}

{% block content %}
<div class="home">
    <h1>Welcome to {{ site.config.title }}</h1>
    <p>{{ site.config.description | default('', true) }}</p>
</div>
{% endblock %}
"""
    atomic_write_text(theme_path / "templates" / "home.html", home_template)

    # Page template
    page_template = """{% extends "base.html" %}

{% block title %}{{ page.title }} - {{ site.config.title }}{% endblock %}

{% block content %}
<article class="page">
    <header class="page-header">
        <h1>{{ page.title }}</h1>
        {% if page.date %}
        <time datetime="{{ page.date | date_iso }}">{{ page.date | strftime('%B %d, %Y') }}</time>
        {% endif %}
    </header>
    <div class="page-content">
        {{ page.content | safe }}
    </div>
</article>
{% endblock %}
"""
    atomic_write_text(theme_path / "templates" / "page.html", page_template)


def _create_theme_assets(theme_path: Path, name: str) -> None:
    """Create theme asset files."""
    # CSS
    css_content = f"""/* Theme: {name} */

:root {{
    --primary-color: #007bff;
    --secondary-color: #6c757d;
    --text-color: #333;
    --bg-color: #fff;
}}

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    color: var(--text-color);
    background-color: var(--bg-color);
    line-height: 1.6;
}}

.container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1rem;
}}

.site-header {{
    background: var(--primary-color);
    color: white;
    padding: 2rem 0;
    margin-bottom: 2rem;
}}

.site-footer {{
    background: var(--secondary-color);
    color: white;
    padding: 2rem 0;
    margin-top: 4rem;
    text-align: center;
}}

article {{
    margin: 2rem 0;
}}

h1, h2, h3, h4, h5, h6 {{
    margin: 1.5rem 0 0.5rem;
    line-height: 1.3;
}}
"""
    atomic_write_text(theme_path / "assets" / "css" / "style.css", css_content)

    # JavaScript
    js_content = f"""// Theme: {name}

console.log('Theme loaded: {name}');

document.addEventListener('DOMContentLoaded', function() {{
    // Your theme scripts here
}});
"""
    atomic_write_text(theme_path / "assets" / "js" / "main.js", js_content)
