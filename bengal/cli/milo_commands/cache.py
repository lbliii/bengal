"""Cache group — CI cache management."""

from __future__ import annotations

import hashlib
import json
from typing import Annotated

from milo import Description


def cache_inputs(
    source: Annotated[str, Description("Source directory path")] = "",
    output_format: Annotated[str, Description("Output format: plain or json")] = "plain",
    verbose: Annotated[bool, Description("Show source of each input pattern")] = False,
    config: Annotated[str, Description("Path to config file")] = "",
) -> dict:
    """List build input patterns for CI cache keys."""
    from bengal.cache.ci import get_input_globs
    from bengal.cli.utils import get_cli_output, load_site_from_cli

    source = source or "."
    config_val = config or None
    cli = get_cli_output()

    site = load_site_from_cli(
        source=source, config=config_val, environment=None, profile=None, cli=cli
    )
    input_globs = get_input_globs(site)

    if output_format == "json":
        if verbose:
            data = [{"pattern": p, "source": s} for p, s in input_globs]
        else:
            data = [p for p, _ in input_globs]
        cli.render_write("json_output.kida", data=json.dumps(data, indent=2))
    else:
        if verbose:
            items = [{"name": p, "description": s} for p, s in input_globs]
            cli.render_write("item_list.kida", title="Cache Input Patterns", items=items)
        else:
            for pattern, _source_desc in input_globs:
                cli.info(pattern)

    return {"patterns": [p for p, _ in input_globs], "count": len(input_globs)}


def cache_hash(
    source: Annotated[str, Description("Source directory path")] = "",
    include_version: Annotated[
        bool, Description("Include Bengal version in hash (recommended)")
    ] = True,
    config: Annotated[str, Description("Path to config file")] = "",
) -> dict:
    """Compute deterministic hash of build inputs for CI cache keys."""
    from pathlib import Path

    import bengal
    from bengal.cache.ci import get_input_globs
    from bengal.cli.utils import get_cli_output, load_site_from_cli

    source = source or "."
    config_val = config or None
    cli = get_cli_output()

    site = load_site_from_cli(
        source=source, config=config_val, environment=None, profile=None, cli=cli
    )
    input_globs = get_input_globs(site)

    hasher = hashlib.sha256()

    if include_version:
        hasher.update(f"bengal:{bengal.__version__}".encode())

    for glob_pattern, _source in input_globs:
        if glob_pattern.count("../") > 1:
            cli.warning(f"Skipping unsupported pattern '{glob_pattern}' (nested ../ not supported)")
            continue

        if glob_pattern.startswith("../"):
            base_path = site.root_path.parent
            resolved_pattern = glob_pattern[3:]
        else:
            base_path = site.root_path
            resolved_pattern = glob_pattern

        try:
            matched_files = sorted(base_path.glob(resolved_pattern))
        except Exception as e:
            cli.warning(f"Error matching pattern '{glob_pattern}': {e}")
            continue

        for file_path in matched_files:
            if not file_path.is_file():
                continue

            try:
                file_path = file_path.resolve()
            except OSError:
                continue

            try:
                rel_path = file_path.relative_to(site.root_path.resolve())
            except ValueError:
                try:
                    rel_path = file_path.relative_to(site.root_path.parent.resolve())
                except ValueError:
                    rel_path = Path(file_path.name)

            try:
                hasher.update(rel_path.as_posix().encode())
                hasher.update(file_path.read_bytes())
            except OSError as e:
                cli.error(f"Cannot read file '{file_path}': {e}")
                raise SystemExit(1) from e

    result = hasher.hexdigest()[:16]
    cli.info(result)

    return {"hash": result, "include_version": include_version}
