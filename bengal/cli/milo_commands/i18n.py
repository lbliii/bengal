"""I18n group — internationalization (PO/MO) commands."""

from __future__ import annotations

import re
from typing import Annotated

from milo import Description


def i18n_compile(
    source: Annotated[str, Description("Source directory path")] = "",
    domain: Annotated[str, Description("Gettext domain")] = "messages",
    locale: Annotated[
        str, Description("Locale(s) to compile, comma-separated (default: all)")
    ] = "",
) -> dict:
    """Compile .po files to .mo."""
    from pathlib import Path

    from bengal.i18n.catalog import clear_catalog_cache
    from bengal.output import get_cli_output

    source = source or "."
    cli = get_cli_output()
    root = Path(source).resolve()
    localedir = root / "i18n"

    if not localedir.exists():
        cli.render_write(
            "command_empty.kida",
            title="Compile Translations",
            message=f"No i18n directory at {localedir}",
            steps=["Run `bengal i18n init <locale>` to create locale directories."],
        )
        return {"status": "skipped", "message": f"No i18n directory at {localedir}", "compiled": 0}

    locales = [loc.strip() for loc in locale.split(",") if loc.strip()] if locale else []

    if locales:
        locale_dirs = [localedir / loc for loc in locales]
    else:
        locale_dirs = [d for d in localedir.iterdir() if d.is_dir()]

    compiled_items = []
    for loc_dir in locale_dirs:
        if not loc_dir.is_dir():
            continue
        loc_name = loc_dir.name
        po_path = loc_dir / "LC_MESSAGES" / f"{domain}.po"
        if not po_path.exists():
            continue
        mo_path = loc_dir / "LC_MESSAGES" / f"{domain}.mo"
        try:
            import polib

            po = polib.pofile(str(po_path))
            po.save_as_mofile(str(mo_path))
            compiled_items.append(
                {
                    "name": loc_name,
                    "description": f"{po_path.relative_to(root)} -> {mo_path.relative_to(root)}",
                }
            )
        except Exception as e:
            cli.error(f"Failed to compile {po_path}: {e}")
            cli.tip("Check the .po file for syntax errors — `msgfmt --check` can help locate them.")
            raise

    compiled = len(compiled_items)
    if compiled == 0:
        cli.render_write(
            "command_empty.kida",
            title="Compile Translations",
            message="No .po files found to compile.",
            steps=["Create i18n/{locale}/LC_MESSAGES/{domain}.po first."],
        )
        raise SystemExit(1)

    clear_catalog_cache(root)
    cli.render_write(
        "command_list.kida",
        title="Compile Translations",
        summary=f"{compiled} catalog(s) compiled for domain={domain}",
        items=compiled_items,
    )

    return {"compiled": compiled, "domain": domain}


# Regex to find t("key") or t('key') in templates
_T_PATTERN = re.compile(r'\bt\s*\(\s*["\']([^"\']+)["\']', re.MULTILINE)


def _extract_keys_from_templates(root, config):
    """Extract t() keys from templates under content, themes, and root."""
    content_dir = root / config.get("build", {}).get("content_dir", "content")
    search_dirs = []
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
                except OSError as e:
                    import logging

                    logging.getLogger("bengal.cli.i18n").debug(
                        "i18n_template_read_error: %s — %s", path, e
                    )
    return keys


def i18n_extract(
    source: Annotated[str, Description("Source directory path")] = "",
    output_path: Annotated[str, Description("Output .pot file path")] = "messages.pot",
    domain: Annotated[str, Description("Gettext domain")] = "messages",
) -> dict:
    """Extract t() calls from templates and generate .pot."""
    from pathlib import Path

    from bengal.config import UnifiedConfigLoader
    from bengal.config.directory_loader import ConfigLoadError
    from bengal.output import get_cli_output

    source = source or "."
    cli = get_cli_output()
    root = Path(source).resolve()

    config_loader = UnifiedConfigLoader()
    try:
        config = config_loader.load(root)
    except ConfigLoadError, OSError:
        config = {}

    raw = config.raw if hasattr(config, "raw") else config
    keys = _extract_keys_from_templates(root, raw)

    if not keys:
        cli.render_write(
            "command_empty.kida",
            title="Extract Translations",
            message="No t() calls found in templates.",
            steps=["Add t('key') calls to templates or content before extracting."],
        )
        return {"status": "skipped", "message": "No t() calls found in templates", "keys": 0}

    out = Path(output_path)
    if not out.is_absolute():
        out = root / out

    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        import polib

        pot = polib.POFile()
        pot.metadata = {"Content-Type": "text/plain; charset=UTF-8", "MIME-Version": "1.0"}
        for key in sorted(keys):
            pot.append(polib.POEntry(msgid=key, msgstr=""))
        pot.save(str(out))
        cli.render_write(
            "kv_detail.kida",
            title="Extract Translations",
            items=[
                {"label": "Strings", "value": str(len(keys))},
                {"label": "Output", "value": str(out.relative_to(root))},
                {"label": "Domain", "value": domain},
            ],
            badge={"level": "success", "text": "Done"},
        )
    except Exception as e:
        cli.error(f"Failed to write .pot: {e}")
        cli.tip("Check write permissions on the i18n/ directory and that the output path exists.")
        raise

    return {"keys": len(keys), "output": str(out), "domain": domain}


def i18n_status(
    source: Annotated[str, Description("Source directory path")] = "",
    domain: Annotated[str, Description("Gettext domain")] = "messages",
    fail_on_missing: Annotated[
        bool, Description("Exit 1 if any locale has incomplete translations (CI gate)")
    ] = False,
) -> dict:
    """Show translation coverage per locale."""
    from pathlib import Path

    from bengal.config import UnifiedConfigLoader
    from bengal.config.directory_loader import ConfigLoadError
    from bengal.i18n.catalog import compute_coverage
    from bengal.output import get_cli_output

    source = source or "."
    cli = get_cli_output()
    root = Path(source).resolve()
    localedir = root / "i18n"

    config_loader = UnifiedConfigLoader()
    try:
        config = config_loader.load(root)
    except ConfigLoadError, OSError:
        config = {}
    raw = config.raw if hasattr(config, "raw") else config

    keys = _extract_keys_from_templates(root, raw)
    if not keys:
        cli.render_write(
            "command_empty.kida",
            title="Translation Coverage",
            message="No t() calls found in templates.",
            steps=["Run `bengal i18n extract` after adding translation calls."],
        )
        return {
            "status": "skipped",
            "message": "No t() calls found in templates",
            "locales": [],
            "keys": 0,
        }

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
        cli.render_write(
            "command_empty.kida",
            title="Translation Coverage",
            message="No locales found.",
            steps=["Add i18n.languages in config or create i18n/{locale}/LC_MESSAGES/."],
        )
        return {
            "status": "skipped",
            "message": "No locales found",
            "locales": [],
            "keys": len(keys),
        }

    any_incomplete = False
    coverage_items = []
    for loc in sorted(locales):
        translated, total, missing = compute_coverage(localedir, domain, loc, keys)
        pct = (translated / total * 100) if total else 0
        if pct < 100:
            any_incomplete = True
        missing_note = ""
        if missing and len(missing) <= 5:
            missing_note = "  missing: " + ", ".join(missing[:5])
        elif missing:
            missing_note = f"  {len(missing)} missing"
        coverage_items.append(
            {"label": loc, "value": f"{translated}/{total} ({pct:.0f}%){missing_note}"}
        )

    cli.render_write(
        "kv_detail.kida",
        title=f"Translation Coverage ({len(keys)} keys, domain={domain})",
        items=coverage_items,
    )

    if fail_on_missing and any_incomplete:
        raise SystemExit(1)

    return {"locales": locales, "keys": len(keys), "complete": not any_incomplete}


def i18n_init(
    locale_codes: Annotated[str, Description("Locale codes, comma-separated (e.g. es,fr,de)")],
    source: Annotated[str, Description("Source directory path")] = "",
    domain: Annotated[str, Description("Gettext domain")] = "messages",
) -> dict:
    """Initialize locale directory structure and PO files."""
    from pathlib import Path

    from bengal.output import get_cli_output

    source = source or "."
    codes = [c.strip() for c in locale_codes.split(",") if c.strip()]

    cli = get_cli_output()
    root = Path(source).resolve()
    localedir = root / "i18n"
    pot_path = root / f"{domain}.pot"

    created_items = []
    existing_items = []
    for locale in codes:
        lc_dir = localedir / locale / "LC_MESSAGES"
        po_path = lc_dir / f"{domain}.po"

        if po_path.exists():
            existing_items.append(
                {"name": locale, "description": f"{po_path.relative_to(root)} already exists"}
            )
            continue

        lc_dir.mkdir(parents=True, exist_ok=True)

        try:
            import polib

            if pot_path.exists():
                pot = polib.pofile(str(pot_path))
                po = polib.POFile()
                po.metadata = dict(pot.metadata)
                po.metadata["Language"] = locale
                for entry in pot:
                    po.append(polib.POEntry(msgid=entry.msgid, msgstr=""))
            else:
                po = polib.POFile()
                po.metadata = {
                    "Content-Type": "text/plain; charset=UTF-8",
                    "MIME-Version": "1.0",
                    "Language": locale,
                }

            po.save(str(po_path))
            created_items.append({"name": locale, "description": str(po_path.relative_to(root))})
        except ImportError:
            cli.error("polib is required: pip install bengal[gettext]")
            cli.tip("Install the gettext extras with `pip install bengal[gettext]` then re-run.")
            raise SystemExit(1) from None
        except Exception as e:
            cli.error(f"Failed to create {po_path}: {e}")
            cli.tip("Check write permissions on the locale directory, then re-run.")
            raise

    created = len(created_items)
    if created_items or existing_items:
        cli.render_write(
            "command_list.kida",
            title="Initialize Translations",
            summary=f"{created} created, {len(existing_items)} existing",
            items=[
                *[{**item, "status": "created"} for item in created_items],
                *[{**item, "status": "exists"} for item in existing_items],
            ],
        )
    if created:
        if pot_path.exists():
            cli.info(f"Used {pot_path.name} as template.")
        else:
            cli.tip("Run 'bengal i18n extract' first to generate a .pot template.")

    return {"created": created, "locales": codes, "domain": domain}


def i18n_sync(
    source: Annotated[str, Description("Source directory path")] = "",
    domain: Annotated[str, Description("Gettext domain")] = "messages",
    locale: Annotated[str, Description("Locale(s) to sync, comma-separated (default: all)")] = "",
) -> dict:
    """Sync PO files with current template keys."""
    from pathlib import Path

    from bengal.config import UnifiedConfigLoader
    from bengal.config.directory_loader import ConfigLoadError
    from bengal.output import get_cli_output

    source = source or "."
    cli = get_cli_output()
    root = Path(source).resolve()
    localedir = root / "i18n"

    if not localedir.exists():
        cli.render_write(
            "command_empty.kida",
            title="Sync Translations",
            message=f"No i18n directory at {localedir}",
            steps=["Run `bengal i18n init <locale>` to create locale directories."],
        )
        return {"status": "skipped", "message": f"No i18n directory at {localedir}", "synced": 0}

    config_loader = UnifiedConfigLoader()
    try:
        config = config_loader.load(root)
    except ConfigLoadError, OSError:
        config = {}
    raw = config.raw if hasattr(config, "raw") else config

    keys = _extract_keys_from_templates(root, raw)
    if not keys:
        cli.render_write(
            "command_empty.kida",
            title="Sync Translations",
            message="No t() calls found in templates.",
            steps=["Add t('key') calls, then run `bengal i18n extract`."],
        )
        return {"status": "skipped", "message": "No t() calls found in templates", "synced": 0}

    key_count = len(keys)

    try:
        import polib
    except ImportError:
        cli.error("polib is required: pip install bengal[gettext]")
        cli.tip("Install the gettext extras with `pip install bengal[gettext]` then re-run.")
        raise SystemExit(1) from None

    locales = [loc.strip() for loc in locale.split(",") if loc.strip()] if locale else []

    if locales:
        locale_dirs = [localedir / loc for loc in locales]
    else:
        locale_dirs = [d for d in localedir.iterdir() if d.is_dir()]

    synced = 0
    sync_items = []
    missing_po_items = []
    for loc_dir in locale_dirs:
        if not loc_dir.is_dir():
            continue
        loc_name = loc_dir.name
        po_path = loc_dir / "LC_MESSAGES" / f"{domain}.po"
        if not po_path.exists():
            missing_po_items.append(
                {"name": loc_name, "description": f"run `bengal i18n init {loc_name}`"}
            )
            continue

        po = polib.pofile(str(po_path))
        existing_ids = {entry.msgid for entry in po}

        added = 0
        for key in sorted(keys):
            if key not in existing_ids:
                po.append(polib.POEntry(msgid=key, msgstr=""))
                added += 1

        obsoleted = 0
        for entry in list(po):
            if entry.msgid and entry.msgid not in keys and not entry.obsolete:
                entry.obsolete = True
                obsoleted += 1

        if added or obsoleted:
            po.save(str(po_path))
            synced += 1
            parts = []
            if added:
                parts.append(f"+{added} new")
            if obsoleted:
                parts.append(f"~{obsoleted} obsolete")
            sync_items.append({"name": loc_name, "description": ", ".join(parts)})
        else:
            sync_items.append({"name": loc_name, "description": "up to date"})

    if sync_items:
        cli.render_write(
            "command_list.kida",
            title="Sync Translations",
            summary=f"{len(sync_items)} locale(s), {synced} synced, {key_count} key(s)",
            items=sync_items,
        )
    if missing_po_items:
        cli.render_write(
            "command_list.kida",
            title="Missing Translation Catalogs",
            summary=f"{len(missing_po_items)} locale(s) missing {domain}.po",
            items=missing_po_items,
        )
    if synced:
        cli.tip("Run 'bengal i18n compile' to regenerate .mo files.")
    elif not sync_items and not missing_po_items:
        cli.render_write(
            "command_empty.kida",
            title="Sync Translations",
            message="All locales already in sync.",
            mascot=False,
        )

    return {"synced": synced, "keys": key_count, "domain": domain}
