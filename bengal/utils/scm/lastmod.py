"""Re-export last-modified helpers from core (postprocess convenience)."""

from bengal.core.page.lastmod import resolve_page_lastmod, resolve_page_lastmod_iso

__all__ = ["resolve_page_lastmod", "resolve_page_lastmod_iso"]
