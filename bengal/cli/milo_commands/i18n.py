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

    from bengal.cli.utils import get_cli_output
    from bengal.i18n.catalog import clear_catalog_cache

    source = source or "."
    cli = get_cli_output()
    root = Path(source).resolve()
    localedir = root / "i18n"

    if not localedir.exists():
        cli.warning(f"No i18n directory at {localedir}")
        return {"status": "skipped", "message": f"No i18n directory at {localedir}", "compiled": 0}

    locales = [loc.strip() for loc in locale.split(",") if loc.strip()] if locale else []

    if locales:
        locale_dirs = [localedir / loc for loc in locales]
    else:
        locale_dirs = [d for d in localedir.iterdir() if d.is_dir()]

    compiled = 0
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
            compiled += 1
            cli.success(f"Compiled {loc_name}: {po_path.relative_to(root)} -> .mo")
        except Exception as e:
            cli.error(f"Failed to compile {po_path}: {e}")
            raise

    if compiled == 0:
        cli.warning("No .po files found to compile.")
        cli.info("Create i18n/{locale}/LC_MESSAGES/{domain}.po first.")
    else:
        clear_catalog_cache(root)
        cli.success(f"Compiled {compiled} catalog(s).")

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

    from bengal.cli.utils import get_cli_output
    from bengal.config import UnifiedConfigLoader
    from bengal.config.directory_loader import ConfigLoadError

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
        cli.warning("No t() calls found in templates.")
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
        cli.success(f"Extracted {len(keys)} strings to {out.relative_to(root)}")
    except Exception as e:
        cli.error(f"Failed to write .pot: {e}")
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

    from bengal.cli.utils import get_cli_output
    from bengal.config import UnifiedConfigLoader
    from bengal.config.directory_loader import ConfigLoadError
    from bengal.i18n.catalog import compute_coverage

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
        cli.warning("No t() calls found in templates.")
        cli.info("Run 'bengal i18n extract' to generate .pot, then add locales.")
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
        cli.warning(
            "No locales found. Add i18n.languages in config or create i18n/{locale}/LC_MESSAGES/"
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

    from bengal.cli.utils import get_cli_output

    source = source or "."
    codes = [c.strip() for c in locale_codes.split(",") if c.strip()]

    cli = get_cli_output()
    root = Path(source).resolve()
    localedir = root / "i18n"
    pot_path = root / f"{domain}.pot"

    created = 0
    for locale in codes:
        lc_dir = localedir / locale / "LC_MESSAGES"
        po_path = lc_dir / f"{domain}.po"

        if po_path.exists():
            cli.warning(f"Already exists: {po_path.relative_to(root)}")
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
            created += 1
            cli.success(f"Created {po_path.relative_to(root)}")
        except ImportError:
            cli.error("polib is required: pip install bengal[gettext]")
            raise SystemExit(1) from None
        except Exception as e:
            cli.error(f"Failed to create {po_path}: {e}")
            raise

    if created:
        cli.success(f"Initialized {created} locale(s).")
        if pot_path.exists():
            cli.info(f"Used {pot_path.name} as template.")
        else:
            cli.info("Tip: Run 'bengal i18n extract' first to generate a .pot template.")
    elif codes:
        cli.info("All locales already exist.")

    return {"created": created, "locales": codes, "domain": domain}


def i18n_sync(
    source: Annotated[str, Description("Source directory path")] = "",
    domain: Annotated[str, Description("Gettext domain")] = "messages",
    locale: Annotated[str, Description("Locale(s) to sync, comma-separated (default: all)")] = "",
) -> dict:
    """Sync PO files with current template keys."""
    from pathlib import Path

    from bengal.cli.utils import get_cli_output
    from bengal.config import UnifiedConfigLoader
    from bengal.config.directory_loader import ConfigLoadError

    source = source or "."
    cli = get_cli_output()
    root = Path(source).resolve()
    localedir = root / "i18n"

    if not localedir.exists():
        cli.warning(f"No i18n directory at {localedir}")
        cli.info("Tip: Run 'bengal i18n init <locale>' to create locale directories.")
        return {"status": "skipped", "message": f"No i18n directory at {localedir}", "synced": 0}

    config_loader = UnifiedConfigLoader()
    try:
        config = config_loader.load(root)
    except ConfigLoadError, OSError:
        config = {}
    raw = config.raw if hasattr(config, "raw") else config

    keys = _extract_keys_from_templates(root, raw)
    if not keys:
        cli.warning("No t() calls found in templates.")
        return {"status": "skipped", "message": "No t() calls found in templates", "synced": 0}

    cli.info(f"Found {len(keys)} keys in templates.")

    try:
        import polib
    except ImportError:
        cli.error("polib is required: pip install bengal[gettext]")
        raise SystemExit(1) from None

    locales = [loc.strip() for loc in locale.split(",") if loc.strip()] if locale else []

    if locales:
        locale_dirs = [localedir / loc for loc in locales]
    else:
        locale_dirs = [d for d in localedir.iterdir() if d.is_dir()]

    synced = 0
    sync_items = []
    for loc_dir in locale_dirs:
        if not loc_dir.is_dir():
            continue
        loc_name = loc_dir.name
        po_path = loc_dir / "LC_MESSAGES" / f"{domain}.po"
        if not po_path.exists():
            cli.warning(f"No PO file for {loc_name} -- run 'bengal i18n init {loc_name}'")
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
            "item_list.kida",
            title=f"Sync Results ({synced} synced)" if synced else "Sync Results",
            items=sync_items,
        )
    if synced:
        cli.tip("Run 'bengal i18n compile' to regenerate .mo files.")
    elif not sync_items:
        cli.info("All locales already in sync.")

    return {"synced": synced, "keys": len(keys), "domain": domain}
