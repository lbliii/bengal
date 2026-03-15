"""
Navigation Tree Models.

Provides hierarchical navigation with O(1) lookups and baseurl-aware URLs.
Pre-computed navigation trees enable fast sidebar and menu rendering.

Public API:
NavNode: Single navigation node (title, URL, children, state flags)
NavTree: Pre-computed navigation tree with O(1) URL lookups
NavTreeContext: Per-page context overlay for active trail detection
NavNodeProxy: Template-safe proxy that applies baseurl to URLs
NavTreeCache: Thread-safe cache for NavTree instances by version

URL Naming Convention:
    _path: Site-relative path WITHOUT baseurl (e.g., "/docs/foo/")
       Used for internal lookups, active trail detection, caching.

    href: Public URL WITH baseurl applied (e.g., "/bengal/docs/foo/")
      Used for template href attributes and external links.

When baseurl is configured (e.g., "/bengal" for GitHub Pages),
NavNodeProxy.href automatically includes it. Templates should always
use .href for links.

Template Usage:
{% for item in get_nav_tree(page) %}
  <a href="{{ item.href }}">{{ item.title }}</a>
  {% if item.is_in_trail %}class="active"{% endif %}
{% endfor %}

Internal Usage:
if page._path in nav_tree.active_trail_urls:
    mark_active()

Performance:
- O(1) URL lookup via NavTree.flat_nodes dict
- Tree built once per version, cached in NavTreeCache
- NavNodeProxy wraps nodes without copying for template state

Related Packages:
bengal.core.site: Site object that holds the NavTree
bengal.core.section: Section objects that form the tree structure
bengal.rendering.template_functions.navigation: Template functions

"""

from __future__ import annotations

from bengal.core.nav_tree.cache import NavTreeCache
from bengal.core.nav_tree.context import NavTreeContext
from bengal.core.nav_tree.node import NavNode
from bengal.core.nav_tree.proxy import NavNodeProxy
from bengal.core.nav_tree.tree import NavTree

__all__ = [
    "NavNode",
    "NavNodeProxy",
    "NavTree",
    "NavTreeCache",
    "NavTreeContext",
]
