"""
Explain command - show how a page is built.

Provides complete traceability for any page: source file, template chain,
dependencies, cache status, output location, and diagnostics.

Commands:
    bengal explain <page> - Show how a page is built
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import click

from bengal.cli.helpers import (
    configure_traceback,
    get_cli_output,
    handle_cli_errors,
    load_site_from_cli,
)
from bengal.errors.traceback import TracebackStyle
from bengal.utils.profile import BuildProfile

if TYPE_CHECKING:
    from bengal.core.page import Page


@click.command("explain")
@handle_cli_errors(show_art=False)
@click.argument("page_path", type=str)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show additional details (timing, template variables)",
)
@click.option(
    "--diagnose",
    "-d",
    is_flag=True,
    help="Check for issues (broken links, missing assets)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON for programmatic use",
)
@click.option(
    "--traceback",
    type=click.Choice([s.value for s in TracebackStyle]),
    help="Traceback verbosity: full | compact | minimal | off",
)
@click.argument("source", type=click.Path(exists=True), default=".", required=False)
def explain(
    page_path: str,
    verbose: bool,
    diagnose: bool,
    output_json: bool,
    traceback: str | None,
    source: str,
) -> None:
    """
    Explain how a page is built.

    Shows complete traceability for any page including:
    - Source file information
    - Frontmatter metadata
    - Template inheritance chain
    - Dependencies (templates, data, assets)
    - Shortcodes/directives used
    - Cache status (HIT/MISS/STALE)
    - Output location

    Examples:
        bengal explain docs/guide.md
        bengal explain content/posts/hello.md --verbose
        bengal explain api/reference.md --diagnose
        bengal explain docs/guide.md --json

    The page path can be:
        - Relative to content dir: docs/guide.md
        - Full path: content/docs/guide.md
        - Partial match: guide.md (if unique)

    See also:
        bengal validate - Check site health
        bengal site build - Build the site
    """
    cli = get_cli_output()

    # Configure traceback behavior
    configure_traceback(debug=False, traceback=traceback, site=None)

    # Load site
    cli.header("🔍 Page Explanation")
    cli.info("Loading site...")

    # Use WRITER profile for fast loading
    build_profile = BuildProfile.WRITER

    site = load_site_from_cli(
        source=source, config=None, environment=None, profile=build_profile, cli=cli
    )

    # Apply file-based traceback config after site is loaded
    configure_traceback(debug=False, traceback=traceback, site=site)

    # Discover content (required for explanation)
    site.discover_content()

    cli.success(f"Loaded {len(site.pages)} pages")

    # Load cache for cache status
    from bengal.cache import BuildCache

    cache_path = site.paths.build_cache
    cache = (
        BuildCache.load(cache_path)
        if cache_path.exists() or (cache_path.with_suffix(".json.zst")).exists()
        else None
    )

    # Create template engine for template resolution
    template_engine = None
    try:
        from bengal.rendering.engines import create_engine

        template_engine = create_engine(site)
    except Exception as e:
        cli.warning(f"Could not initialize template engine: {e}")

    # Create explainer and generate explanation
    from bengal.debug import PageExplainer

    explainer = PageExplainer(site, cache=cache, template_engine=template_engine)

    try:
        explanation = explainer.explain(
            page_path=page_path,
            verbose=verbose,
            diagnose=diagnose,
        )
    except ValueError as e:
        # Page not found
        cli.error(str(e))

        # Suggest similar pages
        matches = _find_similar_pages(page_path, site.pages)
        if matches:
            cli.blank()
            cli.info("Did you mean:")
            for match in matches[:5]:
                cli.info(f"  • {match}")

        raise click.ClickException(f"Page not found: {page_path}") from e

    # Output
    if output_json:
        # JSON output
        import json
        from dataclasses import asdict

        # Convert to JSON-serializable format
        data = asdict(explanation)
        # Convert Path objects to strings
        data = _convert_paths_to_strings(data)
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        # Rich terminal output
        from bengal.debug import ExplanationReporter

        reporter = ExplanationReporter()
        reporter.print(explanation, verbose=verbose)

        # Summary line
        cli.blank()
        if explanation.issues:
            error_count = sum(1 for i in explanation.issues if i.severity == "error")
            warning_count = sum(1 for i in explanation.issues if i.severity == "warning")
            if error_count:
                cli.error(f"Found {error_count} error(s) and {warning_count} warning(s)")
            elif warning_count:
                cli.warning(f"Found {warning_count} warning(s)")
        else:
            cli.success("Page explanation complete")


def _find_similar_pages(query: str, pages: list[Page]) -> list[str]:
    """Find pages with similar paths."""
    query_lower = query.lower()
    matches = []

    for page in pages:
        path_str = str(page.source_path).lower()

        # Exact filename match
        if query_lower in path_str:
            matches.append(str(page.source_path))
            continue

        # Similar filename
        if (
            page.source_path.stem.lower() in query_lower
            or query_lower in page.source_path.stem.lower()
        ):
            matches.append(str(page.source_path))

    # Sort by relevance (shorter paths first, then alphabetically)
    matches.sort(key=lambda x: (len(x), x))
    return matches


def _convert_paths_to_strings(obj: Any) -> Any:
    """Recursively convert Path objects to strings for JSON serialization."""
    if isinstance(obj, Path):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: _convert_paths_to_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_paths_to_strings(item) for item in obj]
    return obj
