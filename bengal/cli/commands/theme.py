"""Theme-related CLI commands (themes, swizzle)."""

from __future__ import annotations

import re
from pathlib import Path

import click

from bengal.cli.base import BengalGroup
from bengal.core.site import Site
from bengal.utils.cli_output import CLIOutput
from bengal.utils.swizzle import SwizzleManager
from bengal.utils.theme_registry import get_installed_themes, get_theme_package


@click.group(cls=BengalGroup)
def theme() -> None:
    """Theme utilities (list/info/discover/install, swizzle)."""
    pass


@theme.command()
@click.argument("template_path")
@click.argument("source", type=click.Path(exists=True), default=".")
def swizzle(template_path: str, source: str) -> None:
    """Copy a theme template/partial to project templates/ and track provenance."""
    cli = CLIOutput()
    site = Site.from_config(Path(source).resolve())
    mgr = SwizzleManager(site)
    dest = mgr.swizzle(template_path)
    cli.success(f"✓ Swizzled to {dest}")


@theme.command("swizzle-list")
@click.argument("source", type=click.Path(exists=True), default=".")
def swizzle_list(source: str) -> None:
    """List swizzled templates."""
    cli = CLIOutput()
    site = Site.from_config(Path(source).resolve())
    mgr = SwizzleManager(site)
    records = mgr.list()
    if not records:
        cli.info("No swizzled templates.")
        return
    for r in records:
        cli.info(f"- {r.target} (from {r.theme})")


@theme.command("swizzle-update")
@click.argument("source", type=click.Path(exists=True), default=".")
def swizzle_update(source: str) -> None:
    """Update swizzled templates if unchanged locally."""
    cli = CLIOutput()
    site = Site.from_config(Path(source).resolve())
    mgr = SwizzleManager(site)
    summary = mgr.update()
    cli.info(
        f"Updated: {summary['updated']}, Skipped (changed): {summary['skipped_changed']}, Missing upstream: {summary['missing_upstream']}"
    )


@theme.command("list")
@click.argument("source", type=click.Path(exists=True), default=".")
def list_themes(source: str) -> None:
    """List available themes (project, installed, bundled)."""
    cli = CLIOutput()
    site = Site.from_config(Path(source).resolve())

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
    except Exception:
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
@click.argument("slug")
@click.argument("source", type=click.Path(exists=True), default=".")
def info(slug: str, source: str) -> None:
    """Show theme info for a slug (source, version, paths)."""
    cli = CLIOutput()
    site = Site.from_config(Path(source).resolve())
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
    except Exception:
        pass


@theme.command("discover")
@click.argument("source", type=click.Path(exists=True), default=".")
def discover(source: str) -> None:
    """List swizzlable templates from the active theme chain."""
    cli = CLIOutput()
    site = Site.from_config(Path(source).resolve())
    from bengal.rendering.template_engine import TemplateEngine

    engine = TemplateEngine(site)
    # Walk all template directories in priority order
    seen: set[str] = set()
    for base in engine.template_dirs:
        for f in base.rglob("*.html"):
            rel = str(f.relative_to(base))
            if rel not in seen:
                seen.add(rel)
                cli.info(rel)


@theme.command("install")
@click.argument("name")
@click.option("--force", is_flag=True, help="Install even if name is non-canonical")
def install(name: str, force: bool) -> None:
    """Install a theme via uv pip.

    NAME may be a package or a slug. If a slug without prefix is provided,
    suggest canonical 'bengal-theme-<slug>'.
    """
    cli = CLIOutput()
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
    """Create a new theme scaffold.

    SLUG is the theme identifier used in config (e.g., [site].theme = SLUG).
    """
    slug = _sanitize_slug(slug)
    output_path = Path(output).resolve()

    if mode == "site":
        # Create under site's themes/<slug>
        site_root = output_path
        theme_dir = site_root / "themes" / slug
        if theme_dir.exists() and not force:
            raise click.ClickException(f"{theme_dir} already exists; use --force to overwrite")
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

        cli = CLIOutput()
        cli.success(f"✓ Created site theme at {theme_dir}")
        return

    # package mode
    package_name = f"bengal-theme-{slug}"
    pkg_root = output_path / package_name
    theme_pkg_dir = pkg_root / "bengal_themes" / slug
    if pkg_root.exists() and not force:
        raise click.ClickException(f"{pkg_root} already exists; use --force to overwrite")

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

    cli = CLIOutput()
    cli.success(f"✓ Created package theme at {pkg_root}")


# Compatibility export for tests
theme_list = list_themes
