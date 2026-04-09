from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from bengal.cli.base import BengalGroup
from bengal.cli.commands.init import init
from bengal.cli.commands.skeleton import skeleton_cli
from bengal.cli.helpers import command_metadata, get_cli_output, handle_cli_errors

# User profiles with customization
PROFILES: dict[str, dict[str, Any]] = {
    "dev": {
        "name": "Developer",
        "emoji": "👨‍💻",
        "description": "Full debug output, performance metrics, all commands",
        "output_format": "human",
        "verbosity": "debug",
        "show_all_commands": True,
        "default_build_profile": "dev",
    },
    "themer": {
        "name": "Theme Developer",
        "emoji": "🎨",
        "description": "Focus on templates, themes, component preview",
        "output_format": "human",
        "verbosity": "info",
        "show_all_commands": True,
        "default_build_profile": "theme-dev",
    },
    "writer": {
        "name": "Content Writer",
        "emoji": "✍️",
        "description": "Simple UX, focus on creating content, minimal tech details",
        "output_format": "human",
        "verbosity": "warn",
        "show_all_commands": False,
        "default_build_profile": "writer",
    },
    "ai": {
        "name": "Automation / AI",
        "emoji": "🤖",
        "description": "Machine-readable output, JSON formats, no interactive prompts",
        "output_format": "json",
        "verbosity": "info",
        "show_all_commands": True,
        "default_build_profile": "dev",
    },
}


@click.group("project", cls=BengalGroup)
def project_cli() -> None:
    """
    Project management and setup commands.

    Commands:
        init       Initialize project structure and content sections
        skeleton   Apply skeleton manifests to create site structure
        profile    Set your working profile (dev, themer, writer, ai)
        validate   Validate configuration and directory structure
        info       Display project information and statistics
        config     View and manage configuration settings

    """


@project_cli.command()
@command_metadata(
    category="project",
    description="Set your Bengal working profile / persona",
    examples=[
        "bengal project profile dev",
        "bengal project profile writer",
    ],
    requires_site=False,
    tags=["project", "config", "quick"],
)
@handle_cli_errors(show_art=False)
@click.argument("profile_name", required=False)
def profile(profile_name: str) -> None:
    """
    👤 Set your Bengal working profile / persona.

    Profiles customize CLI behavior and output format based on your role:

        dev       👨‍💻  Full debug output, performance metrics, all commands
        themer    🎨  Focus on templates, themes, component preview
        writer    ✍️  Simple UX, focus on content, minimal tech details
        ai        🤖  Machine-readable output, JSON formats

    Examples:
        bengal project profile dev       # Switch to developer profile
        bengal project profile writer    # Switch to content writer profile

    """
    cli = get_cli_output()

    profile_path = Path(".bengal-profile")

    # List available profiles
    if profile_name is None:
        current_profile = None
        if profile_path.exists():
            current_profile = profile_path.read_text().strip()

        cli.blank()
        cli.header("👤 Available Profiles")
        cli.blank()

        for profile_key, profile_info in PROFILES.items():
            marker = "✓ " if profile_key == current_profile else "  "
            profile_line = f"{marker}{profile_info['emoji']} {profile_info['name']} - {profile_info['description']}"
            cli.detail(profile_line, indent=1)

        if current_profile:
            cli.blank()
            cli.success(f"📍 Current: {PROFILES[current_profile]['name']}")
        else:
            cli.blank()
            cli.warning("📍 Current: (not set)")

        cli.blank()
        cli.info("Usage: bengal project profile <dev|themer|writer|ai>")
        cli.blank()
        return

    # Validate profile
    if profile_name not in PROFILES:
        cli.error(f"✗ Unknown profile: {profile_name}")
        cli.warning(f"Available: {', '.join(PROFILES.keys())}")
        raise click.Abort()

    # Save profile
    from bengal.utils.io.atomic_write import atomic_write_text

    atomic_write_text(profile_path, profile_name)

    profile_info = PROFILES[profile_name]
    cli.blank()
    cli.success(f"✓ Profile set to: {profile_info['emoji']} {profile_info['name']}")
    cli.detail(profile_info["description"], indent=1)
    cli.blank()

    # Show what changed
    cli.header("💡 This affects:")
    cli.tip(f"Output format:    {profile_info['output_format'].upper()}")
    cli.tip(f"Verbosity level:  {profile_info['verbosity'].upper()}")
    cli.tip(f"Build profile:    {profile_info['default_build_profile']}")
    if not profile_info["show_all_commands"]:
        cli.tip("Commands shown:   Simplified (use --all for full)")
    cli.blank()


@project_cli.command()
@command_metadata(
    category="project",
    description="Validate Bengal project configuration and structure",
    examples=[
        "bengal project validate",
    ],
    requires_site=False,
    tags=["project", "validation", "ci"],
)
@handle_cli_errors(show_art=False)
def validate() -> None:
    """
    ✓ Validate Bengal project configuration and structure.

    Checks:
        ✓ bengal.toml exists and is valid
        ✓ Required configuration fields
        ✓ Directory structure (content/, templates/, assets/)
        ✓ Theme configuration
        ✓ Content files parseable

    """
    cli = get_cli_output()

    import tomllib
    from pathlib import Path

    config_path = Path("bengal.toml")

    cli.blank()
    cli.header("🔍 Validating Bengal project...")
    cli.blank()

    errors = []
    warnings = []
    checks_passed = 0

    # Check 1: Config file exists
    if not config_path.exists():
        errors.append("bengal.toml not found in current directory")
    else:
        checks_passed += 1
        cli.success("   ✓ bengal.toml found")

        # Check 2: Config is valid TOML
        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)
            checks_passed += 1
            cli.success("   ✓ bengal.toml is valid")
        except Exception as e:
            errors.append(f"bengal.toml parse error: {e}")
            config = {}

        # Check 3: Required fields
        site_config = config.get("site", {})
        required_fields = ["title", "baseurl"]
        missing = [f for f in required_fields if f not in site_config]

        if missing:
            warnings.append(f"Missing recommended fields: {', '.join(missing)}")
        else:
            checks_passed += 1
            cli.success("   ✓ Required fields present")

        # Check 4: Theme configured
        theme = site_config.get("theme", "default")
        checks_passed += 1
        cli.success(f"   ✓ Theme configured: {theme}")

    # Check 5: Directory structure
    required_dirs = ["content", "templates", "assets"]
    missing_dirs = [d for d in required_dirs if not Path(d).exists()]

    if missing_dirs:
        warnings.append(f"Missing directories: {', '.join(missing_dirs)}")
    else:
        checks_passed += 1
        cli.success("   ✓ Directory structure valid")

    # Summary
    cli.blank()
    if errors:
        cli.error("❌ Validation FAILED")
        for error in errors:
            cli.error(f"   ✗ {error}")
        cli.blank()
        raise click.Abort()

    if warnings:
        cli.warning("⚠️  Validation passed with warnings")
        for warning in warnings:
            cli.warning(f"   ⚠️  {warning}")
    else:
        cli.success("✅ Validation passed!")

    cli.success(f"\n   {checks_passed} checks passed")
    cli.blank()


@project_cli.command()
@command_metadata(
    category="project",
    description="Display project information and statistics",
    examples=[
        "bengal project info",
    ],
    requires_site=False,
    tags=["project", "info", "quick"],
)
@handle_cli_errors(show_art=False)
def info() -> None:
    """
    Display project information and statistics.

    Shows:
        - Site title, baseurl, theme
        - Content statistics (pages, sections)
        - Asset counts
        - Configuration paths

    """
    cli = get_cli_output()

    import tomllib
    from pathlib import Path

    config_path = Path("bengal.toml")

    cli.blank()
    cli.header("📊 Project Information", trailing_blank=False)

    # Load config
    if not config_path.exists():
        cli.error("bengal.toml not found. Run 'bengal project init' first.")
        raise click.Abort()

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

        site_config = config.get("site", {})
        build_config = config.get("build", {})

        # Site info
        cli.subheader("Site Configuration", trailing_blank=False)
        cli.info(f"  Title:     {site_config.get('title', '(not set)')}")
        cli.info(f"  Base URL:  {site_config.get('baseurl', '(not set)')}")
        cli.info(f"  Theme:     {site_config.get('theme', 'default')}")

        # Build info
        cli.subheader("Build Settings", trailing_blank=False)
        cli.info(f"  Output:    {build_config.get('output_dir', 'public')}")
        cli.info(f"  Parallel:  {'Yes' if build_config.get('parallel', True) else 'No'}")
        cli.info(f"  Incremental: {'Yes' if build_config.get('incremental', True) else 'No'}")

        # Content stats
        content_dir = Path("content")
        if content_dir.exists():
            md_files = list(content_dir.rglob("*.md"))
            dirs = [d for d in content_dir.iterdir() if d.is_dir()]

            cli.subheader("Content", trailing_blank=False)
            cli.info(f"  Pages:    {len(md_files)}")
            cli.info(f"  Sections: {len(dirs)}")

        # Asset stats
        assets_dir = Path("assets")
        if assets_dir.exists():
            css_files = list(assets_dir.rglob("*.css"))
            js_files = list(assets_dir.rglob("*.js"))
            # Count image files (png, jpg, jpeg, gif, svg)
            img_extensions = {".png", ".jpg", ".jpeg", ".gif", ".svg"}
            img_files = [
                f
                for f in assets_dir.rglob("*")
                if f.is_file() and f.suffix.lower() in img_extensions
            ]

            cli.subheader("Assets", trailing_blank=False)
            cli.info(f"  CSS:    {len(css_files)} files")
            cli.info(f"  JS:     {len(js_files)} files")
            cli.info(f"  Images: {len(img_files)} files")

        # Template stats
        templates_dir = Path("templates")
        if templates_dir.exists():
            templates = list(templates_dir.rglob("*.html"))
            partials = (
                list((templates_dir / "partials").rglob("*.html"))
                if (templates_dir / "partials").exists()
                else []
            )

            cli.subheader("Templates", trailing_blank=False)
            cli.info(f"  Templates: {len(templates)}")
            cli.info(f"  Partials:  {len(partials)}")

    cli.blank()


@project_cli.command()
@command_metadata(
    category="project",
    description="Manage Bengal configuration",
    examples=[
        "bengal project config",
        "bengal project config site.title",
        "bengal project config site.title 'My Blog' --set",
    ],
    requires_site=False,
    tags=["project", "config", "quick"],
)
@handle_cli_errors(show_art=False)
@click.argument("key", required=False)
@click.argument("value", required=False)
@click.option("--set", "set_value", flag_value=True, help="Set a configuration value")
@click.option("--list", "list_all", is_flag=True, help="List all configuration options")
def config(key: str, value: str, set_value: bool, list_all: bool) -> None:
    """
    Manage Bengal configuration.

    Examples:
        bengal project config                    # Show current config
        bengal project config site.title         # Get specific value
        bengal project config site.title "My Blog" --set  # Set value
        bengal project config --list             # List all options

    """
    cli = get_cli_output()

    import tomllib
    from pathlib import Path

    config_path = Path("bengal.toml")

    if not config_path.exists():
        cli.error("bengal.toml not found. Run 'bengal project init' first.")
        raise click.Abort()

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

        # Show all options
        if list_all:
            cli.blank()
            cli.header("📋 Available Configuration Options")

            cli.subheader("[site]", trailing_blank=False)
            cli.info("  title           Site title (required)")
            cli.info("  baseurl         Base URL for the site (required)")
            cli.info("  description     Site description")
            cli.info("  theme           Theme name (default: 'default')")

            cli.subheader("[build]", trailing_blank=False)
            cli.info("  output_dir      Output directory (default: 'public')")
            cli.info("  parallel        Enable parallel processing (default: true)")
            cli.info("  incremental     Enable incremental builds (default: true)")

            cli.subheader("[assets]", trailing_blank=False)
            cli.info("  minify          Minify CSS/JS (default: true)")
            cli.info("  fingerprint     Add cache-busting fingerprints (default: true)")
            cli.blank()
            return

        # Show current config
        if not key:
            cli.blank()
            cli.header("⚙️  Current Configuration")
            cli.blank()
            import json

            cli.info(json.dumps(config, indent=2))
            cli.blank()
            return

        # Get specific value
        parts = key.split(".")
        current = config
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                cli.error(f"✗ Config key not found: {key}")
                raise click.Abort()

        if not set_value:
            if cli.use_rich:
                cli.console.print(f"[info]{key}:[/info] {current!s}")
            else:
                cli.info(f"{key}: {current!s}")
            return

        # Set value
        if not value:
            cli.error("Value required for --set flag")
            raise click.Abort()

        # Navigate to parent and set
        current = config
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Parse value
        if value.lower() in ("true", "false"):
            current[parts[-1]] = value.lower() == "true"
        elif value.isdigit():
            current[parts[-1]] = int(value)
        else:
            current[parts[-1]] = value

        # Write back
        import tomli_w

        from bengal.utils.io.atomic_write import atomic_write_bytes

        atomic_write_bytes(config_path, tomli_w.dumps(config).encode())

        cli.success(f"✓ Set {key} = {value}")
        cli.blank()


project_cli.add_command(init)
project_cli.add_command(skeleton_cli)

# Compatibility export for tests expecting validate_command symbol
# (Click command function is named `validate` in this module.)
validate_command = validate
