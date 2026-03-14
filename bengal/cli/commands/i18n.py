"""
Internationalization (i18n) commands.

Provides gettext PO/MO workflow:
- compile: Compile .po files to .mo
- extract: Scan templates for t() calls and generate .pot
"""

from __future__ import annotations

import re
from pathlib import Path

import click

from bengal.cli.base import BengalGroup
from bengal.cli.helpers import command_metadata, get_cli_output, handle_cli_errors
from bengal.config import UnifiedConfigLoader
from bengal.i18n.catalog import clear_catalog_cache


@click.group("i18n", cls=BengalGroup)
def i18n_cli() -> None:
    """
    Internationalization (gettext PO/MO workflow).

    Commands:
        compile   Compile .po files to .mo
        extract   Scan templates for t() calls and generate .pot

    """


@i18n_cli.command("compile")
@command_metadata(
    category="i18n",
    description="Compile PO files to MO",
    examples=[
        "bengal i18n compile",
        "bengal i18n compile --domain messages",
    ],
    requires_site=False,
    tags=["i18n", "gettext", "translations"],
)
@handle_cli_errors(show_art=False)
@click.option(
    "--domain",
    default="messages",
    help="Gettext domain (default: messages)",
)
@click.option(
    "--locale",
    "locales",
    multiple=True,
    help="Locale(s) to compile (default: all in i18n/)",
)
@click.argument("source", type=click.Path(exists=True), default=".")
def compile_cmd(domain: str, locales: tuple[str, ...], source: str) -> None:
    """
    Compile .po files to .mo.

    Looks for i18n/{locale}/LC_MESSAGES/{domain}.po and writes .mo alongside.
    """
    cli = get_cli_output()
    root = Path(source).resolve()
    localedir = root / "i18n"

    if not localedir.exists():
        cli.warning(f"No i18n directory at {localedir}")
        return

    # Find locales: from --locale or by scanning i18n/
    if locales:
        locale_dirs = [localedir / loc for loc in locales]
    else:
        locale_dirs = [d for d in localedir.iterdir() if d.is_dir()]

    compiled = 0
    for loc_dir in locale_dirs:
        if not loc_dir.is_dir():
            continue
        locale = loc_dir.name
        po_path = loc_dir / "LC_MESSAGES" / f"{domain}.po"
        if not po_path.exists():
            continue
        mo_path = loc_dir / "LC_MESSAGES" / f"{domain}.mo"
        try:
            import polib

            po = polib.pofile(str(po_path))
            po.save_as_mofile(str(mo_path))
            compiled += 1
            cli.success(f"Compiled {locale}: {po_path.relative_to(root)} → .mo")
        except Exception as e:
            cli.error(f"Failed to compile {po_path}: {e}")
            raise

    if compiled == 0:
        cli.warning("No .po files found to compile.")
        cli.info("Create i18n/{locale}/LC_MESSAGES/{domain}.po first.")
    else:
        clear_catalog_cache(root)
        cli.success(f"Compiled {compiled} catalog(s).")


# Regex to find t("key") or t('key') in templates
_T_PATTERN = re.compile(r'\bt\s*\(\s*["\']([^"\']+)["\']', re.MULTILINE)


@i18n_cli.command("extract")
@command_metadata(
    category="i18n",
    description="Extract t() calls from templates",
    examples=[
        "bengal i18n extract",
        "bengal i18n extract -o messages.pot",
    ],
    requires_site=False,
    tags=["i18n", "gettext", "translations"],
)
@handle_cli_errors(show_art=False)
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(),
    default="messages.pot",
    help="Output .pot file (default: messages.pot)",
)
@click.option(
    "--domain",
    default="messages",
    help="Gettext domain (default: messages)",
)
@click.argument("source", type=click.Path(exists=True), default=".")
def extract_cmd(output_path: str, domain: str, source: str) -> None:
    """
    Extract t() calls from templates and generate .pot.

    Scans content/, theme templates, and site templates for t("key") patterns.
    """
    cli = get_cli_output()
    root = Path(source).resolve()

    # Load config for theme/content paths
    config_loader = UnifiedConfigLoader()
    try:
        config = config_loader.load(root)
    except Exception:
        config = {}

    content_dir = root / config.get("build", {}).get("content_dir", "content")

    # Search paths: content, themes (if local), bengal themes
    search_dirs: list[Path] = []
    if content_dir.exists():
        search_dirs.append(content_dir)
    themes_dir = root / "themes"
    if themes_dir.exists():
        search_dirs.append(themes_dir)
    # Also scan root for top-level templates
    search_dirs.append(root)

    # Extensions to scan
    exts = (".html", ".kida", ".jinja2", ".jinja", ".j2")

    keys: set[str] = set()
    for search_dir in search_dirs:
        for path in search_dir.rglob("*"):
            if path.suffix.lower() in exts and path.is_file():
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                    for m in _T_PATTERN.finditer(text):
                        keys.add(m.group(1))
                except Exception:
                    pass

    if not keys:
        cli.warning("No t() calls found in templates.")
        return

    out = Path(output_path)
    if not out.is_absolute():
        out = root / out

    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        import polib

        pot = polib.POFile()
        pot.metadata = {
            "Content-Type": "text/plain; charset=UTF-8",
            "MIME-Version": "1.0",
        }
        for key in sorted(keys):
            pot.append(polib.POEntry(msgid=key, msgstr=""))
        pot.save(str(out))
        cli.success(f"Extracted {len(keys)} strings to {out.relative_to(root)}")
    except Exception as e:
        cli.error(f"Failed to write .pot: {e}")
        raise
