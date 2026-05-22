"""Theme group — theme development, directives, and assets."""

from __future__ import annotations

from typing import Annotated

from milo import Description


def _active_theme_slug(site) -> str:
    config = site.config
    if hasattr(config, "get"):
        build = config.get("build", {})
        if isinstance(build, dict) and build.get("theme"):
            return str(build["theme"])
        if config.get("theme"):
            return str(config["theme"])
    return "default"


def _validate_theme_directory(path):
    from bengal.themes.metadata import load_theme_metadata

    metadata_result = load_theme_metadata(path)
    errors = [issue.message for issue in metadata_result.errors]
    warnings = [issue.message for issue in metadata_result.warnings]

    templates_dir = path / "templates"
    if not templates_dir.exists():
        errors.append("Missing templates/ directory")
    else:
        for required in ["base.html", "page.html", "home.html"]:
            found = list(templates_dir.rglob(required))
            if not found:
                errors.append(f"Missing required template: {required}")

    assets_dir = path / "assets"
    if not assets_dir.exists():
        warnings.append("Missing assets/ directory; theme will rely entirely on parent assets")

    return errors, warnings


def theme_list(
    source: Annotated[str, Description("Source directory path")] = "",
) -> dict:
    """List available themes."""

    from bengal.cli.utils import load_site_from_cli
    from bengal.output import get_cli_output

    source = source or "."
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)

    from bengal.themes.resolver import ThemeResolver

    records = ThemeResolver(site.root_path).iter_available()
    items = [
        {
            "name": record.slug,
            "description": (
                "Bundled theme"
                if record.source == "bundled"
                else "Site-local theme"
                if record.source == "site-local"
                else record.distribution or record.package or "Installed theme"
            ),
        }
        for record in records
    ]

    cli.render_write(
        "command_list.kida",
        title="Available Themes",
        summary=f"{len(items)} theme(s) available",
        items=items,
    )

    return {
        "themes": [
            {"slug": record.slug, "name": record.name, "source": record.source}
            for record in records
        ]
    }


def theme_info(
    slug: Annotated[str, Description("Theme identifier")],
    source: Annotated[str, Description("Source directory path")] = "",
) -> dict:
    """Show theme details."""
    from bengal.cli.utils import load_site_from_cli
    from bengal.output import get_cli_output
    from bengal.themes.resolver import ThemeResolver

    source = source or "."
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)

    record = ThemeResolver(site.root_path).resolve(slug)
    if record is None:
        cli.error(f"Theme not found: {slug}")
        cli.tip("Run `bengal theme list` to see available themes.")
        raise SystemExit(1)

    items = [
        {"label": "Name", "value": record.name},
        {"label": "Source", "value": record.source},
    ]
    if record.path is not None:
        items.append({"label": "Location", "value": str(record.path)})
    if record.package:
        items.append({"label": "Package", "value": record.package})
    if record.distribution:
        items.append({"label": "Distribution", "value": record.distribution})
    parent = record.metadata.get("extends") or record.metadata.get("parent")
    if parent:
        items.append({"label": "Extends", "value": str(parent)})
    if record.version:
        items.append({"label": "Version", "value": str(record.version)})
    cli.render_write("kv_detail.kida", title=f"Theme: {slug}", items=items)

    result = {
        "slug": record.slug,
        "name": record.name,
        "source": record.source,
    }
    if record.path is not None:
        result["path"] = str(record.path)
    if record.package:
        result["package"] = record.package
    if record.distribution:
        result["distribution"] = record.distribution
    if record.version:
        result["version"] = record.version
    return result


def theme_discover(
    source: Annotated[str, Description("Source directory path")] = "",
) -> dict:
    """List swizzlable templates from active theme chain."""
    from bengal.cli.utils import load_site_from_cli
    from bengal.output import get_cli_output
    from bengal.rendering.engines import create_engine

    source = source or "."
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    engine = create_engine(site)
    templates = engine.list_templates()

    cli.render_write(
        "command_list.kida",
        title=f"Swizzlable Templates ({len(templates)})",
        items=[{"name": t, "description": ""} for t in templates],
    )

    return {"templates": templates, "count": len(templates)}


def theme_swizzle(
    template_path: Annotated[str, Description("Template path (e.g. layouts/article.html)")],
    source: Annotated[str, Description("Source directory path")] = "",
) -> dict:
    """Copy a theme template to project for customization."""
    from bengal.cli.utils import load_site_from_cli
    from bengal.output import get_cli_output
    from bengal.themes.swizzle import SwizzleManager

    source = source or "."
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    manager = SwizzleManager(site)
    destination = manager.swizzle(template_path)

    cli.success(f"Swizzled: {template_path} -> {destination}")
    return {"template": template_path, "destination": str(destination)}


def theme_swizzle_list(
    source: Annotated[str, Description("Source directory path")] = "",
) -> dict:
    """List templates that have been swizzled into the project."""
    from bengal.cli.utils import load_site_from_cli
    from bengal.output import get_cli_output
    from bengal.themes.swizzle import SwizzleManager

    source = source or "."
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    records = SwizzleManager(site).list()

    if not records:
        cli.render_write(
            "command_empty.kida",
            title="Swizzled Templates",
            message="No swizzled templates found.",
            hint="Run `bengal theme swizzle --template-path <template>` to customize one.",
        )
        return {"templates": [], "count": 0}

    cli.render_write(
        "command_list.kida",
        title=f"Swizzled Templates ({len(records)})",
        items=[
            {
                "name": record.target,
                "description": f"from {record.theme}",
            }
            for record in records
        ],
    )
    return {
        "templates": [
            {"target": record.target, "theme": record.theme, "source": record.source}
            for record in records
        ],
        "count": len(records),
    }


def theme_swizzle_update(
    source: Annotated[str, Description("Source directory path")] = "",
    force: Annotated[bool, Description("Overwrite locally modified swizzled templates")] = False,
) -> dict:
    """Update unchanged swizzled templates from their theme sources."""
    from bengal.cli.utils import load_site_from_cli
    from bengal.output import get_cli_output
    from bengal.themes.swizzle import SwizzleManager

    source = source or "."
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    result = SwizzleManager(site).update(force=force)

    issues = []
    if result["skipped_changed"]:
        issues.append(
            {
                "level": "warning",
                "message": f"{result['skipped_changed']} locally modified template(s) skipped",
            }
        )
    if result["skipped_error"]:
        issues.append(
            {
                "level": "warning",
                "message": f"{result['skipped_error']} template(s) skipped due to checksum errors",
            }
        )
    if result["missing_upstream"]:
        issues.append(
            {
                "level": "warning",
                "message": f"{result['missing_upstream']} upstream template(s) were not found",
            }
        )
    if result["updated"] or result["force_updated"]:
        issues.append(
            {
                "level": "success",
                "message": (
                    f"Updated {result['updated']} template(s)"
                    f" and force-updated {result['force_updated']} template(s)"
                ),
            }
        )
    if not issues:
        issues.append({"level": "success", "message": "No swizzled templates needed updates"})

    cli.render_write(
        "validation_report.kida",
        title="Swizzle Update",
        issues=issues,
        summary={
            "errors": 0,
            "warnings": result["skipped_changed"]
            + result["skipped_error"]
            + result["missing_upstream"],
            "passed": result["updated"] + result["force_updated"],
        },
    )
    return result


def theme_install(
    name: Annotated[str, Description("Package name or slug")],
    force: Annotated[bool, Description("Install even if name is non-canonical")] = False,
) -> dict:
    """Install a theme from PyPI."""
    import re
    import subprocess

    from bengal.output import get_cli_output

    cli = get_cli_output()
    SAFE_PACKAGE_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

    if not SAFE_PACKAGE_PATTERN.match(name) and not force:
        cli.error(f"Package name '{name}' doesn't match safe pattern")
        cli.info("Use --force to override")
        raise SystemExit(1)

    cli.info(f"Installing theme: {name}")
    try:
        subprocess.run(["uv", "pip", "install", name], check=True)
    except subprocess.CalledProcessError, FileNotFoundError:
        subprocess.run(["pip", "install", name], check=True)

    cli.success(f"Theme '{name}' installed")
    return {"name": name}


def theme_validate(
    theme_path: Annotated[str, Description("Path to theme directory")],
) -> dict:
    """Validate theme directory structure."""
    from pathlib import Path

    from bengal.output import get_cli_output

    cli = get_cli_output()
    path = Path(theme_path).resolve()

    if not path.exists():
        cli.error(f"Theme directory not found: {path}")
        cli.tip("Pass a valid path, or run `bengal theme list` to see available themes.")
        raise SystemExit(1)

    errors, warnings = _validate_theme_directory(path)

    if errors:
        cli.render_write(
            "validation_report.kida",
            title="Theme Validation",
            issues=[
                *[{"level": "error", "message": e} for e in errors],
                *[{"level": "warning", "message": warning} for warning in warnings],
            ],
            summary={"errors": len(errors), "warnings": len(warnings), "passed": 0},
        )
        raise SystemExit(1)

    cli.render_write(
        "validation_report.kida",
        title="Theme Validation",
        issues=[
            {"level": "success", "message": f"Theme at {path} is valid"},
            *[{"level": "warning", "message": warning} for warning in warnings],
        ],
        summary={"errors": 0, "warnings": len(warnings), "passed": 1},
    )
    return {"path": str(path), "valid": True}


def theme_new(
    slug: Annotated[str, Description("Theme identifier")],
    mode: Annotated[str, Description("Scaffold mode: site or package")] = "site",
    output: Annotated[str, Description("Output directory")] = ".",
    extends: Annotated[str, Description("Parent theme to extend")] = "default",
    force: Annotated[bool, Description("Overwrite existing directory")] = False,
) -> dict:
    """Create a new theme scaffold."""
    import re
    from pathlib import Path

    from bengal.output import get_cli_output
    from bengal.utils.io.atomic_write import atomic_write_text

    cli = get_cli_output()
    slug = re.sub(r"[^a-z0-9_-]", "-", slug.lower().strip())
    package_name = f"bengal-theme-{slug}"
    output_root = Path(output).resolve()
    if mode == "site":
        output_dir = output_root / "themes" / slug
    elif mode == "package":
        output_dir = output_root / package_name
    else:
        cli.error(f"Unknown scaffold mode: {mode}")
        cli.tip("Use --mode site or --mode package.")
        raise SystemExit(2)

    if output_dir.exists() and not force:
        cli.error(f"Directory already exists: {output_dir}")
        cli.info("Use --force to overwrite")
        raise SystemExit(1)

    theme_root = output_dir
    if mode == "package":
        package_slug = slug.replace("-", "_")
        theme_root = output_dir / "bengal_themes" / package_slug
        (output_dir / "bengal_themes").mkdir(parents=True, exist_ok=True)
        atomic_write_text(output_dir / "bengal_themes" / "__init__.py", "")
        atomic_write_text(theme_root / "__init__.py", "")
        atomic_write_text(
            output_dir / "pyproject.toml",
            (
                "[build-system]\n"
                'requires = ["setuptools>=68"]\n'
                'build-backend = "setuptools.build_meta"\n\n'
                "[project]\n"
                f'name = "{package_name}"\n'
                'version = "0.1.0"\n'
                f'description = "Bengal theme: {slug}"\n'
                'requires-python = ">=3.14"\n\n'
                "[tool.setuptools.packages.find]\n"
                'include = ["bengal_themes*"]\n\n'
                "[tool.setuptools.package-data]\n"
                f'"bengal_themes.{package_slug}" = ["theme.toml", "templates/**/*.html", "assets/**/*"]\n\n'
                '[project.entry-points."bengal.themes"]\n'
                f'{slug} = "bengal_themes.{package_slug}"\n'
            ),
        )

    # Create scaffold
    theme_root.mkdir(parents=True, exist_ok=True)
    (theme_root / "templates").mkdir(exist_ok=True)
    (theme_root / "templates" / "partials").mkdir(exist_ok=True)
    (theme_root / "assets" / "css").mkdir(parents=True, exist_ok=True)

    theme_config = f'name = "{slug}"\nextends = "{extends}"\nversion = "0.1.0"\n'
    atomic_write_text(theme_root / "theme.toml", theme_config)

    atomic_write_text(
        theme_root / "templates" / "base.html",
        (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '  <meta charset="utf-8">\n'
            '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
            "  <title>{% block title %}{{ page.title ?? site.title }}{% endblock %}</title>\n"
            '  <link rel="stylesheet" href="{{ asset_url(\'css/style.css\') }}">\n'
            "</head>\n"
            "<body>\n"
            "  {% block content %}{% endblock %}\n"
            "</body>\n"
            "</html>\n"
        ),
    )
    atomic_write_text(
        theme_root / "templates" / "page.html",
        (
            '{% extends "base.html" %}\n'
            "{% block content %}\n"
            '<main class="theme-page">\n'
            "  <h1>{{ page.title }}</h1>\n"
            "  {{ content | safe }}\n"
            "</main>\n"
            "{% endblock %}\n"
        ),
    )
    atomic_write_text(
        theme_root / "templates" / "home.html",
        (
            '{% extends "base.html" %}\n'
            "{% block content %}\n"
            '<main class="theme-home">\n'
            "  <h1>{{ site.title }}</h1>\n"
            "  {{ content | safe }}\n"
            "</main>\n"
            "{% endblock %}\n"
        ),
    )
    atomic_write_text(
        theme_root / "assets" / "css" / "style.css",
        (
            f"/* Theme: {slug} */\n"
            ":root {\n"
            "  --color-primary: #2563eb;\n"
            "  --color-text: #1f2937;\n"
            "  --color-background: #ffffff;\n"
            "}\n\n"
            "body {\n"
            "  margin: 0;\n"
            "  color: var(--color-text);\n"
            "  background: var(--color-background);\n"
            "  font-family: system-ui, sans-serif;\n"
            "  line-height: 1.6;\n"
            "}\n\n"
            ".theme-page,\n"
            ".theme-home {\n"
            "  max-width: 72rem;\n"
            "  margin-inline: auto;\n"
            "  padding: 2rem;\n"
            "}\n"
        ),
    )
    atomic_write_text(
        theme_root / "README.md",
        (
            f"# {slug}\n\n"
            "A Bengal theme scaffold.\n\n"
            "## Use\n\n"
            "```toml\n"
            "[build]\n"
            f'theme = "{slug}"\n'
            "```\n"
        ),
    )

    cli.render_write(
        "scaffold_result.kida",
        title=f"Theme scaffold: {slug}",
        entries=[
            {"name": str(output_dir), "note": mode},
            {"name": "theme.toml", "note": "theme metadata"},
            {"name": "templates/", "note": "3 files"},
            {"name": "templates/partials/", "note": ""},
            {"name": "assets/css/", "note": ""},
        ],
        steps=[
            f"Edit {theme_root}/theme.toml",
            f"Customize templates in {theme_root}/templates/",
            "Run: bengal serve",
        ],
        summary="Theme scaffold created!",
    )

    return {
        "slug": slug,
        "path": str(output_dir),
        "theme_path": str(theme_root),
        "mode": mode,
        "extends": extends,
    }


def theme_preview(
    source: Annotated[str, Description("Source directory path")] = "",
    host: Annotated[str, Description("Server host address")] = "localhost",
    port: Annotated[int, Description("Server port number")] = 5173,
    open_browser: Annotated[bool, Description("Open browser after server starts")] = True,
) -> dict:
    """Start a theme-focused dev server with live reload."""
    from bengal.cli.milo_commands.serve import serve
    from bengal.cli.utils import load_site_from_cli
    from bengal.output import get_cli_output
    from bengal.themes.resolver import ThemeResolver

    source = source or "."
    cli = get_cli_output()
    site = load_site_from_cli(
        source=source,
        config=None,
        environment="local",
        profile="theme-dev",
        cli=cli,
    )
    active_theme = _active_theme_slug(site)
    resolver = ThemeResolver(site.root_path)
    record = resolver.resolve(active_theme)
    if record is None:
        cli.error(f"Theme not found: {active_theme}")
        cli.tip("Run `bengal theme list` to see available themes.")
        raise SystemExit(1)

    items = [
        {"label": "Active theme", "value": record.slug},
        {"label": "Source", "value": record.source},
        {"label": "Server", "value": f"http://{host}:{port}"},
        {"label": "Watch", "value": "enabled"},
    ]
    watched_dirs = [str(site.root_path / "content"), str(site.root_path / "templates")]
    if record.path is not None:
        watched_dirs.append(str(record.path))
        items.append({"label": "Theme path", "value": str(record.path)})

    cli.render_write("kv_detail.kida", title="Theme Preview", items=items)
    cli.render_write(
        "command_list.kida",
        title="Watched Paths",
        items=[{"name": path, "description": ""} for path in watched_dirs],
    )

    if record.path is not None:
        errors, warnings = _validate_theme_directory(record.path)
        if errors or warnings:
            cli.render_write(
                "validation_report.kida",
                title="Theme Preview Preflight",
                issues=[
                    *[{"level": "error", "message": error} for error in errors],
                    *[{"level": "warning", "message": warning} for warning in warnings],
                ],
                summary={"errors": len(errors), "warnings": len(warnings), "passed": 0},
            )
        if errors:
            raise SystemExit(1)

    return serve(
        source=source,
        host=host,
        port=port,
        watch=True,
        auto_port=True,
        open_browser=open_browser,
        profile="theme-dev",
    )


def theme_debug(
    source: Annotated[str, Description("Source directory path")] = "",
    template: Annotated[str, Description("Show resolution path for specific template")] = "",
) -> dict:
    """Debug theme resolution and paths."""
    from bengal.cli.utils import load_site_from_cli
    from bengal.output import get_cli_output

    source = source or "."
    template_val = template or None
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)

    from bengal.core.theme import resolve_theme_chain

    active_theme = site.config.get("theme", "default") if hasattr(site.config, "get") else "default"
    chain = resolve_theme_chain(site.root_path, active_theme)

    cli.render_write(
        "item_list.kida",
        title="Theme Chain",
        items=[{"name": f"{i + 1}. {name}", "description": ""} for i, name in enumerate(chain)],
    )

    if template_val:
        from bengal.rendering.engines import create_engine

        engine = create_engine(site)
        resolution_items = []
        for tdir in engine.template_dirs:
            candidate = tdir / template_val
            exists = candidate.exists()
            resolution_items.append(
                {"name": f"{'*' if exists else ' '} {candidate}", "description": ""}
            )
        cli.render_write(
            "item_list.kida",
            title=f"Resolution for '{template_val}'",
            items=resolution_items,
        )

    return {"chain": [{"slug": name, "path": ""} for name in chain]}


# --- Absorbed from shortcodes ---


def theme_directives(
    output_format: Annotated[str, Description("Output format: table or json")] = "table",
) -> dict:
    """List available MyST directives."""
    import json

    from bengal.debug import ShortcodeSandbox
    from bengal.output import get_cli_output

    cli = get_cli_output()
    sandbox = ShortcodeSandbox()
    directives = sandbox.list_directives()

    if output_format == "json":
        cli.render_write("json_output.kida", data=json.dumps(directives, indent=2))
        return {"directives": directives, "count": len(directives)}

    cli.render_write(
        "item_list.kida",
        title=f"Available Directives ({len(directives)} types)",
        items=[
            {
                "name": ", ".join(d["names"]),
                "description": d["description"].split("\n")[0].strip() if d["description"] else "",
            }
            for d in directives
        ],
    )

    return {"directives": directives, "count": len(directives)}


def theme_test(
    content: Annotated[str, Description("Directive markdown content")] = "",
    file: Annotated[str, Description("Read content from file")] = "",
    validate_only: Annotated[bool, Description("Only validate syntax, don't render")] = False,
    output_format: Annotated[str, Description("Output format: console, html, json")] = "console",
) -> dict:
    """Render a directive in isolation for testing."""
    import json
    from pathlib import Path

    from bengal.debug import ShortcodeSandbox
    from bengal.output import get_cli_output

    cli = get_cli_output()
    sandbox = ShortcodeSandbox()

    if file:
        content = Path(file).read_text(encoding="utf-8")
    elif content:
        content = content.replace("\\n", "\n")
    else:
        cli.warning("No content provided.")
        cli.info("Usage: bengal theme test '<content>' or --file <path>")
        return {"status": "skipped", "message": "No content provided"}

    if validate_only:
        validation = sandbox.validate(content)
        if output_format == "json":
            cli.render_write(
                "json_output.kida",
                data=json.dumps(
                    {
                        "valid": validation.valid,
                        "directive": validation.directive_name,
                        "errors": validation.errors,
                        "suggestions": validation.suggestions,
                    },
                    indent=2,
                ),
            )
        elif validation.valid:
            cli.success(f"Valid syntax: {validation.directive_name or 'no directive'}")
        else:
            cli.render_write(
                "validation_report.kida",
                issues=[{"level": "error", "message": err} for err in validation.errors],
                summary={"errors": len(validation.errors), "warnings": 0, "passed": 0},
            )
        return {
            "valid": validation.valid,
            "directive": validation.directive_name,
            "errors": validation.errors,
        }

    result = sandbox.render(content)

    if output_format == "json":
        cli.render_write(
            "json_output.kida",
            data=json.dumps(
                {
                    "success": result.success,
                    "directive": result.directive_name,
                    "html": result.html,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "parse_time_ms": result.parse_time_ms,
                    "render_time_ms": result.render_time_ms,
                },
                indent=2,
            ),
        )
    elif output_format == "html":
        cli.info(result.html)
    elif result.success:
        cli.render_write(
            "kv_detail.kida",
            title=f"Rendered: {result.directive_name}",
            items=[
                {"label": "Parse", "value": f"{result.parse_time_ms:.2f}ms"},
                {"label": "Render", "value": f"{result.render_time_ms:.2f}ms"},
            ],
        )
        cli.blank()
        cli.info(result.html)
    else:
        cli.render_write(
            "validation_report.kida",
            issues=[{"level": "error", "message": err} for err in result.errors],
            summary={"errors": len(result.errors), "warnings": 0, "passed": 0},
        )

    return {
        "success": result.success,
        "directive": result.directive_name,
        "parse_time_ms": result.parse_time_ms,
        "render_time_ms": result.render_time_ms,
    }


# --- Absorbed from assets ---


def theme_assets(
    source: Annotated[str, Description("Source directory path")] = "",
    watch: Annotated[bool, Description("Watch and rebuild on changes")] = False,
) -> dict:
    """Build assets using the configured pipeline."""
    import time
    from pathlib import Path

    from bengal.assets.pipeline import from_site as pipeline_from_site
    from bengal.cli.utils import load_site_from_cli
    from bengal.output import get_cli_output

    source = source or "."
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)

    def run_once():
        try:
            start_time = time.time()
            pipeline = pipeline_from_site(site)
            outputs = pipeline.build()
            elapsed_ms = (time.time() - start_time) * 1000
            cli.phase("Assets", duration_ms=elapsed_ms, details=f"{len(outputs)} outputs")
        except Exception as e:
            cli.error(f"Asset pipeline failed: {e}")
            cli.tip("Re-run with --verbose to see which asset failed, then check its source file.")

    if not watch:
        run_once()
        return {"source": source, "watch": False}

    run_once()

    root = Path(source).resolve()
    watch_dirs: list[str] = []
    assets_dir = root / "assets"
    if assets_dir.exists():
        watch_dirs.append(str(assets_dir))
    theme = getattr(site, "theme", None)
    if theme:
        theme_path = getattr(theme, "assets_path", None) or getattr(theme, "path", None)
        if theme_path:
            theme_assets = Path(theme_path) / "assets"
            if theme_assets.exists():
                watch_dirs.append(str(theme_assets))

    if not watch_dirs:
        cli.warning("No assets directories found to watch.")
        return {"status": "skipped", "message": "No assets directories found to watch"}

    try:
        import watchfiles
    except ImportError:
        cli.error("watchfiles is required for --watch: pip install watchfiles")
        raise SystemExit(1) from None

    cli.info(f"Watching {len(watch_dirs)} directory(ies) for changes... Press Ctrl+C to stop.")
    try:
        for changes in watchfiles.watch(*watch_dirs, debounce=1000):
            changed_files = [Path(path) for _, path in changes]
            names = ", ".join(p.name for p in changed_files[:3])
            if len(changed_files) > 3:
                names += f" (+{len(changed_files) - 3} more)"
            cli.info(f"Changed: {names}")
            run_once()
    except KeyboardInterrupt:
        cli.blank()
        cli.warning("Stopped asset watcher.")

    return {"status": "ok", "message": "Asset watcher stopped"}
