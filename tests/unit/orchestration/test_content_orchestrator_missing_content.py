from __future__ import annotations

import pytest

from bengal.core.site import Site
from bengal.errors import BengalConfigError


def test_site_discover_content_warns_when_content_dir_is_missing(tmp_path) -> None:
    site = Site(root_path=tmp_path)

    with pytest.warns(UserWarning, match="Content directory not found"):
        site.discover_content()

    assert site.pages == []
    assert site.sections == []


def test_site_discover_content_raises_when_missing_content_is_strict(tmp_path) -> None:
    site = Site(root_path=tmp_path, config={"build": {"strict_mode": True}})

    with pytest.raises(BengalConfigError, match="Content directory not found"):
        site.discover_content()
