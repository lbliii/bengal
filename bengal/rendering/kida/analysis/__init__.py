"""Kida Template Introspection API.

Static analysis of compiled templates for caching optimization,
validation, and tooling support.

Core Capabilities:
    - Block enumeration: "What blocks does this template define?"
    - Dependency analysis: "What context variables does this block need?"
    - Purity inference: "Is this block deterministic?"
    - Role classification: "Is this navigation, content, or sidebar?"
    - Cache scope: "Can this be cached per-page or per-site?"

Design Principles:
    1. Zero syntax changes — Templates work exactly as before
    2. Zero author burden — Introspection is automatic, not annotated
    3. Zero runtime impact — Analysis happens at compile time
    4. Conservative claims — When uncertain, report "unknown"
    5. Standalone-ready — API designed for Kida as independent package
    6. Configurable — Memory/analysis trade-off controllable via Environment

Example:
    >>> from bengal.rendering.kida import Environment
    >>> env = Environment()
    >>> template = env.get_template("page.html")
    >>> meta = template.block_metadata()
    >>> nav = meta.get("nav")
    >>> if nav and nav.cache_scope == "site":
    ...     print(f"Nav can be cached site-wide, depends on: {nav.depends_on}")

Thread-Safety:
    All analysis classes are stateless or use immutable results.
    Safe for concurrent use across threads.
"""

from __future__ import annotations

from bengal.rendering.kida.analysis.analyzer import BlockAnalyzer
from bengal.rendering.kida.analysis.cache import infer_cache_scope
from bengal.rendering.kida.analysis.config import DEFAULT_CONFIG, AnalysisConfig
from bengal.rendering.kida.analysis.dependencies import DependencyWalker
from bengal.rendering.kida.analysis.landmarks import LandmarkDetector
from bengal.rendering.kida.analysis.metadata import BlockMetadata, TemplateMetadata
from bengal.rendering.kida.analysis.purity import PurityAnalyzer
from bengal.rendering.kida.analysis.roles import classify_role

__all__ = [
    "AnalysisConfig",
    "BlockAnalyzer",
    "BlockMetadata",
    "DEFAULT_CONFIG",
    "DependencyWalker",
    "LandmarkDetector",
    "PurityAnalyzer",
    "TemplateMetadata",
    "classify_role",
    "infer_cache_scope",
]
