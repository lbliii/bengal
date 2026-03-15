"""Version URL template registration.

Registers get_version_target_url and page_exists_in_version with template
environments. Core logic lives in bengal.core.version_url.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.core.version_url import get_version_target_url, page_exists_in_version

if TYPE_CHECKING:
    from bengal.protocols import PageLike, SiteLike, TemplateEnvironment


def register(env: TemplateEnvironment, site: SiteLike) -> None:
    """
    Register version URL functions with template environment.

    Registers global functions for template use: {{ get_version_target_url(page, v) }}

    The preferred engine-agnostic approach is to use the Site method:
        {{ site.get_version_target_url(page, v) }}
    """

    def get_version_target_url_wrapper(
        page: PageLike | None, target_version: dict[str, Any] | None
    ) -> str:
        return get_version_target_url(page, target_version, site)

    def page_exists_in_version_wrapper(path: str, version_id: str) -> bool:
        return page_exists_in_version(path, version_id, site)

    env.globals.update(
        {
            "get_version_target_url": get_version_target_url_wrapper,
            "page_exists_in_version": page_exists_in_version_wrapper,
        }
    )
