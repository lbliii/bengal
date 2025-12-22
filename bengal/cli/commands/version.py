"""
Version management commands.

Provides commands for managing versioned documentation:
- list: Display all configured versions
- create: Create a new version snapshot
- info: Show details about a specific version
"""

from __future__ import annotations

import shutil
from pathlib import Path

import click

from bengal.cli.base import BengalGroup
from bengal.cli.helpers import command_metadata, get_cli_output, handle_cli_errors
from bengal.config.loader import ConfigLoader
from bengal.core.version import Version, VersionConfig


@click.group("version", cls=BengalGroup)
def version_cli() -> None:
    """
    Version management for documentation.

    Commands:
        list     Display all configured versions
        create   Create a new version snapshot
        info     Show details about a specific version
    """
    pass


@version_cli.command("list")
@command_metadata(
    category="version",
    description="Display all configured documentation versions",
    examples=[
        "bengal version list",
        "bengal version list --format json",
    ],
    requires_site=False,
    tags=["version", "docs", "quick"],
)
@handle_cli_errors(show_art=False)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format (default: table)",
)
@click.argument("source", type=click.Path(exists=True), default=".")
def list_versions(output_format: str, source: str) -> None:
    """
    📋 Display all configured versions.

    Shows version ID, label, source directory, and status (latest, deprecated).

    Examples:
        bengal version list
        bengal version list --format json

    See also:
        bengal version info - Show details about a specific version
        bengal version create - Create a new version snapshot
    """
    cli = get_cli_output()

    root_path = Path(source).resolve()
    version_config = _load_version_config(root_path)

    if not version_config or not version_config.enabled:
        cli.warning("Versioning is not enabled in this site.")
        cli.info("Add 'versioning.enabled: true' to your config to enable versioning.")
        return

    if not version_config.versions:
        cli.warning("No versions configured.")
        cli.info("Add versions to your config or use 'bengal version create' to create one.")
        return

    cli.header("📚 Documentation Versions")
    cli.blank()

    if output_format == "json":
        import json

        data = [_version_to_dict(v) for v in version_config.versions]
        cli.console.print(json.dumps(data, indent=2))
    elif output_format == "yaml":
        import yaml

        data = [_version_to_dict(v) for v in version_config.versions]
        cli.console.print(yaml.dump(data, default_flow_style=False, sort_keys=False))
    else:
        _display_version_table(cli, version_config)

    cli.blank()

    # Show aliases
    if version_config.aliases:
        cli.info("📎 Aliases:")
        for alias, version_id in version_config.aliases.items():
            cli.info(f"  {alias} → {version_id}")
        cli.blank()


@version_cli.command("info")
@command_metadata(
    category="version",
    description="Show details about a specific version",
    examples=[
        "bengal version info v2",
        "bengal version info latest",
    ],
    requires_site=False,
    tags=["version", "docs"],
)
@handle_cli_errors(show_art=False)
@click.argument("version_id", required=True)
@click.argument("source", type=click.Path(exists=True), default=".")
def info(version_id: str, source: str) -> None:
    """
    Show details about a specific version.

    Accepts version ID or alias (e.g., 'v2', 'latest', 'stable').

    Examples:
        bengal version info v2
        bengal version info latest

    See also:
        bengal version list - List all versions
    """
    cli = get_cli_output()

    root_path = Path(source).resolve()
    version_config = _load_version_config(root_path)

    if not version_config or not version_config.enabled:
        cli.error("Versioning is not enabled in this site.")
        raise click.Abort()

    # Resolve alias to version ID
    resolved_id = version_config.aliases.get(version_id, version_id)
    version = next((v for v in version_config.versions if v.id == resolved_id), None)

    if not version:
        cli.error(f"Version '{version_id}' not found.")
        cli.info("Available versions:")
        for v in version_config.versions:
            cli.info(f"  - {v.id}")
        raise click.Abort()

    cli.header(f"📚 Version: {version.id}")
    cli.blank()

    # Basic info
    cli.info(f"  Label:      {version.label}")
    cli.info(f"  Source:     {version.source}")
    cli.info(f"  Latest:     {'Yes' if version.latest else 'No'}")
    cli.info(f"  Deprecated: {'Yes' if version.deprecated else 'No'}")

    # Aliases pointing to this version
    aliases_for = [a for a, vid in version_config.aliases.items() if vid == version.id]
    if aliases_for:
        cli.info(f"  Aliases:    {', '.join(aliases_for)}")

    # Banner info
    if version.banner:
        cli.blank()
        cli.info("  Banner:")
        cli.info(f"    Type:     {version.banner.type}")
        if version.banner.message:
            cli.info(f"    Message:  {version.banner.message}")

    # Check source directory exists
    cli.blank()
    source_path = root_path / version.source
    if source_path.exists():
        # Count files
        md_files = list(source_path.rglob("*.md"))
        cli.success(f"  ✅ Source directory exists ({len(md_files)} markdown files)")
    else:
        cli.warning(f"  ⚠️  Source directory not found: {source_path}")


@version_cli.command("create")
@command_metadata(
    category="version",
    description="Create a new version snapshot from current docs",
    examples=[
        "bengal version create v2",
        "bengal version create v2 --label '2.0'",
        "bengal version create v2 --from docs --to _versions/v2/docs",
    ],
    requires_site=False,
    tags=["version", "docs", "create"],
)
@handle_cli_errors(show_art=False)
@click.argument("version_id", required=True)
@click.option(
    "--label",
    "-l",
    help="Human-readable label for the version (default: version ID)",
)
@click.option(
    "--from",
    "from_path",
    default="docs",
    help="Source directory to snapshot (default: docs)",
)
@click.option(
    "--to",
    "to_path",
    help="Destination directory (default: _versions/<version_id>/docs)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without making changes",
)
@click.argument("source", type=click.Path(exists=True), default=".")
def create(
    version_id: str,
    label: str | None,
    from_path: str,
    to_path: str | None,
    dry_run: bool,
    source: str,
) -> None:
    """
    Create a new version snapshot.

    Copies the current documentation to a versioned directory and updates
    configuration to include the new version.

    Examples:
        bengal version create v2
        bengal version create v2 --label '2.0 (Stable)'
        bengal version create v1 --from docs --to _versions/v1/docs

    Workflow:
        1. Copy docs/ → _versions/v2/docs/
        2. Update config with new version entry
        3. Current docs/ becomes the new "latest" version

    See also:
        bengal version list - List all versions
    """
    cli = get_cli_output()

    root_path = Path(source).resolve()

    # Determine paths
    source_dir = root_path / from_path
    dest_dir = root_path / to_path if to_path else root_path / "_versions" / version_id / from_path

    # Validate source exists
    if not source_dir.exists():
        cli.error(f"Source directory not found: {source_dir}")
        raise click.Abort()

    # Check if destination already exists
    if dest_dir.exists() and not dry_run:
        cli.error(f"Destination already exists: {dest_dir}")
        cli.info("Choose a different version ID or remove the existing directory.")
        raise click.Abort()

    # Calculate stats
    md_files = list(source_dir.rglob("*.md"))
    all_files = list(source_dir.rglob("*"))
    file_count = len([f for f in all_files if f.is_file()])

    cli.header(f"✨ Creating Version: {version_id}")
    cli.blank()

    cli.info(f"  Source:      {source_dir}")
    cli.info(f"  Destination: {dest_dir}")
    cli.info(f"  Label:       {label or version_id}")
    cli.info(f"  Files:       {file_count} ({len(md_files)} markdown)")
    cli.blank()

    if dry_run:
        cli.info("🔍 Dry run - no changes will be made")
        cli.blank()

        cli.info("Would perform:")
        cli.info(f"  1. Create directory: {dest_dir}")
        cli.info(f"  2. Copy {file_count} files")
        cli.info("  3. Update bengal.yaml with new version entry")
        return

    # Perform the copy
    cli.info("📁 Copying files...")
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, dest_dir)
    cli.success(f"  ✅ Copied {file_count} files")

    # Update config
    cli.info("📝 Updating configuration...")
    _update_config_with_version(root_path, version_id, dest_dir, label, cli)

    cli.blank()
    cli.success(f"✨ Version '{version_id}' created successfully!")
    cli.blank()

    cli.info("💡 Next steps:")
    cli.info("  1. Review the copied content")
    cli.info("  2. Update any version-specific content")
    cli.info("  3. Run: bengal build")


def _load_version_config(root_path: Path) -> VersionConfig | None:
    """Load version configuration from site config."""
    loader = ConfigLoader(root_path)
    config = loader.load()

    if not config:
        return None

    versioning = config.get("versioning")
    if not versioning:
        return None

    return VersionConfig.from_config(config)


def _version_to_dict(version: Version) -> dict:
    """Convert Version to dictionary for JSON/YAML output."""
    result = {
        "id": version.id,
        "label": version.label,
        "source": version.source,
        "latest": version.latest,
    }
    if version.deprecated:
        result["deprecated"] = True
    aliases = getattr(version, "aliases", None)
    if aliases:
        result["aliases"] = aliases
    if version.banner:
        result["banner"] = {
            "type": version.banner.type,
            "message": version.banner.message,
        }
    return result


def _display_version_table(cli, version_config: VersionConfig) -> None:
    """Display versions in a table format."""
    from rich.table import Table

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="cyan")
    table.add_column("Label")
    table.add_column("Source", style="dim")
    table.add_column("Status")

    for version in version_config.versions:
        status_parts = []
        if version.latest:
            status_parts.append("✅ latest")
        if version.deprecated:
            status_parts.append("⚠️ deprecated")
        status = ", ".join(status_parts) if status_parts else "-"

        table.add_row(version.id, version.label, version.source, status)

    cli.console.print(table)


@version_cli.command("diff")
@command_metadata(
    category="version",
    description="Compare documentation between two versions",
    examples=[
        "bengal version diff v2 v3",
        "bengal version diff main release/0.1.6 --git",
    ],
    requires_site=False,
    tags=["version", "docs", "diff"],
)
@handle_cli_errors(show_art=False)
@click.argument("old_version", required=True)
@click.argument("new_version", required=True)
@click.option(
    "--git",
    is_flag=True,
    help="Compare git refs instead of folder versions",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["summary", "markdown", "json"]),
    default="summary",
    help="Output format (default: summary)",
)
@click.argument("source", type=click.Path(exists=True), default=".")
def diff_versions(
    old_version: str,
    new_version: str,
    git: bool,
    output: str,
    source: str,
) -> None:
    """
    Compare documentation between two versions.

    Shows added, removed, and modified pages between versions.

    Examples:
        bengal version diff v2 v3
        bengal version diff main release/0.1.6 --git
        bengal version diff v1 v2 --output markdown

    Output formats:
        summary  - Brief summary of changes (default)
        markdown - Markdown changelog suitable for release notes
        json     - JSON output for automation

    See also:
        bengal version list - List all versions
    """
    cli = get_cli_output()

    root_path = Path(source).resolve()

    cli.header(f"📊 Version Diff: {old_version} → {new_version}")
    cli.blank()

    if git:
        # Git mode - compare refs directly
        from bengal.utils.version_diff import diff_git_versions

        cli.info("Comparing git refs...")
        result = diff_git_versions(
            repo_path=root_path,
            old_ref=old_version,
            new_ref=new_version,
            content_dir="docs",
        )
    else:
        # Folder mode - compare directories
        version_config = _load_version_config(root_path)

        if not version_config or not version_config.enabled:
            cli.error("Versioning is not enabled in this site.")
            raise click.Abort()

        # Find versions
        old_v = next((v for v in version_config.versions if v.id == old_version), None)
        new_v = next((v for v in version_config.versions if v.id == new_version), None)

        if not old_v:
            cli.error(f"Version '{old_version}' not found.")
            raise click.Abort()
        if not new_v:
            cli.error(f"Version '{new_version}' not found.")
            raise click.Abort()

        # Compare directories
        from bengal.utils.version_diff import VersionDiffer

        old_path = root_path / old_v.source
        new_path = root_path / new_v.source

        if not old_path.exists():
            cli.error(f"Old version path not found: {old_path}")
            raise click.Abort()
        if not new_path.exists():
            cli.error(f"New version path not found: {new_path}")
            raise click.Abort()

        differ = VersionDiffer(old_path, new_path)
        result = differ.diff(old_version, new_version)

    # Output results
    if output == "json":
        import json

        data = {
            "old_version": result.old_version,
            "new_version": result.new_version,
            "added": [p.path for p in result.added_pages],
            "removed": [p.path for p in result.removed_pages],
            "modified": [
                {"path": p.path, "change_pct": p.change_percentage} for p in result.modified_pages
            ],
            "unchanged_count": len(result.unchanged_pages),
        }
        cli.console.print(json.dumps(data, indent=2))
    elif output == "markdown":
        cli.console.print(result.to_markdown())
    else:
        # Summary output
        cli.info(result.summary())
        cli.blank()

        if result.added_pages:
            cli.success("✨ Added pages:")
            for p in result.added_pages[:10]:
                cli.info(f"  + {p.path}")
            if len(result.added_pages) > 10:
                cli.info(f"  ... and {len(result.added_pages) - 10} more")
            cli.blank()

        if result.removed_pages:
            cli.warning("🗑️ Removed pages:")
            for p in result.removed_pages[:10]:
                cli.info(f"  - {p.path}")
            if len(result.removed_pages) > 10:
                cli.info(f"  ... and {len(result.removed_pages) - 10} more")
            cli.blank()

        if result.modified_pages:
            cli.info("📝 Modified pages:")
            for p in sorted(result.modified_pages, key=lambda x: x.change_percentage, reverse=True)[
                :10
            ]:
                cli.info(f"  ~ {p.path} ({p.change_percentage:.1f}% changed)")
            if len(result.modified_pages) > 10:
                cli.info(f"  ... and {len(result.modified_pages) - 10} more")
            cli.blank()

        if not result.has_changes:
            cli.success("✅ No changes between versions")


def _update_config_with_version(
    root_path: Path,
    version_id: str,
    dest_dir: Path,
    label: str | None,
    cli,
) -> None:
    """Update bengal.yaml with the new version entry."""
    import yaml

    config_file = root_path / "bengal.yaml"
    if not config_file.exists():
        config_file = root_path / "bengal.toml"

    if not config_file.exists():
        cli.warning("No bengal.yaml or bengal.toml found.")
        cli.info("Add the version manually to your config:")
        cli.blank()
        cli.console.print(f"""
versioning:
  enabled: true
  versions:
    - id: {version_id}
      label: "{label or version_id}"
      source: {dest_dir.relative_to(root_path)}
""")
        return

    if config_file.suffix == ".yaml":
        # Load existing config
        with open(config_file) as f:
            config = yaml.safe_load(f) or {}

        # Ensure versioning section exists
        if "versioning" not in config:
            config["versioning"] = {"enabled": True, "versions": []}

        versioning = config["versioning"]
        if "versions" not in versioning:
            versioning["versions"] = []

        # Add new version
        new_version = {
            "id": version_id,
            "label": label or version_id,
            "source": str(dest_dir.relative_to(root_path)),
        }
        versioning["versions"].append(new_version)

        # Write updated config
        with open(config_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        cli.success(f"  ✅ Updated {config_file.name}")
    else:
        cli.warning(f"Cannot auto-update {config_file.name}")
        cli.info("Add the version manually to your config.")
