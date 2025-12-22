"""Theme-related CLI commands (themes, swizzle)."""

from __future__ import annotations

import re
from pathlib import Path

import click

from bengal.cli.base import BengalGroup
from bengal.cli.helpers import (
    command_metadata,
    get_cli_output,
    handle_cli_errors,
    load_site_from_cli,
)
from bengal.core.theme import get_installed_themes, get_theme_package
from bengal.utils.logger import get_logger
from bengal.utils.swizzle import SwizzleManager

logger = get_logger(__name__)


@click.group(cls=BengalGroup)
def theme() -> None:
    """Theme utilities (list/info/discover/install, swizzle)."""
    pass


@theme.command()
@command_metadata(
    category="theming",
    description="Copy a theme template/partial to project templates",
    examples=[
        "bengal utils theme swizzle layouts/article.html",
        "bengal utils theme swizzle partials/header.html",
    ],
    requires_site=True,
    tags=["theming", "templates", "quick"],
)
@handle_cli_errors(show_art=False)
@click.argument("template_path")
@click.argument("source", type=click.Path(exists=True), default=".")
def swizzle(template_path: str, source: str) -> None:
    """
    Copy a theme template/partial to project templates.

    Swizzling copies a template from the active theme to your project's
    templates/ directory, allowing you to customize it while tracking
    provenance for future updates.

    Examples:
        bengal theme swizzle layouts/article.html
        bengal theme swizzle partials/header.html

    See also:
        bengal theme swizzle-list - List swizzled templates
        bengal theme swizzle-update - Update swizzled templates
    """
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    mgr = SwizzleManager(site)
    dest = mgr.swizzle(template_path)
    cli.success(f"✓ Swizzled to {dest}")


@theme.command("swizzle-list")
@command_metadata(
    category="theming",
    description="List swizzled templates",
    examples=["bengal utils theme swizzle-list"],
    requires_site=True,
    tags=["theming", "info", "quick"],
)
@handle_cli_errors(show_art=False)
@click.argument("source", type=click.Path(exists=True), default=".")
def swizzle_list(source: str) -> None:
    """
    📋 List swizzled templates.

    Shows all templates that have been copied from themes to your project,
    along with their source theme for tracking.

    Examples:
        bengal theme swizzle-list

    See also:
        bengal theme swizzle - Copy a template from theme
        bengal theme swizzle-update - Update swizzled templates
    """
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    mgr = SwizzleManager(site)
    records = mgr.list()
    if not records:
        cli.info("No swizzled templates.")
        return
    for r in records:
        cli.info(f"- {r.target} (from {r.theme})")


@theme.command("swizzle-update")
@command_metadata(
    category="theming",
    description="Update swizzled templates if unchanged locally",
    examples=["bengal utils theme swizzle-update"],
    requires_site=True,
    tags=["theming", "maintenance"],
)
@handle_cli_errors(show_art=False)
@click.argument("source", type=click.Path(exists=True), default=".")
def swizzle_update(source: str) -> None:
    """
    Update swizzled templates if unchanged locally.

    Checks swizzled templates and updates them from the theme if you haven't
    modified them locally. Templates you've customized are skipped.

    Examples:
        bengal theme swizzle-update

    See also:
        bengal theme swizzle - Copy a template from theme
        bengal theme swizzle-list - List swizzled templates
    """
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    mgr = SwizzleManager(site)
    summary = mgr.update()
    cli.info(
        f"Updated: {summary['updated']}, Skipped (changed): {summary['skipped_changed']}, Missing upstream: {summary['missing_upstream']}"
    )


@theme.command("list")
@command_metadata(
    category="theming",
    description="List available themes (project, installed, bundled)",
    examples=["bengal utils theme list"],
    requires_site=True,
    tags=["theming", "info", "quick"],
)
@handle_cli_errors(show_art=False)
@click.argument("source", type=click.Path(exists=True), default=".")
def list_themes(source: str) -> None:
    """
    📋 List available themes.

    Shows themes from three sources:
    - Project themes: themes/ directory in your site
    - Installed themes: Themes installed via pip/uv
    - Bundled themes: Themes included with Bengal

    Examples:
        bengal theme list

    See also:
        bengal theme info - Show details about a specific theme
        bengal theme install - Install a theme package
    """
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)

    # Project themes
    themes_dir = site.root_path / "themes"
    project = []
    if themes_dir.exists():
        project = [p.name for p in themes_dir.iterdir() if (p / "templates").exists()]

    # Installed themes
    installed = list(get_installed_themes().keys())

    # Bundled themes
    bundled = []
    try:
        import bengal

        pkg_dir = Path(bengal.__file__).parent / "themes"
        if pkg_dir.exists():
            bundled = [p.name for p in pkg_dir.iterdir() if (p / "templates").exists()]
    except Exception as e:
        # Ignore all exceptions: if any error occurs (e.g., import failure, missing files),
        # treat as "no bundled themes available"
        logger.debug(
            "bundled_themes_discovery_failed",
            error=str(e),
            error_type=type(e).__name__,
            action="treating_as_no_bundled_themes",
        )
        pass

    cli.header("Project themes:")
    if project:
        for t in sorted(project):
            cli.info(f"  - {t}")
    else:
        cli.info("  (none)")

    cli.header("Installed themes:")
    if installed:
        for t in sorted(installed):
            pkg = get_theme_package(t)
            ver = pkg.version if pkg else None
            cli.info(f"  - {t}{' ' + ver if ver else ''}")
    else:
        cli.info("  (none)")

    cli.header("Bundled themes:")
    if bundled:
        for t in sorted(bundled):
            cli.info(f"  - {t}")
    else:
        cli.info("  (none)")


@theme.command("info")
@command_metadata(
    category="theming",
    description="Show theme info for a slug (source, version, paths)",
    examples=["bengal utils theme info default"],
    requires_site=True,
    tags=["theming", "info", "quick"],
)
@handle_cli_errors(show_art=False)
@click.argument("slug")
@click.argument("source", type=click.Path(exists=True), default=".")
def info(slug: str, source: str) -> None:
    """
    Show theme info for a slug.

    Displays information about a theme including:
    - Source location (project, installed, or bundled)
    - Version (if installed)
    - Template and asset paths

    Examples:
        bengal theme info default
        bengal theme info my-theme

    See also:
        bengal theme list - List all available themes
    """
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    cli.header(f"Theme: {slug}")

    # Project theme
    site_theme = site.root_path / "themes" / slug
    if site_theme.exists():
        cli.info(f"  Project path: {site_theme}")

    # Installed theme
    pkg = get_theme_package(slug)
    if pkg:
        cli.info(f"  Installed: {pkg.distribution or pkg.package} {pkg.version or ''}")
        tp = pkg.resolve_resource_path("templates")
        ap = pkg.resolve_resource_path("assets")
        if tp:
            cli.info(f"  Templates: {tp}")
        if ap:
            cli.info(f"  Assets:    {ap}")

    # Bundled theme
    try:
        import bengal

        bundled = Path(bengal.__file__).parent / "themes" / slug
        if bundled.exists():
            cli.info(f"  Bundled path: {bundled}")
    except Exception as e:
        # Ignore all exceptions: if any error occurs (e.g., import failure, missing files),
        # treat as "bundled theme not found"
        logger.debug(
            "bundled_theme_path_check_failed",
            theme_slug=slug,
            error=str(e),
            error_type=type(e).__name__,
            action="treating_as_not_found",
        )
        pass


@theme.command("discover")
@command_metadata(
    category="theming",
    description="List swizzlable templates from the active theme chain",
    examples=["bengal utils theme discover"],
    requires_site=True,
    tags=["theming", "info"],
)
@handle_cli_errors(show_art=False)
@click.argument("source", type=click.Path(exists=True), default=".")
def discover(source: str) -> None:
    """
    List swizzlable templates from the active theme chain.

    Shows all templates available in your active theme(s) that can be
    swizzled (copied) to your project for customization.

    Examples:
        bengal theme discover

    See also:
        bengal theme swizzle - Copy a template from theme
    """
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    from bengal.rendering.engines import create_engine

    engine = create_engine(site)
    # Walk all template directories in priority order
    seen: set[str] = set()
    for base in engine.template_dirs:
        for f in base.rglob("*.html"):
            rel = str(f.relative_to(base))
            if rel not in seen:
                seen.add(rel)
                cli.info(rel)


@theme.command("debug")
@command_metadata(
    category="theming",
    description="Debug theme resolution: show chain, paths, and template sources",
    examples=["bengal utils theme debug"],
    requires_site=True,
    tags=["theming", "debug", "diagnostics"],
)
@handle_cli_errors(show_art=False)
@click.argument("source", type=click.Path(exists=True), default=".")
@click.option("--template", help="Show resolution path for a specific template")
def debug(source: str, template: str | None) -> None:
    """
    🐛 Debug theme resolution and template paths.

    Shows comprehensive information about:
    - Active theme chain (inheritance order)
    - Template resolution paths (priority order)
    - Template source locations
    - Theme validation (circular inheritance, missing themes)
    - Specific template resolution (if --template provided)

    Examples:
        bengal theme debug
        bengal theme debug --template page.html

    See also:
        bengal theme info - Show details about a specific theme
        bengal theme list - List available themes
    """
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    from bengal.core.theme import resolve_theme_chain
    from bengal.rendering.engines import create_engine

    engine = create_engine(site)

    # Show active theme
    cli.header("Active Theme")
    cli.info(f"  Theme: {site.theme or 'default'}")

    # Show theme chain
    cli.header("Theme Inheritance Chain")
    chain = resolve_theme_chain(site.root_path, site.theme)
    if not chain:
        cli.info("  (no inheritance, using default)")
    else:
        for i, theme_name in enumerate(chain):
            prefix = "  → " if i > 0 else "  "
            extends = _get_theme_extends(site.root_path, theme_name)
            if extends:
                cli.info(f"{prefix}{theme_name} (extends {extends})")
            else:
                cli.info(f"{prefix}{theme_name} (base theme)")
        if "default" not in chain:
            cli.info("  → default (fallback)")

    # Validate theme chain
    cli.header("Theme Validation")
    issues = _validate_theme_chain(site.root_path, site.theme)
    if issues:
        for issue in issues:
            cli.warning(f"  ⚠ {issue}")
    else:
        cli.info("  ✓ No issues detected")

    # Show template resolution paths
    cli.header("Template Resolution Paths (priority order)")
    for i, template_dir in enumerate(engine.template_dirs):
        source_type = _get_template_dir_source_type(site.root_path, template_dir)
        cli.info(f"  {i + 1}. {template_dir} ({source_type})")

    # Show template sources for common templates
    if not template:
        cli.header("Common Template Sources")
        common_templates = ["base.html", "page.html", "home.html", "404.html"]
        for tpl_name in common_templates:
            tpl_path = engine._find_template_path(tpl_name)
            if tpl_path:
                source_type = _get_template_dir_source_type(site.root_path, tpl_path.parent)
                cli.info(f"  {tpl_name}: {tpl_path} ({source_type})")
            else:
                cli.info(f"  {tpl_name}: (not found)")

    # Show specific template resolution if requested
    if template:
        cli.header(f"Template Resolution: {template}")
        tpl_path = engine._find_template_path(template)
        if tpl_path:
            source_type = _get_template_dir_source_type(site.root_path, tpl_path.parent)
            cli.info(f"  Found: {tpl_path}")
            cli.info(f"  Source: {source_type}")
            # Show all possible locations
            cli.info("  Searched in:")
            for i, template_dir in enumerate(engine.template_dirs):
                candidate = template_dir / template
                marker = "✓" if candidate.exists() else " "
                cli.info(f"    {marker} {i + 1}. {candidate}")
        else:
            cli.warning(f"  Template '{template}' not found")
            cli.info("  Searched in:")
            for i, template_dir in enumerate(engine.template_dirs):
                cli.info(f"    {i + 1}. {template_dir / template}")


def _get_theme_extends(site_root: Path, theme_name: str) -> str | None:
    """Get the theme that a theme extends."""
    from bengal.core.theme import _read_theme_extends

    return _read_theme_extends(site_root, theme_name)


def _validate_theme_chain(site_root: Path, active_theme: str | None) -> list[str]:
    """Validate theme chain and return list of issues."""
    issues: list[str] = []
    from bengal.core.theme import _read_theme_extends

    # Check for circular inheritance by walking the chain manually
    visited: set[str] = set()
    current = active_theme or "default"
    depth = 0
    MAX_DEPTH = 5
    chain_path: list[str] = []

    while current and depth < MAX_DEPTH:
        if current in visited:
            # Found a cycle - show the cycle path
            cycle_start = chain_path.index(current)
            cycle = " → ".join(chain_path[cycle_start:] + [current])
            issues.append(f"Circular inheritance detected: {cycle}")
            break
        visited.add(current)
        chain_path.append(current)
        extends = _read_theme_extends(site_root, current)
        if not extends or extends == current:
            break
        current = extends
        depth += 1

    if depth >= MAX_DEPTH:
        issues.append(f"Theme inheritance depth exceeds maximum ({MAX_DEPTH})")

    # Check for missing themes in the resolved chain
    from bengal.core.theme import resolve_theme_chain

    chain = resolve_theme_chain(site_root, active_theme)
    for theme_name in chain:
        if not _theme_exists(site_root, theme_name):
            issues.append(
                f"Theme '{theme_name}' not found in any location (site, installed, or bundled)"
            )

    return issues


def _theme_exists(site_root: Path, theme_name: str) -> bool:
    """Check if a theme exists in any location."""
    # Site theme
    site_theme = site_root / "themes" / theme_name
    if site_theme.exists():
        return True

    # Installed theme
    try:
        pkg = get_theme_package(theme_name)
        if pkg:
            return True
    except Exception as e:
        logger.debug(
            "cli_theme_installed_check_failed",
            theme=theme_name,
            error=str(e),
            error_type=type(e).__name__,
            action="continuing_to_bundled_check",
        )

    # Bundled theme
    try:
        import bengal

        bundled = Path(bengal.__file__).parent / "themes" / theme_name
        if bundled.exists():
            return True
    except Exception as e:
        logger.debug(
            "cli_theme_bundled_check_failed",
            theme=theme_name,
            error=str(e),
            error_type=type(e).__name__,
            action="returning_not_found",
        )

    return False


def _get_template_dir_source_type(site_root: Path, template_dir: Path) -> str:
    """Determine the source type of a template directory."""
    # Project templates
    if template_dir == site_root / "templates":
        return "project templates"

    # Site theme
    if template_dir.is_relative_to(site_root / "themes"):
        theme_name = template_dir.relative_to(site_root / "themes").parts[0]
        return f"site theme: {theme_name}"

    # Bundled theme
    try:
        import bengal

        bengal_themes = Path(bengal.__file__).parent / "themes"
        if template_dir.is_relative_to(bengal_themes):
            theme_name = template_dir.relative_to(bengal_themes).parts[0]
            return f"bundled theme: {theme_name}"
    except Exception as e:
        logger.debug(
            "cli_theme_source_bundled_check_failed",
            template_dir=str(template_dir),
            error=str(e),
            error_type=type(e).__name__,
            action="continuing_to_installed_check",
        )

    # Installed theme (check if it's in a package)
    try:
        from bengal.core.theme import get_installed_themes

        installed = get_installed_themes()
        for theme_slug, pkg in installed.items():
            resolved = pkg.resolve_resource_path("templates")
            if resolved and template_dir == resolved:
                return f"installed theme: {theme_slug}"
    except Exception as e:
        logger.debug(
            "cli_theme_source_installed_check_failed",
            template_dir=str(template_dir),
            error=str(e),
            error_type=type(e).__name__,
            action="returning_unknown",
        )

    return "unknown"


# SECURITY: Safe package name pattern to prevent malicious package names
# Allows: alphanumeric, dots, underscores, hyphens (standard PyPI naming)
# Blocks: path traversal (../), shell injection characters, etc.
SAFE_PACKAGE_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9._-]*$")


@theme.command("install")
@command_metadata(
    category="theming",
    description="Install a theme via uv pip",
    examples=[
        "bengal utils theme install bengal-theme-minimal",
        "bengal utils theme install minimal --force",
    ],
    requires_site=False,
    tags=["theming", "setup"],
)
@handle_cli_errors(show_art=False)
@click.argument("name")
@click.option("--force", is_flag=True, help="Install even if name is non-canonical")
def install(name: str, force: bool) -> None:
    """
    Install a theme via uv pip.

    Installs a theme package from PyPI. NAME may be a package name or a slug.
    If a slug without prefix is provided, suggests canonical 'bengal-theme-<slug>'.

    Examples:
        bengal theme install bengal-theme-minimal
        bengal theme install minimal --force

    See also:
        bengal theme list - List available themes
    """
    cli = get_cli_output()

    # SECURITY: Validate package name against safe pattern
    if not SAFE_PACKAGE_PATTERN.match(name):
        cli.error(
            f"Invalid package name: '{name}'\n"
            f"Package names must start with a letter and contain only "
            f"alphanumeric characters, dots, underscores, or hyphens."
        )
        raise SystemExit(1)

    pkg = name
    is_slug = (
        "." not in name
        and "/" not in name
        and not name.startswith("bengal-theme-")
        and not name.endswith("-bengal-theme")
    )
    if is_slug:
        sugg = f"bengal-theme-{name}"
        if not force:
            cli.warning(
                f"⚠ Theme name '{name}' is non-standard. Prefer '{sugg}'. Use --force to proceed."
            )
            return
        pkg = sugg

    # Run uv pip install (best-effort)
    try:
        import subprocess
        import sys

        cmd = [sys.executable, "-m", "uv", "pip", "install", pkg]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            cli.error(proc.stderr or proc.stdout)
            raise SystemExit(proc.returncode) from None
        cli.success(f"Installed {pkg}")
    except FileNotFoundError:
        cli.warning("uv not found; falling back to pip")
        import subprocess
        import sys

        cmd = [sys.executable, "-m", "pip", "install", pkg]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            cli.error(proc.stderr or proc.stdout)
            raise SystemExit(proc.returncode) from None
        cli.success(f"Installed {pkg}")


def _sanitize_slug(slug: str) -> str:
    slugified = re.sub(r"[^a-z0-9\-]", "-", slug.lower()).strip("-")
    slugified = re.sub(r"-+", "-", slugified)
    if not slugified:
        raise click.ClickException("Invalid slug; must contain letters, numbers, or dashes")
    return slugified


@theme.command("new")
@command_metadata(
    category="theming",
    description="Create a new theme scaffold",
    examples=[
        "bengal utils theme new my-theme",
        "bengal utils theme new my-theme --mode package",
    ],
    requires_site=False,
    tags=["theming", "setup"],
)
@handle_cli_errors(show_art=False)
@click.argument("slug")
@click.option(
    "--mode",
    type=click.Choice(["site", "package"]),
    default="site",
    help="Scaffold locally under themes/ or an installable package",
)
@click.option(
    "--output",
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    default=".",
    help="Output directory (for site mode: site root; for package mode: parent dir)",
)
@click.option("--extends", default="default", help="Parent theme to extend")
@click.option("--force", is_flag=True, help="Overwrite existing directory if present")
def new(slug: str, mode: str, output: str, extends: str, force: bool) -> None:
    """
    Create a new theme scaffold.

    Creates a new theme with templates, partials, and assets. SLUG is the
    theme identifier used in config (e.g., [site].theme = SLUG).

    Examples:
        bengal theme new my-theme
        bengal theme new my-theme --mode package

    See also:
        bengal theme list - List available themes
    """
    cli = get_cli_output()
    slug = _sanitize_slug(slug)
    output_path = Path(output).resolve()

    if mode == "site":
        # Create under site's themes/<slug>
        site_root = output_path
        theme_dir = site_root / "themes" / slug
        if theme_dir.exists() and not force:
            cli.error(f"{theme_dir} already exists; use --force to overwrite")
            raise click.Abort()
        (theme_dir / "templates" / "partials").mkdir(parents=True, exist_ok=True)
        (theme_dir / "assets" / "css").mkdir(parents=True, exist_ok=True)
        (theme_dir / "dev" / "components").mkdir(parents=True, exist_ok=True)

        # Minimal files
        (theme_dir / "templates" / "page.html").write_text(
            "{% extends 'page.html' %}\n{% block content %}<main>{{ content|default('Hello from ' ~ site.theme) }}</main>{% endblock %}\n",
            encoding="utf-8",
        )
        (theme_dir / "templates" / "partials" / "example.html").write_text(
            '<div class="example">Example Partial</div>\n',
            encoding="utf-8",
        )
        (theme_dir / "assets" / "css" / "style.css").write_text(
            "/* Your theme styles */\n", encoding="utf-8"
        )
        (theme_dir / "theme.toml").write_text(
            f'name="{slug}"\nextends="{extends}"\n',
            encoding="utf-8",
        )
        (theme_dir / "dev" / "components" / "example.yaml").write_text(
            "name: Example\ntemplate: partials/example.html\nvariants:\n  - id: default\n    name: Default\n    context: {}\n",
            encoding="utf-8",
        )

        cli.success(f"✓ Created site theme at {theme_dir}")
        return

    # package mode
    package_name = f"bengal-theme-{slug}"
    pkg_root = output_path / package_name
    theme_pkg_dir = pkg_root / "bengal_themes" / slug
    if pkg_root.exists() and not force:
        cli.error(f"{pkg_root} already exists; use --force to overwrite")
        raise click.Abort()

    (theme_pkg_dir / "templates" / "partials").mkdir(parents=True, exist_ok=True)
    (theme_pkg_dir / "assets" / "css").mkdir(parents=True, exist_ok=True)
    (theme_pkg_dir / "dev" / "components").mkdir(parents=True, exist_ok=True)

    # Minimal package files
    (pkg_root / "README.md").write_text(
        f"# {package_name}\n\nA starter Bengal theme.\n",
        encoding="utf-8",
    )
    (pkg_root / "pyproject.toml").write_text(
        (
            "[project]\n"
            f'name = "{package_name}"\n'
            'version = "0.1.0"\n'
            'requires-python = ">=3.14"\n'
            'description = "A starter theme for Bengal SSG"\n'
            'readme = "README.md"\n'
            'license = {text = "MIT"}\n'
            "dependencies = []\n\n"
            "[project.entry-points.'bengal.themes']\n"
            f'{slug} = "bengal_themes.{slug}"\n'
        ),
        encoding="utf-8",
    )
    (pkg_root / "bengal_themes" / "__init__.py").write_text("__all__ = []\n", encoding="utf-8")
    (theme_pkg_dir / "__init__.py").write_text("__all__ = []\n", encoding="utf-8")
    (theme_pkg_dir / "templates" / "page.html").write_text(
        "{% extends 'page.html' %}\n{% block content %}<main>{{ content|default('Hello from ' ~ site.theme) }}</main>{% endblock %}\n",
        encoding="utf-8",
    )
    (theme_pkg_dir / "templates" / "partials" / "example.html").write_text(
        '<div class="example">Example Partial</div>\n',
        encoding="utf-8",
    )
    (theme_pkg_dir / "assets" / "css" / "style.css").write_text(
        "/* Your theme styles */\n", encoding="utf-8"
    )
    (theme_pkg_dir / "theme.toml").write_text(
        f'name="{slug}"\nextends="{extends}"\n',
        encoding="utf-8",
    )
    (theme_pkg_dir / "dev" / "components" / "example.yaml").write_text(
        "name: Example\ntemplate: partials/example.html\nvariants:\n  - id: default\n    name: Default\n    context: {}\n",
        encoding="utf-8",
    )

    cli.success(f"✓ Created package theme at {pkg_root}")
