"""
Context-aware error handlers to enrich exception displays.

Handlers provide concise, helpful suggestions for common Python errors:
- ImportError: Show available exports in the target module and close matches
- AttributeError: Show available attributes on a target module and close matches
- TypeError: Generic guidance for common patterns

These handlers are best-effort and must never raise; they return lightweight
strings suitable for inclusion in compact/minimal traceback renderers.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass
class ContextAwareHelp:
    title: str
    lines: list[str]


def get_context_aware_help(error: BaseException) -> ContextAwareHelp | None:
    try:
        if isinstance(error, ImportError):
            return _handle_import_error(error)
        if isinstance(error, AttributeError):
            return _handle_attribute_error(error)
        if isinstance(error, TypeError):
            return _handle_type_error(error)
    except Exception:
        return None
    return None


def _handle_import_error(error: ImportError) -> ContextAwareHelp | None:
    # Common messages:
    #   cannot import name 'X' from 'pkg.mod' (/path/...)
    #   No module named 'pkg'
    msg = str(error)

    if "cannot import name" in msg and " from " in msg:
        missing = _between(msg, "name '", "'") or _between(msg, 'name "', '"')
        module = _between(msg, " from '", "'") or _between(msg, ' from "', '"')
        if module:
            exports = _safe_list_module_exports(module)
            suggestions = _closest_matches(missing, exports) if missing else []
            lines: list[str] = []
            if suggestions:
                lines.append("Did you mean:")
                lines.extend([f"  • {s}" for s in suggestions])
            # Show a short sample of available exports to guide users
            if exports:
                preview = ", ".join(sorted(exports)[:8])
                lines.append(f"Available in {module}: {preview}{' …' if len(exports) > 8 else ''}")
            title = "ImportError: cannot import name"
            return ContextAwareHelp(title=title, lines=lines)

    if "No module named" in msg:
        # Suggest installing or checking environment
        missing_mod = _between(msg, "No module named '", "'") or _between(
            msg, 'No module named "', '"'
        )
        title = "ImportError: module not found"
        lines = [
            f"Missing module: {missing_mod}" if missing_mod else "Missing module",
            "Check virtualenv and dependencies (pip/uv/poetry)",
        ]
        return ContextAwareHelp(title=title, lines=lines)

    return None


def _handle_attribute_error(error: AttributeError) -> ContextAwareHelp | None:
    # Common messages:
    #   module 'json' has no attribute 'Dump'
    #   'dict' object has no attribute 'x'
    msg = str(error)

    # Module attribute case
    if "module '" in msg and "' has no attribute '" in msg:
        module = _between(msg, "module '", "'")
        attr = _between(msg, "attribute '", "'")
        exports = _safe_list_module_exports(module) if module else []
        suggestions = _closest_matches(attr, exports) if attr else []
        lines: list[str] = []
        if suggestions:
            lines.append("Did you mean:")
            lines.extend([f"  • {s}" for s in suggestions])
        if exports:
            preview = ", ".join(sorted(exports)[:8])
            lines.append(f"Available in {module}: {preview}{' …' if len(exports) > 8 else ''}")
        title = "AttributeError: unknown module attribute"
        return ContextAwareHelp(title=title, lines=lines)

    # Dict object attribute case
    if "'dict' object has no attribute" in msg:
        attr = _between(msg, "has no attribute '", "'")
        title = "AttributeError: dict attribute access"
        if attr:
            lines = [
                "Use dict.get('<key>') or bracket access instead of attribute access",
                f"Try: mapping.get('{attr}') or mapping.get('{attr}', default)",
            ]
        else:
            lines = [
                "Use dict.get('<key>') or bracket access instead of attribute access",
            ]
        return ContextAwareHelp(title=title, lines=lines)

    return None


def _handle_type_error(error: TypeError) -> ContextAwareHelp | None:
    msg = str(error)
    title = "TypeError: argument/type mismatch"
    lines = [
        "Check function signature and parameter order",
        "Validate types of inputs (e.g., str vs int, list vs dict)",
    ]
    if "positional arguments" in msg or "keyword arguments" in msg:
        lines.append("Verify number of positional/keyword arguments")
    if "expected" in msg and "got" in msg:
        lines.append("Ensure provided value matches expected type")
    return ContextAwareHelp(title=title, lines=lines)


# =============== helpers ===============


def _between(text: str, start: str, end: str) -> str | None:
    try:
        s = text.index(start) + len(start)
        e = text.index(end, s)
        return text[s:e]
    except ValueError:
        return None


def _safe_list_module_exports(module_path: str) -> list[str]:
    exports: list[str] = []
    try:
        mod = __import__(module_path, fromlist=["*"])
        if hasattr(mod, "__all__") and isinstance(mod.__all__, (list, tuple)):
            exports = [str(x) for x in mod.__all__]
        else:
            exports = [n for n in dir(mod) if not n.startswith("_")]
    except Exception:
        return []
    return sorted(set(exports))


def _closest_matches(name: str | None, candidates: Iterable[str]) -> list[str]:
    if not name:
        return []
    try:
        from difflib import get_close_matches

        return get_close_matches(name, list(candidates), n=5, cutoff=0.6)
    except Exception:
        return []
