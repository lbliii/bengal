from types import SimpleNamespace
from unittest.mock import MagicMock

from bengal.content.page_source import get_raw_source


def test_get_raw_source_prefers_raw_content() -> None:
    page = SimpleNamespace(_raw_content="raw", _source="legacy")

    assert get_raw_source(page) == "raw"


def test_get_raw_source_falls_back_to_legacy_source() -> None:
    page = SimpleNamespace(_source="legacy")

    assert get_raw_source(page) == "legacy"


def test_get_raw_source_returns_empty_string_when_missing() -> None:
    page = SimpleNamespace()

    assert get_raw_source(page) == ""


def test_get_raw_source_ignores_mocked_raw_content_attribute() -> None:
    page = MagicMock()
    page._source = "legacy"

    assert get_raw_source(page) == "legacy"
