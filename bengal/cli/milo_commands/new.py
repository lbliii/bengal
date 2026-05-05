"""Milo commands for ``bengal new`` — scaffold sites, themes, pages, templates, and content types."""

from __future__ import annotations

from textwrap import dedent
from typing import Annotated

from milo import Description

# ---------------------------------------------------------------------------
# new site
# ---------------------------------------------------------------------------


def new_site(
    name: Annotated[str, Description("Site name (slugified for directory)")] = "",
    theme: Annotated[str, Description("Visual theme (colors, layout): default")] = "default",
    template: Annotated[
        str,
        Description(
            "Site structure (directories, starter content): default, blog, docs, portfolio, product, resume, landing, changelog"
        ),
    ] = "default",
    no_init: Annotated[bool, Description("Skip structure initialization wizard")] = False,
    init_preset: Annotated[
        str,
        Description(
            "Initialize with preset (blog, docs, portfolio, product, resume) without prompting"
        ),
    ] = "",
) -> dict:
    """Create a new Bengal site with optional structure initialization."""
    from pathlib import Path

    from bengal.output import get_cli_output
    from bengal.scaffolds import get_template
    from bengal.utils.io.atomic_write import atomic_write_text
    from bengal.utils.primitives.text import slugify

    cli = get_cli_output()

    if not name:
        name = cli.prompt("Enter site name")
        if not name:
            cli.warning("Cancelled.")
            raise SystemExit(1)

    site_title = name.strip()
    slug = slugify(site_title)
    if not slug:
        cli.error("Site name must contain at least one alphanumeric character!")
        cli.tip("Try a name like 'my-site' or 'docs'.")
        raise SystemExit(1)

    site_path = Path(slug)
    if site_path.exists():
        cli.error(f"Directory {slug} already exists!")
        cli.tip(f"Pick a different name, or remove the existing './{slug}' directory first.")
        raise SystemExit(1)

    # Use init_preset as template if provided
    effective_template = init_preset if init_preset else template
    site_template = get_template(effective_template)
    if site_template is None:
        cli.error(f"Template '{effective_template}' not found")
        cli.tip(
            "Built-in templates: default, blog, docs, portfolio, product, resume, landing, changelog."
        )
        raise SystemExit(1)

    # Create directory structure
    site_path.mkdir(parents=True)
    (site_path / "content").mkdir()
    (site_path / "assets" / "css").mkdir(parents=True)
    (site_path / "assets" / "js").mkdir()
    (site_path / "assets" / "images").mkdir()
    (site_path / "templates").mkdir()
    for d in site_template.additional_dirs:
        (site_path / d).mkdir(parents=True, exist_ok=True)

    # Create config directory
    config_dir = site_path / "config" / "_default"
    config_dir.mkdir(parents=True)
    atomic_write_text(
        config_dir / "site.yaml",
        f'title: {site_title}\nbaseurl: ""\ndescription: A new Bengal site\ntheme: {theme}\n\n# Uncomment to customize:\n# language: en\n# author: Your Name\n',
    )

    # Create .gitignore
    atomic_write_text(
        site_path / ".gitignore",
        "# Bengal build outputs\npublic/\n\n# Bengal cache\n.bengal/\n\n# Python\n__pycache__/\n*.py[cod]\n\n# IDE\n.vscode/\n.idea/\n\n# OS\n.DS_Store\n",
    )

    # Write template files
    files_created = 0
    for tf in site_template.files:
        base_dir = site_path / tf.target_dir
        base_dir.mkdir(parents=True, exist_ok=True)
        file_path = base_dir / tf.relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(file_path, tf.content)
        files_created += 1

    cli.render_write(
        "scaffold_result.kida",
        title=f"Site: {site_title}",
        entries=[
            {"name": slug, "note": site_template.description},
            {"name": "config/", "note": "site.yaml"},
            {"name": "content/", "note": f"{files_created} files"},
        ],
        steps=[f"cd {slug}", "bengal serve"],
        summary="Site created successfully!",
    )

    return {"name": site_title, "slug": slug, "template": effective_template}


# ---------------------------------------------------------------------------
# new theme
# ---------------------------------------------------------------------------


def new_theme(
    name: Annotated[str, Description("Theme name (slugified for directory)")] = "",
) -> dict:
    """Create a new theme scaffold with templates and assets."""
    from pathlib import Path

    from bengal.output import get_cli_output
    from bengal.utils.io.atomic_write import atomic_write_text
    from bengal.utils.primitives.text import slugify

    cli = get_cli_output()

    if not name:
        name = cli.prompt("Enter theme name")
        if not name:
            cli.warning("Cancelled.")
            raise SystemExit(1)

    slug = slugify(name)

    # Detect if inside a Bengal site
    in_site = Path("content").exists() and Path("bengal.toml").exists()
    theme_path = (Path("themes") / slug) if in_site else Path(slug)

    if theme_path.exists():
        cli.error(f"Theme directory {theme_path} already exists!")
        cli.tip(f"Pick a different name, or remove the existing '{theme_path}' directory first.")
        raise SystemExit(1)

    # Create directory structure
    theme_path.mkdir(parents=True)
    (theme_path / "templates").mkdir()
    (theme_path / "templates" / "partials").mkdir()
    (theme_path / "assets" / "css").mkdir(parents=True)
    (theme_path / "assets" / "js").mkdir(parents=True)
    (theme_path / "assets" / "images").mkdir(parents=True)

    cli.blank()
    cli.header(f"Creating new theme: {name}")

    # Templates
    atomic_write_text(
        theme_path / "templates" / "base.html",
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '    <meta charset="UTF-8">\n'
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        "    <title>{% block title %}{{ site.config.title }}{% endblock %}</title>\n"
        '    <link rel="stylesheet" href="{{ url_for(\'assets/css/style.css\') }}">\n'
        "    {% block extra_head %}{% endblock %}\n"
        "</head>\n<body>\n"
        '    {% include "partials/header.html" %}\n'
        "    <main>{% block content %}{% endblock %}</main>\n"
        '    {% include "partials/footer.html" %}\n'
        "    <script src=\"{{ url_for('assets/js/main.js') }}\"></script>\n"
        "    {% block extra_scripts %}{% endblock %}\n"
        "</body>\n</html>\n",
    )
    atomic_write_text(
        theme_path / "templates" / "home.html",
        '{% extends "base.html" %}\n\n{% block content %}\n'
        "<h1>Welcome to {{ site.config.title }}</h1>\n"
        "{{ page.content | safe }}\n{% endblock %}\n",
    )
    atomic_write_text(
        theme_path / "templates" / "page.html",
        '{% extends "base.html" %}\n\n{% block title %}{{ page.title }} - {{ site.config.title }}{% endblock %}\n\n'
        "{% block content %}\n<article>\n  <h1>{{ page.title }}</h1>\n  {{ page.content | safe }}\n</article>\n{% endblock %}\n",
    )
    atomic_write_text(
        theme_path / "templates" / "partials" / "header.html",
        '<header class="site-header">\n  <div class="container">\n'
        '    <h1><a href="{{ site.config.baseurl }}">{{ site.config.title }}</a></h1>\n'
        "  </div>\n</header>\n",
    )
    atomic_write_text(
        theme_path / "templates" / "partials" / "footer.html",
        '<footer class="site-footer">\n  <div class="container">\n'
        "    <p>&copy; {{ get_current_year() }} {{ site.config.title }}</p>\n"
        "  </div>\n</footer>\n",
    )
    # templates created above

    # Assets
    atomic_write_text(
        theme_path / "assets" / "css" / "style.css",
        f"/* Theme: {name} */\n\n:root {{\n  --primary: #007bff;\n  --text: #333;\n  --bg: #fff;\n}}\n\n"
        "body { font-family: system-ui, sans-serif; color: var(--text); background: var(--bg); line-height: 1.6; }\n"
        ".container { max-width: 1200px; margin: 0 auto; padding: 0 1rem; }\n",
    )
    atomic_write_text(
        theme_path / "assets" / "js" / "main.js",
        f"// Theme: {name}\n\ndocument.addEventListener('DOMContentLoaded', () => {{\n  // Your scripts here\n}});\n",
    )
    steps = []
    if in_site:
        steps = [f'Update bengal.toml: theme = "{slug}"', "Run: bengal serve"]
    else:
        steps = [f"Package as: bengal-theme-{slug}", "Add to pyproject.toml for distribution"]

    cli.render_write(
        "scaffold_result.kida",
        title=f"Theme: {name}",
        entries=[
            {"name": str(theme_path), "note": ""},
            {"name": "templates/", "note": "3 templates + 2 partials"},
            {"name": "assets/css/", "note": "style.css"},
            {"name": "assets/js/", "note": "main.js"},
        ],
        steps=steps,
        summary="Theme created successfully!",
    )

    return {"name": name, "slug": slug, "path": str(theme_path)}


# ---------------------------------------------------------------------------
# new page
# ---------------------------------------------------------------------------


def new_page(
    name: Annotated[str, Description("Page name (slugified for filename)")],
    section: Annotated[str, Description("Section to create page in")] = "",
) -> dict:
    """Create a new content page."""
    from datetime import datetime
    from pathlib import Path

    from bengal.output import get_cli_output
    from bengal.utils.io.atomic_write import atomic_write_text
    from bengal.utils.primitives.text import slugify

    cli = get_cli_output()

    content_dir = Path("content")
    if not content_dir.exists():
        cli.error("Not in a Bengal site directory!")
        cli.tip("Run `bengal new site <name>` to create one, or cd into an existing site.")
        raise SystemExit(1)

    slug = slugify(name)
    title = name.replace("-", " ").title()

    page_dir = content_dir / section if section else content_dir
    page_dir.mkdir(parents=True, exist_ok=True)
    page_path = page_dir / f"{slug}.md"

    if page_path.exists():
        cli.error(f"Page {page_path} already exists!")
        cli.tip(f"Pick a different name, or remove the existing file: {page_path}")
        raise SystemExit(1)

    atomic_write_text(
        page_path,
        f"---\ntitle: {title}\ndate: {datetime.now().isoformat()}\n---\n\n# {title}\n\nYour content goes here.\n",
    )

    cli.render_write(
        "scaffold_result.kida",
        title="New Page",
        entries=[{"name": str(page_path), "note": title}],
        summary=f"Created: {page_path}",
    )

    return {"path": str(page_path), "title": title, "slug": slug}


# ---------------------------------------------------------------------------
# new layout
# ---------------------------------------------------------------------------


def new_layout(
    name: Annotated[str, Description("Layout name (slugified for filename)")] = "",
) -> dict:
    """Create a new layout template."""
    from pathlib import Path

    from bengal.output import get_cli_output
    from bengal.utils.io.atomic_write import atomic_write_text
    from bengal.utils.primitives.text import slugify

    cli = get_cli_output()

    templates_dir = Path("templates")
    if not templates_dir.exists():
        cli.error("Not in a Bengal site directory!")
        cli.tip("Run `bengal new site <name>` to create one, or cd into an existing site.")
        raise SystemExit(1)

    if not name:
        name = cli.prompt("Enter layout name")
        if not name:
            cli.warning("Cancelled.")
            raise SystemExit(1)

    slug = slugify(name)
    target_dir = templates_dir / "layouts"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{slug}.html"

    if target_path.exists():
        cli.error(f"Layout {target_path} already exists!")
        cli.tip(f"Pick a different name, or remove the existing file: {target_path}")
        raise SystemExit(1)

    atomic_write_text(
        target_path,
        '{% extends "base.html" %}\n\n{% block content %}\n{# Your layout content here #}\n{{ page.content | safe }}\n{% endblock %}\n',
    )

    cli.render_write(
        "scaffold_result.kida",
        title="New Layout",
        entries=[{"name": str(target_path), "note": f"layout: {slug}"}],
        summary=f"Created: {target_path}",
    )

    return {"path": str(target_path), "name": name, "slug": slug}


# ---------------------------------------------------------------------------
# new partial
# ---------------------------------------------------------------------------


def new_partial(
    name: Annotated[str, Description("Partial name (slugified for filename)")] = "",
) -> dict:
    """Create a new partial template."""
    from pathlib import Path

    from bengal.output import get_cli_output
    from bengal.utils.io.atomic_write import atomic_write_text
    from bengal.utils.primitives.text import slugify

    cli = get_cli_output()

    templates_dir = Path("templates")
    if not templates_dir.exists():
        cli.error("Not in a Bengal site directory!")
        cli.tip("Run `bengal new site <name>` to create one, or cd into an existing site.")
        raise SystemExit(1)

    if not name:
        name = cli.prompt("Enter partial name")
        if not name:
            cli.warning("Cancelled.")
            raise SystemExit(1)

    slug = slugify(name)
    target_dir = templates_dir / "partials"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{slug}.html"

    if target_path.exists():
        cli.error(f"Partial {target_path} already exists!")
        cli.tip(f"Pick a different name, or remove the existing file: {target_path}")
        raise SystemExit(1)

    atomic_write_text(
        target_path,
        f'{{# Partial: {slug} #}}\n<div class="partial partial-{slug}">\n  {{# Your content here #}}\n</div>\n',
    )

    cli.render_write(
        "scaffold_result.kida",
        title="New Partial",
        entries=[{"name": str(target_path), "note": f'include "partials/{slug}.html"'}],
        summary=f"Created: {target_path}",
    )

    return {"path": str(target_path), "name": name, "slug": slug}


# ---------------------------------------------------------------------------
# new content-type
# ---------------------------------------------------------------------------


def _content_type_scaffold(slug: str, class_name: str) -> str:
    """Render the source for a new ContentTypeStrategy scaffold."""
    return dedent(
        f'''\
        """Custom content type strategy: {slug}.

        Generated by ``bengal new content-type {slug}``. Edit the TODOs below.
        """

        from __future__ import annotations

        from typing import TYPE_CHECKING

        from bengal.content_types import ContentTypeStrategy, register_strategy

        if TYPE_CHECKING:
            from collections.abc import Sequence

            from bengal.protocols import PageLike, SectionLike


        class {class_name}Strategy(ContentTypeStrategy):
            """
            Strategy for the ``{slug}`` content type.

            When to use:
                A section opts in by setting ``type = "{slug}"`` in its
                ``_index.md`` frontmatter, or auto-detected via
                ``detect_from_section`` below. Override only the methods whose
                defaults don\'t suit your content — the base class in
                ``bengal/content_types/base.py`` handles the rest.
            """

            # TODO: point at the template you want for ``{slug}`` list pages.
            default_template = "{slug}/list.html"

            # TODO: set True if a ``{slug}`` section can grow large enough to paginate.
            allows_pagination = False

            def sort_pages(self, pages: Sequence[PageLike]) -> list[PageLike]:
                """Sort pages for list views.

                Default below sorts by ``weight`` (low first), then ``title``.
                Replace with a domain-appropriate ordering — e.g. by date for
                chronological content, or by ``metadata["difficulty"]`` for tutorials.
                """
                return sorted(
                    pages,
                    key=lambda p: (p.metadata.get("weight", 999), p.title),
                )

            def detect_from_section(self, section: SectionLike) -> bool:
                """Auto-detect whether ``section`` is a ``{slug}`` section.

                Return True to claim a section without explicit ``type =`` in
                its frontmatter. Default below is conservative: claim only
                sections literally named ``"{slug}"``.
                """
                return section.name.lower() == "{slug}"


        # Registration runs at import time. Whoever imports this module activates
        # the strategy. For Bengal contributors, add this module to
        # ``bengal/content_types/registry.py`` (next to the built-in strategies).
        # For site authors, import this from a plugin entry point or site-level
        # init module so it loads before the build runs.
        register_strategy("{slug}", {class_name}Strategy())
        '''
    )


def new_content_type(
    name: Annotated[str, Description("Content type name (e.g. recipe, case-study)")] = "",
) -> dict:
    """Create a new ContentTypeStrategy scaffold.

    See ``bengal/content_types/base.py`` for the full strategy interface, and
    ``bengal/content_types/strategies.py`` for built-in examples (BlogStrategy,
    DocsStrategy, TutorialStrategy).
    """
    from pathlib import Path

    from bengal.output import get_cli_output
    from bengal.utils.io.atomic_write import atomic_write_text
    from bengal.utils.primitives.text import slugify

    cli = get_cli_output()

    if not name:
        name = cli.prompt("Enter content type name (e.g. recipe, case-study)")
        if not name:
            cli.warning("Cancelled.")
            raise SystemExit(1)

    slug = slugify(name)
    if not slug:
        cli.error("Content type name must contain at least one alphanumeric character!")
        cli.tip("Examples: 'recipe', 'case-study', 'release-note'")
        raise SystemExit(1)

    class_name = "".join(part.capitalize() for part in slug.split("-"))

    # Choose target dir: bengal repo → bengal/content_types/, else → content_types/
    bengal_pkg = Path("bengal") / "content_types"
    if bengal_pkg.is_dir():
        target_dir = bengal_pkg
        location_note = "Bengal repo (built-in)"
    else:
        target_dir = Path("content_types")
        location_note = "site-local (wire up via plugin or init)"

    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{slug.replace('-', '_')}_strategy.py"

    if target_path.exists():
        cli.error(f"File {target_path} already exists!")
        cli.tip(f"Remove it first, or pick a different name than '{slug}'.")
        raise SystemExit(1)

    atomic_write_text(target_path, _content_type_scaffold(slug, class_name))

    if target_dir == bengal_pkg:
        steps = [
            f"Edit {target_path} — replace TODO defaults",
            "Import the module from bengal/content_types/registry.py to activate it",
            f'Set ``type = "{slug}"`` in any section\'s _index.md',
        ]
    else:
        steps = [
            f"Edit {target_path} — replace TODO defaults",
            "Import this module from a plugin or site init so register_strategy() runs",
            f'Set ``type = "{slug}"`` in any section\'s _index.md',
        ]

    cli.render_write(
        "scaffold_result.kida",
        title=f"Content Type: {slug}",
        entries=[
            {"name": str(target_path), "note": f"{class_name}Strategy ({location_note})"},
        ],
        steps=steps,
        summary=f"Created: {target_path}",
    )

    return {
        "path": str(target_path),
        "slug": slug,
        "class_name": f"{class_name}Strategy",
    }
