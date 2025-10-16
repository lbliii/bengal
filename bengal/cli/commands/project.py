from pathlib import Path

import click

from bengal.cli.commands.init import init
from bengal.utils.build_stats import show_error

# User profiles with customization
PROFILES = {
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


@click.group("project")
def project_cli():
    """
    📦 Project management and setup commands.

    Commands:
        init       Initialize project structure and content sections
        profile    Set your working profile (dev, themer, writer, ai)
        validate   Validate configuration and directory structure
        info       Display project information and statistics
        config     View and manage configuration settings
    """
    pass


@project_cli.command()
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
    try:
        profile_path = Path(".bengal-profile")

        # List available profiles
        if profile_name is None:
            current_profile = None
            if profile_path.exists():
                current_profile = profile_path.read_text().strip()

            click.echo(click.style("\n👤 Available Profiles\n", fg="cyan", bold=True))

            for profile_key, profile_info in PROFILES.items():
                marker = "✓ " if profile_key == current_profile else "  "
                click.echo(
                    click.style(
                        f"{marker}{profile_info['emoji']} ",
                        fg="cyan" if profile_key == current_profile else "white",
                    )
                    + click.style(profile_info["name"], bold=profile_key == current_profile)
                    + click.style(f" - {profile_info['description']}", fg="bright_black")
                )

            if current_profile:
                click.echo(
                    click.style(f"\n📍 Current: {PROFILES[current_profile]['name']}", fg="green")
                )
            else:
                click.echo(click.style("\n📍 Current: (not set)", fg="yellow"))

            click.echo(
                click.style("\nUsage: bengal project profile <dev|themer|writer|ai>\n", fg="cyan")
            )
            return

        # Validate profile
        if profile_name not in PROFILES:
            click.echo(click.style(f"✗ Unknown profile: {profile_name}", fg="red"))
            click.echo(click.style(f"Available: {', '.join(PROFILES.keys())}", fg="yellow"))
            raise click.Abort()

        # Save profile
        from bengal.utils.atomic_write import atomic_write_text

        atomic_write_text(profile_path, profile_name)

        profile_info = PROFILES[profile_name]
        click.echo()
        click.echo(
            click.style("✓ Profile set to: ", fg="green")
            + click.style(f"{profile_info['emoji']} {profile_info['name']}", fg="green", bold=True)
        )
        click.echo(click.style(f"  {profile_info['description']}", fg="bright_black"))
        click.echo()

        # Show what changed
        click.echo(click.style("💡 This affects:", fg="cyan", bold=True))
        click.echo(f"  • Output format:    {profile_info['output_format'].upper()}")
        click.echo(f"  • Verbosity level:  {profile_info['verbosity'].upper()}")
        click.echo(f"  • Build profile:    {profile_info['default_build_profile']}")
        if not profile_info["show_all_commands"]:
            click.echo("  • Commands shown:   Simplified (use --all for full)")
        click.echo()

    except click.Abort:
        raise
    except Exception as e:
        show_error(f"Profile error: {e}", show_art=False)
        raise click.Abort() from e


@project_cli.command()
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
    try:
        import tomllib
        from pathlib import Path

        config_path = Path("bengal.toml")

        click.echo(click.style("\n🔍 Validating Bengal project...\n", fg="cyan", bold=True))

        errors = []
        warnings = []
        checks_passed = 0

        # Check 1: Config file exists
        if not config_path.exists():
            errors.append("bengal.toml not found in current directory")
        else:
            checks_passed += 1
            click.echo(click.style("   ✓ ", fg="green") + "bengal.toml found")

            # Check 2: Config is valid TOML
            try:
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)
                checks_passed += 1
                click.echo(click.style("   ✓ ", fg="green") + "bengal.toml is valid")
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
                click.echo(click.style("   ✓ ", fg="green") + "Required fields present")

            # Check 4: Theme configured
            theme = site_config.get("theme", "default")
            checks_passed += 1
            click.echo(click.style("   ✓ ", fg="green") + f"Theme configured: {theme}")

        # Check 5: Directory structure
        required_dirs = ["content", "templates", "assets"]
        missing_dirs = [d for d in required_dirs if not Path(d).exists()]

        if missing_dirs:
            warnings.append(f"Missing directories: {', '.join(missing_dirs)}")
        else:
            checks_passed += 1
            click.echo(click.style("   ✓ ", fg="green") + "Directory structure valid")

        # Summary
        click.echo()
        if errors:
            click.echo(click.style("❌ Validation FAILED", fg="red", bold=True))
            for error in errors:
                click.echo(click.style("   ✗ ", fg="red") + error)
            click.echo()
            raise click.Abort()

        if warnings:
            click.echo(click.style("⚠️  Validation passed with warnings", fg="yellow", bold=True))
            for warning in warnings:
                click.echo(click.style("   ⚠️  ", fg="yellow") + warning)
        else:
            click.echo(click.style("✅ Validation passed!", fg="green", bold=True))

        click.echo(click.style(f"\n   {checks_passed} checks passed\n", fg="green"))

    except Exception as e:
        if isinstance(e, click.Abort):
            raise
        show_error(f"Validation error: {e}", show_art=False)
        raise click.Abort() from e


@project_cli.command()
def info() -> None:
    """
    ℹ️  Display project information and statistics.

    Shows:
        - Site title, baseurl, theme
        - Content statistics (pages, sections)
        - Asset counts
        - Configuration paths
    """
    try:
        import tomllib
        from pathlib import Path

        config_path = Path("bengal.toml")

        click.echo(click.style("\n📊 Project Information\n", fg="cyan", bold=True))

        # Load config
        if not config_path.exists():
            show_error("bengal.toml not found. Run 'bengal project init' first.", show_art=False)
            raise click.Abort()

        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        site_config = config.get("site", {})
        build_config = config.get("build", {})

        # Site info
        click.echo(click.style("Site Configuration:", fg="cyan", bold=True))
        click.echo(f"  Title:     {site_config.get('title', '(not set)')}")
        click.echo(f"  Base URL:  {site_config.get('baseurl', '(not set)')}")
        click.echo(f"  Theme:     {site_config.get('theme', 'default')}")
        click.echo()

        # Build info
        click.echo(click.style("Build Settings:", fg="cyan", bold=True))
        click.echo(f"  Output:    {build_config.get('output_dir', 'public')}")
        click.echo(f"  Parallel:  {'Yes' if build_config.get('parallel', True) else 'No'}")
        click.echo(f"  Incremental: {'Yes' if build_config.get('incremental', True) else 'No'}")
        click.echo()

        # Content stats
        content_dir = Path("content")
        if content_dir.exists():
            md_files = list(content_dir.rglob("*.md"))
            dirs = [d for d in content_dir.iterdir() if d.is_dir()]

            click.echo(click.style("Content:", fg="cyan", bold=True))
            click.echo(f"  Pages:    {len(md_files)}")
            click.echo(f"  Sections: {len(dirs)}")
            click.echo()

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

            click.echo(click.style("Assets:", fg="cyan", bold=True))
            click.echo(f"  CSS:    {len(css_files)} files")
            click.echo(f"  JS:     {len(js_files)} files")
            click.echo(f"  Images: {len(img_files)} files")
            click.echo()

        # Template stats
        templates_dir = Path("templates")
        if templates_dir.exists():
            templates = list(templates_dir.rglob("*.html"))
            partials = (
                list((templates_dir / "partials").rglob("*.html"))
                if (templates_dir / "partials").exists()
                else []
            )

            click.echo(click.style("Templates:", fg="cyan", bold=True))
            click.echo(f"  Templates: {len(templates)}")
            click.echo(f"  Partials:  {len(partials)}")
            click.echo()

    except click.Abort:
        raise
    except Exception as e:
        show_error(f"Error reading project info: {e}", show_art=False)
        raise click.Abort() from e


@project_cli.command()
@click.argument("key", required=False)
@click.argument("value", required=False)
@click.option("--set", "set_value", flag_value=True, help="Set a configuration value")
@click.option("--list", "list_all", is_flag=True, help="List all configuration options")
def config(key: str, value: str, set_value: bool, list_all: bool) -> None:
    """
    ⚙️  Manage Bengal configuration.

    Examples:
        bengal project config                    # Show current config
        bengal project config site.title         # Get specific value
        bengal project config site.title "My Blog" --set  # Set value
        bengal project config --list             # List all options
    """
    try:
        import tomllib
        from pathlib import Path

        config_path = Path("bengal.toml")

        if not config_path.exists():
            show_error("bengal.toml not found. Run 'bengal project init' first.", show_art=False)
            raise click.Abort()

        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        # Show all options
        if list_all:
            click.echo(click.style("\n📋 Available Configuration Options\n", fg="cyan", bold=True))

            click.echo(click.style("[site]", fg="cyan", bold=True))
            click.echo("  title           Site title (required)")
            click.echo("  baseurl         Base URL for the site (required)")
            click.echo("  description     Site description")
            click.echo("  theme           Theme name (default: 'default')")
            click.echo()

            click.echo(click.style("[build]", fg="cyan", bold=True))
            click.echo("  output_dir      Output directory (default: 'public')")
            click.echo("  parallel        Enable parallel processing (default: true)")
            click.echo("  incremental     Enable incremental builds (default: true)")
            click.echo()

            click.echo(click.style("[assets]", fg="cyan", bold=True))
            click.echo("  minify          Minify CSS/JS (default: true)")
            click.echo("  fingerprint     Add cache-busting fingerprints (default: true)")
            click.echo()
            return

        # Show current config
        if not key:
            click.echo(click.style("\n⚙️  Current Configuration\n", fg="cyan", bold=True))
            import json

            click.echo(json.dumps(config, indent=2))
            click.echo()
            return

        # Get specific value
        parts = key.split(".")
        current = config
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                click.echo(click.style(f"✗ Config key not found: {key}", fg="red"))
                raise click.Abort()

        if not set_value:
            click.echo(click.style(f"{key}: ", fg="cyan") + str(current))
            return

        # Set value
        if not value:
            show_error("Value required for --set flag", show_art=False)
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
        from bengal.utils.atomic_write import atomic_write_text

        # Format TOML (simple, not perfect)
        toml_lines = []
        for section, section_config in config.items():
            toml_lines.append(f"[{section}]")
            for k, v in section_config.items():
                if isinstance(v, bool):
                    toml_lines.append(f'{k} = {"true" if v else "false"}')
                elif isinstance(v, int | float):
                    toml_lines.append(f"{k} = {v}")
                else:
                    toml_lines.append(f'{k} = "{v}"')
            toml_lines.append("")

        atomic_write_text(config_path, "\n".join(toml_lines))

        click.echo(click.style(f"✓ Set {key} = {value}", fg="green"))
        click.echo()

    except click.Abort:
        raise
    except Exception as e:
        show_error(f"Config error: {e}", show_art=False)
        raise click.Abort() from e


project_cli.add_command(init)
