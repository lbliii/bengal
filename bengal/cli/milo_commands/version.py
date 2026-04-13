"""Version group — documentation versioning commands."""

from __future__ import annotations

from typing import Annotated

from milo import Description


def version_list(
    source: Annotated[str, Description("Source directory path")] = "",
    output_format: Annotated[str, Description("Output format: table, json, yaml")] = "table",
) -> dict:
    """Display all configured documentation versions."""
    from pathlib import Path

    from bengal.cli.utils import get_cli_output

    source = source or "."
    cli = get_cli_output()
    root_path = Path(source).resolve()
    version_config = _load_version_config(root_path)

    if not version_config or not version_config.enabled:
        cli.warning("Versioning is not enabled in this site.")
        cli.info("Add 'versioning.enabled: true' to your config to enable versioning.")
        return {
            "status": "skipped",
            "message": "Versioning is not enabled",
            "versions": [],
            "count": 0,
        }

    if not version_config.versions:
        cli.warning("No versions configured.")
        cli.info("Add versions to your config or use 'bengal version create' to create one.")
        return {
            "status": "skipped",
            "message": "No versions configured",
            "versions": [],
            "count": 0,
        }

    cli.header("Documentation Versions")
    cli.blank()

    if output_format == "json":
        import json

        data = [_version_to_dict(v) for v in version_config.versions]
        cli.render_write("json_output.kida", data=json.dumps(data, indent=2))
    elif output_format == "yaml":
        import yaml

        data = [_version_to_dict(v) for v in version_config.versions]
        cli.render_write(
            "json_output.kida",
            data=yaml.dump(data, default_flow_style=False, sort_keys=False),
            language="yaml",
        )
    else:
        _display_version_table(cli, version_config)

    cli.blank()

    if version_config.aliases:
        cli.render_write(
            "item_list.kida",
            title="Aliases",
            items=[
                {"name": alias, "description": f"→ {vid}"}
                for alias, vid in version_config.aliases.items()
            ],
        )

    return {
        "versions": [_version_to_dict(v) for v in version_config.versions],
        "count": len(version_config.versions),
    }


def version_info(
    version_id: Annotated[str, Description("Version ID or alias (e.g. v2, latest)")],
    source: Annotated[str, Description("Source directory path")] = "",
) -> dict:
    """Show details about a specific version."""
    from pathlib import Path

    from bengal.cli.utils import get_cli_output

    source = source or "."
    cli = get_cli_output()
    root_path = Path(source).resolve()
    version_config = _load_version_config(root_path)

    if not version_config or not version_config.enabled:
        cli.error("Versioning is not enabled in this site.")
        raise SystemExit(1)

    resolved_id = version_config.aliases.get(version_id, version_id)
    version = next((v for v in version_config.versions if v.id == resolved_id), None)

    if not version:
        cli.error(f"Version '{version_id}' not found.")
        cli.info("Available versions:")
        for v in version_config.versions:
            cli.info(f"  - {v.id}")
        raise SystemExit(1)

    items = [
        {"label": "Label", "value": version.label},
        {"label": "Source", "value": version.source},
        {"label": "Latest", "value": "Yes" if version.latest else "No"},
        {"label": "Deprecated", "value": "Yes" if version.deprecated else "No"},
    ]

    aliases_for = [a for a, vid in version_config.aliases.items() if vid == version.id]
    if aliases_for:
        items.append({"label": "Aliases", "value": ", ".join(aliases_for)})

    if version.banner:
        items.append({"label": "Banner type", "value": version.banner.type})
        if version.banner.message:
            items.append({"label": "Banner message", "value": version.banner.message})

    source_path = root_path / version.source
    if source_path.exists():
        md_files = list(source_path.rglob("*.md"))
        items.append({"label": "Files", "value": f"{len(md_files)} markdown files"})
        badge = {"level": "success", "text": "exists"}
    else:
        badge = {"level": "warning", "text": "missing"}

    cli.render_write("kv_detail.kida", title=f"Version: {version.id}", items=items, badge=badge)

    return _version_to_dict(version)


def version_create(
    version_id: Annotated[str, Description("New version identifier")],
    source: Annotated[str, Description("Source directory path")] = "",
    label: Annotated[str, Description("Human-readable label (default: version ID)")] = "",
    from_path: Annotated[str, Description("Source directory to snapshot (default: docs)")] = "docs",
    to_path: Annotated[str, Description("Destination directory")] = "",
    dry_run: Annotated[bool, Description("Show what would be done without making changes")] = False,
) -> dict:
    """Create a new version snapshot from current docs."""
    import shutil
    from pathlib import Path

    from bengal.cli.utils import get_cli_output

    source = source or "."
    label_val = label or None
    to_path_val = to_path or None

    cli = get_cli_output()
    root_path = Path(source).resolve()

    source_dir = root_path / from_path
    dest_dir = (
        root_path / to_path_val if to_path_val else root_path / "_versions" / version_id / from_path
    )

    if not source_dir.exists():
        cli.error(f"Source directory not found: {source_dir}")
        raise SystemExit(1)

    if dest_dir.exists() and not dry_run:
        cli.error(f"Destination already exists: {dest_dir}")
        cli.info("Choose a different version ID or remove the existing directory.")
        raise SystemExit(1)

    md_files = list(source_dir.rglob("*.md"))
    all_files = list(source_dir.rglob("*"))
    file_count = len([f for f in all_files if f.is_file()])

    cli.render_write(
        "kv_detail.kida",
        title=f"Creating Version: {version_id}",
        items=[
            {"label": "Source", "value": str(source_dir)},
            {"label": "Destination", "value": str(dest_dir)},
            {"label": "Label", "value": label_val or version_id},
            {"label": "Files", "value": f"{file_count} ({len(md_files)} markdown)"},
        ],
        badge={"level": "warning", "text": "DRY RUN"} if dry_run else None,
    )

    if dry_run:
        cli.render_write(
            "item_list.kida",
            title="Would perform",
            items=[
                {"name": f"Create directory: {dest_dir}", "description": ""},
                {"name": f"Copy {file_count} files", "description": ""},
                {"name": "Update bengal.yaml with new version entry", "description": ""},
            ],
        )
        return {
            "version_id": version_id,
            "dest": str(dest_dir),
            "files": file_count,
            "dry_run": True,
        }

    cli.info("Copying files...")
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, dest_dir)
    cli.success(f"Copied {file_count} files")

    cli.info("Updating configuration...")
    _update_config_with_version(root_path, version_id, dest_dir, label_val, cli)

    cli.render_write(
        "scaffold_result.kida",
        title=f"Version '{version_id}' created",
        entries=[{"name": str(dest_dir.relative_to(root_path)), "note": f"{file_count} files"}],
        steps=[
            "Review the copied content",
            "Update any version-specific content",
            "Run: bengal build",
        ],
        summary="Version created successfully!",
    )

    return {
        "version_id": version_id,
        "dest": str(dest_dir),
        "files": file_count,
        "label": label_val or version_id,
    }


def version_diff(
    old_version: Annotated[str, Description("Old version ID or git ref")],
    new_version: Annotated[str, Description("New version ID or git ref")],
    source: Annotated[str, Description("Source directory path")] = "",
    git: Annotated[bool, Description("Compare git refs instead of folder versions")] = False,
    output: Annotated[str, Description("Output format: summary, markdown, json")] = "summary",
) -> dict:
    """Compare documentation between two versions."""
    from pathlib import Path

    from bengal.cli.utils import get_cli_output

    source = source or "."
    cli = get_cli_output()
    root_path = Path(source).resolve()

    cli.header(f"Version Diff: {old_version} -> {new_version}")
    cli.blank()

    if git:
        from bengal.content.discovery.version_diff import diff_git_versions

        cli.info("Comparing git refs...")
        result = diff_git_versions(
            repo_path=root_path,
            old_ref=old_version,
            new_ref=new_version,
            content_dir="docs",
        )
    else:
        version_config = _load_version_config(root_path)

        if not version_config or not version_config.enabled:
            cli.error("Versioning is not enabled in this site.")
            raise SystemExit(1)

        old_v = next((v for v in version_config.versions if v.id == old_version), None)
        new_v = next((v for v in version_config.versions if v.id == new_version), None)

        if not old_v:
            cli.error(f"Version '{old_version}' not found.")
            raise SystemExit(1)
        if not new_v:
            cli.error(f"Version '{new_version}' not found.")
            raise SystemExit(1)

        from bengal.content.discovery.version_diff import VersionDiffer

        old_path = root_path / old_v.source
        new_path = root_path / new_v.source

        if not old_path.exists():
            cli.error(f"Old version path not found: {old_path}")
            raise SystemExit(1)
        if not new_path.exists():
            cli.error(f"New version path not found: {new_path}")
            raise SystemExit(1)

        differ = VersionDiffer(old_path, new_path)
        result = differ.diff(old_version, new_version)

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
        cli.render_write("json_output.kida", data=json.dumps(data, indent=2))
    elif output == "markdown":
        cli.info(result.to_markdown())
    else:
        cli.info(result.summary())
        cli.blank()

        if result.has_changes:
            changes = [
                {"type": "added", "path": p.path, "value": "new"} for p in result.added_pages[:10]
            ]
            changes.extend(
                {"type": "removed", "path": p.path, "value": "deleted"}
                for p in result.removed_pages[:10]
            )
            changes.extend(
                {
                    "type": "changed",
                    "path": p.path,
                    "old": "previous",
                    "new": f"{p.change_percentage:.1f}% changed",
                }
                for p in sorted(
                    result.modified_pages, key=lambda x: x.change_percentage, reverse=True
                )[:10]
            )

            truncated = []
            if len(result.added_pages) > 10:
                truncated.append(f"+{len(result.added_pages) - 10} added")
            if len(result.removed_pages) > 10:
                truncated.append(f"+{len(result.removed_pages) - 10} removed")
            if len(result.modified_pages) > 10:
                truncated.append(f"+{len(result.modified_pages) - 10} modified")
            summary_line = f"{len(result.added_pages)} added, {len(result.removed_pages)} removed, {len(result.modified_pages)} modified"
            if truncated:
                summary_line += f" ({', '.join(truncated)} not shown)"

            cli.render_write(
                "diff_view.kida",
                changes=changes,
                summary=summary_line,
                labels=(old_version, new_version),
            )
        else:
            cli.success("No changes between versions")

    return {
        "old_version": old_version,
        "new_version": new_version,
        "added": len(result.added_pages),
        "removed": len(result.removed_pages),
        "modified": len(result.modified_pages),
        "has_changes": result.has_changes,
    }


# --- Helpers ---


def _load_version_config(root_path):
    from bengal.config import UnifiedConfigLoader
    from bengal.core.version import VersionConfig

    loader = UnifiedConfigLoader()
    config = loader.load(root_path)
    if not config:
        return None
    versioning = config.get("versioning")
    if not versioning:
        return None
    return VersionConfig.from_config(config)


def _version_to_dict(version):
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
        result["banner"] = {"type": version.banner.type, "message": version.banner.message}
    return result


def _display_version_table(cli, version_config):
    cli.render_write(
        "item_list.kida",
        items=[
            {
                "name": v.id,
                "description": f"{v.label}  {v.source}  {', '.join(p for p in [('latest' if v.latest else ''), ('deprecated' if v.deprecated else '')] if p) or '-'}",
            }
            for v in version_config.versions
        ],
    )


def _update_config_with_version(root_path, version_id, dest_dir, label, cli):
    import yaml

    config_file = root_path / "bengal.yaml"
    if not config_file.exists():
        config_file = root_path / "bengal.toml"

    if not config_file.exists():
        cli.warning("No bengal.yaml or bengal.toml found.")
        cli.info("Add the version manually to your config.")
        return

    if config_file.suffix == ".yaml":
        with open(config_file) as f:
            config = yaml.safe_load(f) or {}

        if "versioning" not in config:
            config["versioning"] = {"enabled": True, "versions": []}

        versioning = config["versioning"]
        if "versions" not in versioning:
            versioning["versions"] = []

        new_version = {
            "id": version_id,
            "label": label or version_id,
            "source": str(dest_dir.relative_to(root_path)),
        }
        versioning["versions"].append(new_version)

        with open(config_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        cli.success(f"  Updated {config_file.name}")
    else:
        cli.warning(f"Cannot auto-update {config_file.name}")
        cli.info("Add the version manually to your config.")
