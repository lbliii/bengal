"""Content group — content sources and collections management."""

from __future__ import annotations

from typing import Annotated

from milo import Description

# --- Sources subcommands ---


def content_sources(
    source: Annotated[str, Description("Source directory path")] = "",
) -> dict:
    """List all configured content sources."""
    from pathlib import Path

    from bengal.cli.utils import get_cli_output
    from bengal.collections.loader import load_collections

    source = source or "."
    cli = get_cli_output()
    site_root = Path(source).resolve()
    collections = load_collections(site_root)

    if not collections:
        cli.warning("No collections configured.")
        cli.info("To configure collections, create a collections.py file.")
        cli.info("Run 'bengal content collections-init' to get started.")
        return {
            "status": "skipped",
            "message": "No collections configured",
            "sources": [],
            "count": 0,
        }

    items = []
    for name, config in collections.items():
        source_type = config.source_type
        if config.loader:
            location = config.loader.name
        elif config.directory:
            location = str(config.directory)
        else:
            location = "N/A"
        schema_name = config.schema.__name__
        items.append(
            {"name": name, "description": f"[{source_type}]  {location}  schema={schema_name}"}
        )

    cli.render_write("item_list.kida", title="Content Sources", items=items)

    remote_sources = [(name, config) for name, config in collections.items() if config.is_remote]
    if remote_sources:
        cli.render_write(
            "item_list.kida",
            title="Remote sources require extras",
            items=[
                {"name": "pip install bengal[github]", "description": "GitHub loader"},
                {"name": "pip install bengal[notion]", "description": "Notion loader"},
                {"name": "pip install bengal[rest]", "description": "REST API loader"},
            ],
        )

    return {"sources": list(collections.keys()), "count": len(collections)}


def content_fetch(
    source: Annotated[str, Description("Source directory path")] = "",
    filter_source: Annotated[str, Description("Specific source to fetch (default: all)")] = "",
    force: Annotated[bool, Description("Force refresh (ignore cache)")] = False,
) -> dict:
    """Fetch content from remote sources."""
    from pathlib import Path

    from bengal.cli.utils import get_cli_output
    from bengal.collections.loader import load_collections

    source = source or "."
    filter_val = filter_source or None
    cli = get_cli_output()
    site_root = Path(source).resolve()
    collections = load_collections(site_root)

    if not collections:
        cli.warning("No collections configured.")
        return {
            "status": "skipped",
            "message": "No collections configured",
            "fetched": {},
            "total": 0,
        }

    remote_collections = {
        name: config
        for name, config in collections.items()
        if config.is_remote and (filter_val is None or name == filter_val)
    }

    if not remote_collections:
        if filter_val:
            cli.warning(f"Source '{filter_val}' not found or is not remote.")
        else:
            cli.info("No remote content sources configured.")
        return {
            "status": "skipped",
            "message": "No remote content sources",
            "fetched": {},
            "total": 0,
        }

    from bengal.cache.paths import BengalPaths
    from bengal.content.sources.manager import ContentLayerManager

    paths = BengalPaths(site_root)
    manager = ContentLayerManager(cache_dir=paths.content_dir)

    for name, config in remote_collections.items():
        if config.loader:
            manager.register_custom_source(name, config.loader)

    cli.info(f"Fetching from {len(remote_collections)} source(s)...")

    try:
        entries = manager.fetch_all_sync(use_cache=not force)

        by_source: dict[str, int] = {}
        for entry in entries:
            by_source[entry.source_name] = by_source.get(entry.source_name, 0) + 1

        cli.render_write(
            "kv_detail.kida",
            title="Fetch Complete",
            items=[
                {"label": name, "value": f"{count} entries"} for name, count in by_source.items()
            ],
            badge={"level": "success", "text": "Done"},
        )

        return {"fetched": by_source, "total": sum(by_source.values())}
    except Exception as e:
        cli.error(f"Fetch failed: {e}")
        raise SystemExit(1) from None


def content_collections(
    source: Annotated[str, Description("Source directory path")] = "",
    config: Annotated[str, Description("Path to config file")] = "",
) -> dict:
    """List defined content collections and their schemas."""
    from dataclasses import MISSING, fields, is_dataclass
    from pathlib import Path
    from typing import Any

    from bengal.cli.utils import get_cli_output
    from bengal.collections import CollectionConfig, load_collections

    source = source or "."
    cli = get_cli_output()
    root_path = Path(source).resolve()

    cli.blank()
    cli.header("Content Collections")
    cli.blank()

    loaded: dict[str, CollectionConfig[Any]] = load_collections(root_path)

    if not loaded:
        cli.warning("No collections defined")
        cli.info("Run 'bengal content collections-init' to create collections.py")
        return {
            "status": "skipped",
            "message": "No collections defined",
            "collections": [],
            "count": 0,
        }

    for name, coll_config in loaded.items():
        items = [
            {"label": "Directory", "value": f"content/{coll_config.directory}"},
            {"label": "Schema", "value": coll_config.schema.__name__},
            {"label": "Strict", "value": str(coll_config.strict)},
        ]

        if is_dataclass(coll_config.schema):
            field_strs = []
            for f in fields(coll_config.schema):
                required = f.default is MISSING and f.default_factory is MISSING
                marker = "*" if required else " "
                field_strs.append(f"{marker} {f.name}: {f.type}")
            items.append({"label": "Fields", "value": ", ".join(field_strs)})

        cli.render_write("kv_detail.kida", title=name, items=items)

    cli.info(f"Total: {len(loaded)} collection(s)")
    return {"collections": list(loaded.keys()), "count": len(loaded)}


def content_schemas(
    source: Annotated[str, Description("Source directory path")] = "",
    collection: Annotated[str, Description("Validate specific collection only")] = "",
    config: Annotated[str, Description("Path to config file")] = "",
) -> dict:
    """Validate content against collection schemas."""
    from pathlib import Path

    import frontmatter

    from bengal.cli.utils import get_cli_output
    from bengal.collections import SchemaValidator, load_collections

    source = source or "."
    collection_val = collection or None
    cli = get_cli_output()
    root_path = Path(source).resolve()
    content_dir = root_path / "content"

    cli.blank()
    cli.header("Validating collections...")
    cli.blank()

    loaded = load_collections(root_path)

    if not loaded:
        cli.warning("No collections defined")
        cli.info("Run 'bengal content collections-init' to create collections.py")
        return {"status": "skipped", "message": "No collections defined", "files": 0, "errors": 0}

    if collection_val:
        if collection_val not in loaded:
            cli.error(f"Collection '{collection_val}' not found")
            cli.info(f"Available: {', '.join(loaded.keys())}")
            return {
                "status": "error",
                "message": f"Collection '{collection_val}' not found",
                "files": 0,
                "errors": 0,
            }
        loaded = {collection_val: loaded[collection_val]}

    total_files = 0
    total_errors = 0
    errors_by_file: dict[str, list[str]] = {}

    for name, coll_config in loaded.items():
        if coll_config.directory is None:
            cli.warning(f"Collection '{name}' has no directory configured - skipping")
            continue
        collection_dir = content_dir / coll_config.directory

        if not collection_dir.exists():
            cli.warning(f"Collection '{name}' directory not found: {collection_dir}")
            continue

        cli.info(f"  {name}")

        files = list(collection_dir.glob(coll_config.glob))
        validator = SchemaValidator(coll_config.schema, strict=coll_config.strict)

        for file_path in files:
            total_files += 1
            try:
                with open(file_path) as f:
                    post = frontmatter.load(f)

                metadata = dict(post.metadata)
                result = validator.validate(metadata, source_file=file_path)

                if not result.valid:
                    total_errors += 1
                    rel_path = file_path.relative_to(root_path)
                    errors_by_file[str(rel_path)] = [
                        f"{e.field}: {e.message}" for e in result.errors
                    ]
                    cli.info(f"    x {rel_path}")
                else:
                    rel_path = file_path.relative_to(root_path)
                    cli.info(f"    v {rel_path}")
            except Exception as e:
                total_errors += 1
                rel_path = file_path.relative_to(root_path)
                errors_by_file[str(rel_path)] = [str(e)]
                cli.info(f"    x {rel_path}: {e}")

        cli.blank()

    if total_errors == 0:
        cli.render_write(
            "validation_report.kida",
            issues=[{"level": "success", "message": f"All {total_files} files valid!"}],
            summary={"errors": 0, "warnings": 0, "passed": 1},
        )
    else:
        issues = [
            {"level": "error", "message": err_file_path, "detail": error}
            for err_file_path, errors in errors_by_file.items()
            for error in errors
        ]
        cli.render_write(
            "validation_report.kida",
            title="Schema Validation",
            issues=issues,
            summary={"errors": total_errors, "warnings": 0, "passed": 0},
        )

    return {"files": total_files, "errors": total_errors, "passed": total_errors == 0}
