"""Unit tests for Content Signals enforcement in output format generation.

Verifies that OutputFormatsGenerator respects ai_input, ai_train, and search
signals when deciding which pages receive output formats.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_page(
    title="Test",
    path="/test/",
    in_ai_input=True,
    in_ai_train=True,
    in_search=True,
    href="/test/",
):
    page = MagicMock()
    page.title = title
    page._path = path
    page.href = href
    page.output_path = Path(f"/tmp/output{path}index.html")
    page.in_ai_input = in_ai_input
    page.in_ai_train = in_ai_train
    page.in_search = in_search
    page.draft = False
    page.plain_text = f"Content for {title}"
    page.html_content = f"<p>Content for {title}</p>"
    page.date = None
    page.tags = []
    page.metadata = {"title": title}
    page.source_path = Path(f"content/{title.lower()}.md")
    return page


def _make_site(pages=None):
    site = MagicMock()
    site.pages = pages or []
    site.output_dir = Path("/tmp/output")
    site.baseurl = ""
    site.title = "Test Site"
    site.dev_mode = False
    site.config = MagicMock()
    site.config.get = lambda key, default=None: {
        "output_formats": {
            "enabled": True,
            "per_page": ["json", "llm_txt"],
            "site_wide": ["index_json", "llm_full"],
            "options": {},
        },
        "search": {"lunr": {"prebuilt": False}},
    }.get(key, default)
    return site


class TestAiInputEnforcement:
    """Pages with in_ai_input=False should not get JSON/TXT output."""

    def test_ai_input_false_excluded_from_json(self):
        from bengal.postprocess.output_formats import OutputFormatsGenerator

        restricted = _make_page("Restricted", "/restricted/", in_ai_input=False)
        allowed = _make_page("Allowed", "/allowed/", in_ai_input=True)
        site = _make_site([restricted, allowed])

        gen = OutputFormatsGenerator(
            site,
            config={
                "enabled": True,
                "per_page": ["json"],
                "site_wide": [],
            },
        )

        with patch.object(gen, "_filter_pages", return_value=[restricted, allowed]):
            json_gen_mock = MagicMock()
            json_gen_mock.generate.return_value = 1
            with patch(
                "bengal.postprocess.output_formats.PageJSONGenerator",
                return_value=json_gen_mock,
            ):
                gen.generate()
                call_args = json_gen_mock.generate.call_args
                pages_passed = call_args[0][0]
                assert allowed in pages_passed
                assert restricted not in pages_passed

    def test_ai_input_false_excluded_from_txt(self):
        from bengal.postprocess.output_formats import OutputFormatsGenerator

        restricted = _make_page("Restricted", "/restricted/", in_ai_input=False)
        allowed = _make_page("Allowed", "/allowed/", in_ai_input=True)
        site = _make_site([restricted, allowed])

        gen = OutputFormatsGenerator(
            site,
            config={
                "enabled": True,
                "per_page": ["llm_txt"],
                "site_wide": [],
            },
        )

        with patch.object(gen, "_filter_pages", return_value=[restricted, allowed]):
            txt_gen_mock = MagicMock()
            txt_gen_mock.generate.return_value = 1
            with patch(
                "bengal.postprocess.output_formats.PageTxtGenerator",
                return_value=txt_gen_mock,
            ):
                gen.generate()
                call_args = txt_gen_mock.generate.call_args
                pages_passed = call_args[0][0]
                assert allowed in pages_passed
                assert restricted not in pages_passed


class TestAiTrainEnforcement:
    """Pages with in_ai_train=False should be excluded from llm-full.txt."""

    def test_ai_train_false_excluded_from_llm_full(self):
        from bengal.postprocess.output_formats import OutputFormatsGenerator

        no_train = _make_page("NoTrain", "/no-train/", in_ai_train=False)
        yes_train = _make_page("YesTrain", "/yes-train/", in_ai_train=True)
        site = _make_site([no_train, yes_train])

        gen = OutputFormatsGenerator(
            site,
            config={
                "enabled": True,
                "per_page": [],
                "site_wide": ["llm_full"],
            },
        )

        with patch.object(gen, "_filter_pages", return_value=[no_train, yes_train]):
            llm_gen_mock = MagicMock()
            with patch(
                "bengal.postprocess.output_formats.SiteLlmTxtGenerator",
                return_value=llm_gen_mock,
            ):
                gen.generate()
                call_args = llm_gen_mock.generate.call_args
                pages_passed = call_args[0][0]
                assert yes_train in pages_passed
                assert no_train not in pages_passed


class TestSearchEnforcement:
    """Pages with in_search=False should be excluded from index.json."""

    def test_search_false_excluded_from_index(self):
        from bengal.postprocess.output_formats import OutputFormatsGenerator

        no_search = _make_page("NoSearch", "/no-search/", in_search=False)
        yes_search = _make_page("YesSearch", "/yes-search/", in_search=True)
        site = _make_site([no_search, yes_search])

        gen = OutputFormatsGenerator(
            site,
            config={
                "enabled": True,
                "per_page": [],
                "site_wide": ["index_json"],
            },
        )

        with patch.object(gen, "_filter_pages", return_value=[no_search, yes_search]):
            index_gen_mock = MagicMock()
            index_gen_mock.generate.return_value = Path("/tmp/index.json")
            with patch(
                "bengal.postprocess.output_formats.SiteIndexGenerator",
                return_value=index_gen_mock,
            ):
                gen.generate()
                call_args = index_gen_mock.generate.call_args
                pages_passed = call_args[0][0]
                assert yes_search in pages_passed
                assert no_search not in pages_passed


class TestAllSignalsPermissive:
    """When all signals are permissive, all pages go through."""

    def test_all_pages_included_when_all_permissive(self):
        from bengal.postprocess.output_formats import OutputFormatsGenerator

        page1 = _make_page("Page1", "/page1/")
        page2 = _make_page("Page2", "/page2/")
        site = _make_site([page1, page2])

        gen = OutputFormatsGenerator(
            site,
            config={
                "enabled": True,
                "per_page": ["json"],
                "site_wide": ["llm_full"],
            },
        )

        with patch.object(gen, "_filter_pages", return_value=[page1, page2]):
            json_gen_mock = MagicMock()
            json_gen_mock.generate.return_value = 2
            llm_gen_mock = MagicMock()
            with (
                patch(
                    "bengal.postprocess.output_formats.PageJSONGenerator",
                    return_value=json_gen_mock,
                ),
                patch(
                    "bengal.postprocess.output_formats.SiteLlmTxtGenerator",
                    return_value=llm_gen_mock,
                ),
            ):
                gen.generate()

                json_pages = json_gen_mock.generate.call_args[0][0]
                assert len(json_pages) == 2

                llm_pages = llm_gen_mock.generate.call_args[0][0]
                assert len(llm_pages) == 2
