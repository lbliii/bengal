"""
Debug and introspection utilities for Bengal.

Provides tools for understanding how pages are built, including template
resolution, dependency tracking, cache status, and performance analysis.

Key Components:
    - PageExplainer: Generate explanations for how pages are built
    - ExplanationReporter: Format and display explanations in terminal

Related Modules:
    - bengal.cli.commands.explain: CLI command for page explanation
    - bengal.core.page: Page model being explained
    - bengal.rendering.template_engine: Template resolution
    - bengal.cache.build_cache: Cache status introspection

See Also:
    - plan/active/rfc-explain-page.md: Design RFC for this feature
"""

from __future__ import annotations

from bengal.debug.explainer import PageExplainer
from bengal.debug.models import (
    CacheInfo,
    DependencyInfo,
    OutputInfo,
    PageExplanation,
    ShortcodeUsage,
    SourceInfo,
    TemplateInfo,
)
from bengal.debug.reporter import ExplanationReporter

__all__ = [
    "PageExplainer",
    "PageExplanation",
    "ExplanationReporter",
    "SourceInfo",
    "TemplateInfo",
    "DependencyInfo",
    "ShortcodeUsage",
    "CacheInfo",
    "OutputInfo",
]

