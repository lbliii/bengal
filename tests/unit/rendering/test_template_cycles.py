from __future__ import annotations


from pathlib import Path

import pytest
from jinja2.exceptions import TemplateError

from bengal.core.site import Site
from bengal.rendering.template_engine import TemplateEngine


class TestTemplateCircularDependencies:
    def test_direct_self_include(self, tmp_path):
        templates_dir = Path(tmp_path) / "templates"
        templates_dir.mkdir()
        (templates_dir / "loop.html").write_text("{% include 'loop.html' %}")

        (Path(tmp_path) / "content").mkdir()
        (Path(tmp_path) / "bengal.toml").write_text("title='t'")

        site = Site.from_config(tmp_path)
        engine = TemplateEngine(site)

        with pytest.raises((TemplateError, RecursionError)):
            tpl = engine.env.get_template("loop.html")
            tpl.render()

    def test_indirect_include_cycle(self, tmp_path):
        templates_dir = Path(tmp_path) / "templates"
        templates_dir.mkdir()
        (templates_dir / "a.html").write_text("{% include 'b.html' %}")
        (templates_dir / "b.html").write_text("{% include 'a.html' %}")

        (Path(tmp_path) / "content").mkdir()
        (Path(tmp_path) / "bengal.toml").write_text("title='t'")

        site = Site.from_config(tmp_path)
        engine = TemplateEngine(site)

        with pytest.raises((TemplateError, RecursionError)):
            tpl = engine.env.get_template("a.html")
            tpl.render()

    def test_extends_cycle(self, tmp_path):
        templates_dir = Path(tmp_path) / "templates"
        templates_dir.mkdir()
        (templates_dir / "base.html").write_text("{% extends 'base.html' %}")

        (Path(tmp_path) / "content").mkdir()
        (Path(tmp_path) / "bengal.toml").write_text("title='t'")

        site = Site.from_config(tmp_path)
        engine = TemplateEngine(site)

        with pytest.raises((TemplateError, RecursionError)):
            tpl = engine.env.get_template("base.html")
            tpl.render()
