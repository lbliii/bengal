"""Theme group — theme development, directives, and assets."""

from __future__ import annotations

from typing import Annotated

from milo import Description


def theme_list(
    source: Annotated[str, Description("Source directory path")] = "",
) -> dict:
    """List available themes."""

    from bengal.cli.utils import get_cli_output, load_site_from_cli

    source = source or "."
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)

    from bengal.themes import get_installed_themes

    themes = get_installed_themes(site)

    cli.render_write(
        "item_list.kida",
        title="Available Themes",
        items=[{"name": t.slug, "description": f"{t.name}  {t.source}"} for t in themes],
    )

    return {"themes": [{"slug": t.slug, "name": t.name, "source": t.source} for t in themes]}


def theme_info(
    slug: Annotated[str, Description("Theme identifier")],
    source: Annotated[str, Description("Source directory path")] = "",
) -> dict:
    """Show theme details."""
    from bengal.cli.utils import get_cli_output, load_site_from_cli
    from bengal.themes import get_theme_package

    source = source or "."
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    theme = get_theme_package(slug, site)

    items = [
        {"label": "Name", "value": theme.name},
        {"label": "Location", "value": str(theme.path)},
    ]
    if hasattr(theme, "version"):
        items.append({"label": "Version", "value": str(theme.version)})
    cli.render_write("kv_detail.kida", title=f"Theme: {slug}", items=items)

    return {"slug": slug, "name": theme.name, "path": str(theme.path)}


def theme_discover(
    source: Annotated[str, Description("Source directory path")] = "",
) -> dict:
    """List swizzlable templates from active theme chain."""
    from bengal.cli.utils import get_cli_output, load_site_from_cli
    from bengal.rendering.engines import create_engine

    source = source or "."
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    engine = create_engine(site)
    templates = engine.list_templates()

    cli.render_write(
        "item_list.kida",
        title=f"Swizzlable Templates ({len(templates)})",
        items=[{"name": t, "description": ""} for t in templates],
    )

    return {"templates": templates, "count": len(templates)}


def theme_swizzle(
    template_path: Annotated[str, Description("Template path (e.g. layouts/article.html)")],
    source: Annotated[str, Description("Source directory path")] = "",
) -> dict:
    """Copy a theme template to project for customization."""
    from bengal.cli.utils import get_cli_output, load_site_from_cli
    from bengal.themes.swizzle import SwizzleManager

    source = source or "."
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    manager = SwizzleManager(site)
    result = manager.swizzle(template_path)

    cli.success(f"Swizzled: {template_path} -> {result.destination}")
    return {"template": template_path, "destination": str(result.destination)}


def theme_install(
    name: Annotated[str, Description("Package name or slug")],
    force: Annotated[bool, Description("Install even if name is non-canonical")] = False,
) -> dict:
    """Install a theme from PyPI."""
    import re
    import subprocess

    from bengal.cli.utils import get_cli_output

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

    from bengal.cli.utils import get_cli_output

    cli = get_cli_output()
    path = Path(theme_path).resolve()

    if not path.exists():
        cli.error(f"Theme directory not found: {path}")
        raise SystemExit(1)

    errors = []

    # Check for theme config
    has_config = (path / "theme.toml").exists() or (path / "theme.yaml").exists()
    if not has_config:
        errors.append("Missing theme.toml or theme.yaml")

    # Check for templates
    templates_dir = path / "templates"
    if not templates_dir.exists():
        errors.append("Missing templates/ directory")
    else:
        for required in ["base.html", "page.html", "home.html"]:
            found = list(templates_dir.rglob(required))
            if not found:
                errors.append(f"Missing required template: {required}")

    if errors:
        cli.render_write(
            "validation_report.kida",
            title="Theme Validation",
            issues=[{"level": "error", "message": e} for e in errors],
            summary={"errors": len(errors), "warnings": 0, "passed": 0},
        )
        raise SystemExit(1)

    cli.render_write(
        "validation_report.kida",
        issues=[{"level": "success", "message": f"Theme at {path} is valid"}],
        summary={"errors": 0, "warnings": 0, "passed": 1},
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

    from bengal.cli.utils import get_cli_output

    cli = get_cli_output()
    slug = re.sub(r"[^a-z0-9_-]", "-", slug.lower().strip())
    output_dir = Path(output).resolve() / slug if mode == "site" else Path(output).resolve()

    if output_dir.exists() and not force:
        cli.error(f"Directory already exists: {output_dir}")
        cli.info("Use --force to overwrite")
        raise SystemExit(1)

    # Create scaffold
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "templates").mkdir(exist_ok=True)
    (output_dir / "templates" / "partials").mkdir(exist_ok=True)
    (output_dir / "assets" / "css").mkdir(parents=True, exist_ok=True)

    # Theme config
    theme_config = f'[theme]\nname = "{slug}"\nextends = "{extends}"\n'
    (output_dir / "theme.toml").write_text(theme_config)

    # Base template
    (output_dir / "templates" / "base.html").write_text(
        "<!DOCTYPE html>\n<html>\n<head><title>{{ page.title }}</title></head>\n<body>{% block content %}{% endblock %}</body>\n</html>\n"
    )
    (output_dir / "templates" / "page.html").write_text(
        '{% extends "base.html" %}\n{% block content %}{{ page.content }}{% endblock %}\n'
    )
    (output_dir / "templates" / "home.html").write_text(
        '{% extends "base.html" %}\n{% block content %}<h1>Welcome</h1>{{ page.content }}{% endblock %}\n'
    )

    cli.render_write(
        "scaffold_result.kida",
        title=f"Theme scaffold: {slug}",
        entries=[
            {"name": "theme.toml", "note": "theme config"},
            {"name": "templates/", "note": "3 files"},
            {"name": "templates/partials/", "note": ""},
            {"name": "assets/css/", "note": ""},
        ],
        steps=[
            f"Edit {output_dir}/theme.toml",
            f"Customize templates in {output_dir}/templates/",
            "Run: bengal serve",
        ],
        summary="Theme scaffold created!",
    )

    return {"slug": slug, "path": str(output_dir), "mode": mode, "extends": extends}


def theme_debug(
    source: Annotated[str, Description("Source directory path")] = "",
    template: Annotated[str, Description("Show resolution path for specific template")] = "",
) -> dict:
    """Debug theme resolution and paths."""
    from bengal.cli.utils import get_cli_output, load_site_from_cli

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

    from bengal.cli.utils import get_cli_output
    from bengal.debug import ShortcodeSandbox

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

    from bengal.cli.utils import get_cli_output
    from bengal.debug import ShortcodeSandbox

    cli = get_cli_output()
    sandbox = ShortcodeSandbox()

    if file:
        content = Path(file).read_text(encoding="utf-8")
    elif content:
        content = content.replace("\\n", "\n")
    else:
        cli.warning("No content provided.")
        cli.info("Usage: bengal theme test '<content>' or --file <path>")
        return None

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
    from bengal.cli.utils import get_cli_output, load_site_from_cli

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
        return None

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

    return None
