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
from bengal.i18n.catalog import clear_catalog_cache, compute_coverage


@click.group("i18n", cls=BengalGroup)
def i18n_cli() -> None:
    """
    Internationalization (gettext PO/MO workflow).

    Commands:
        compile   Compile .po files to .mo
        extract   Scan templates for t() calls and generate .pot
        status    Show translation coverage per locale

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


def _extract_keys_from_templates(root: Path, config: dict) -> set[str]:
    """Extract t() keys from templates under content, themes, and root."""
    content_dir = root / config.get("build", {}).get("content_dir", "content")
    search_dirs: list[Path] = []
    if content_dir.exists():
        search_dirs.append(content_dir)
    themes_dir = root / "themes"
    if themes_dir.exists():
        search_dirs.append(themes_dir)
    search_dirs.append(root)
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
    return keys


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
    config_loader = UnifiedConfigLoader()
    try:
        config = config_loader.load(root)
    except Exception:
        config = {}

    raw = config.raw if hasattr(config, "raw") else config
    keys = _extract_keys_from_templates(root, raw)

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


@i18n_cli.command("status")
@command_metadata(
    category="i18n",
    description="Show translation coverage per locale",
    examples=[
        "bengal i18n status",
        "bengal i18n status --fail-on-missing",
    ],
    requires_site=False,
    tags=["i18n", "gettext", "translations", "coverage"],
)
@handle_cli_errors(show_art=False)
@click.option(
    "--domain",
    default="messages",
    help="Gettext domain (default: messages)",
)
@click.option(
    "--fail-on-missing-translations",
    "--fail-on-missing",
    "fail_on_missing",
    is_flag=True,
    help="Exit with code 1 if any locale has incomplete translations (CI gate)",
)
@click.argument("source", type=click.Path(exists=True), default=".")
def status_cmd(domain: str, fail_on_missing: bool, source: str) -> None:
    """
    Show translation coverage per locale.

    Compares template t() keys against each locale's PO file.
    Color coding: green (100%), yellow (80-99%), red (<80%).
    """
    cli = get_cli_output()
    root = Path(source).resolve()
    localedir = root / "i18n"

    config_loader = UnifiedConfigLoader()
    try:
        config = config_loader.load(root)
    except Exception:
        config = {}
    raw = config.raw if hasattr(config, "raw") else config

    keys = _extract_keys_from_templates(root, raw)
    if not keys:
        cli.warning("No t() calls found in templates.")
        cli.info("Run 'bengal i18n extract' to generate .pot, then add locales.")
        return

    # Locales: from config i18n.languages or from i18n/ dir
    locales: list[str] = []
    i18n_cfg = raw.get("i18n") or {}
    for lang in i18n_cfg.get("languages", []):
        if isinstance(lang, dict) and "code" in lang:
            locales.append(lang["code"])
        elif isinstance(lang, str):
            locales.append(lang)
    if not locales:
        locales.extend(
            d.name
            for d in (localedir.iterdir() if localedir.exists() else [])
            if d.is_dir() and (d / "LC_MESSAGES").exists()
        )

    if not locales:
        cli.warning(
            "No locales found. Add i18n.languages in config or create i18n/{locale}/LC_MESSAGES/"
        )
        return

    cli.info(f"Translation coverage ({len(keys)} keys, domain={domain})")
    any_incomplete = False
    for locale in sorted(locales):
        translated, total, missing = compute_coverage(localedir, domain, locale, keys)
        pct = (translated / total * 100) if total else 0
        if pct < 100:
            any_incomplete = True
        # Color: green 100%, yellow 80-99%, red <80%
        if pct >= 100:
            style = "[success]"
        elif pct >= 80:
            style = "[warning]"
        else:
            style = "[error]"
        line = f"  {locale}: {style}{translated}/{total} ({pct:.0f}%)[/]"
        cli.console.print(line)
        if missing and len(missing) <= 5:
            for k in missing[:5]:
                cli.info(f"    missing: {k}", icon="")
        elif missing:
            cli.info(f"    {len(missing)} missing", icon="")

    if fail_on_missing and any_incomplete:
        raise SystemExit(1)
