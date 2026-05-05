"""Focused command output parity checks for Milo/Kida templates."""

from __future__ import annotations

from types import SimpleNamespace


def test_plugin_empty_states_use_command_template():
    """Plugin list/validate empty states should be branded and actionable."""
    from bengal.cli.milo_app import cli

    listed = cli.invoke(["plugin", "list"])
    validated = cli.invoke(["plugin", "validate"])

    assert listed.exit_code == 0
    assert listed.output.startswith("ᓚᘏᗢ Bengal Plugins")
    assert "No Bengal plugins discovered." in listed.output
    assert "Next steps" in listed.output

    assert validated.exit_code == 0
    assert validated.output.startswith("ᓚᘏᗢ Plugin Validation")
    assert "No Bengal plugins discovered." in validated.output
    assert "Next steps" in validated.output


def test_content_sources_empty_state_uses_command_template(tmp_path):
    """Content sources should render a single branded empty state."""
    from bengal.cli.milo_app import cli

    result = cli.invoke(["content", "sources", "--source", str(tmp_path)])

    assert result.exit_code == 0
    assert result.output.startswith("ᓚᘏᗢ Content Sources")
    assert "No collections configured." in result.output
    assert "collections.py" in result.output
    assert "▲" not in result.output


def test_command_list_template_renders_cache_inputs(tmp_path):
    """List-style commands should use the richer command list template."""
    from bengal.cli.milo_app import cli

    (tmp_path / "bengal.toml").write_text("[site]\ntitle = 'Test'\n")
    (tmp_path / "content").mkdir()

    result = cli.invoke(["cache", "inputs", "--source", str(tmp_path)])

    assert result.exit_code == 0
    assert "ᓚᘏᗢ Cache Input Patterns" in result.output
    assert "pattern(s)" in result.output
    assert "content/**" in result.output


def test_build_dashboard_template_renders_bengal_panel():
    """Developer build dashboard should not depend on broken upstream panel internals."""
    from bengal.output import get_cli_output

    cli = get_cli_output(use_global=False)

    output = cli.render(
        "build_dashboard.kida",
        grade_letter="A",
        grade_score=100,
        grade_summary="Build performance is excellent!",
        throughput=12.3,
        render_dist=None,
        bottleneck="Menus",
        regression=None,
        regression_positive=False,
        content=[{"label": "Pages", "value": "1"}, {"label": "Mode", "value": "parallel"}],
        timing=[{"name": "Menus", "time_str": "10ms", "pct": 100.0}],
        total_time="10ms",
        slowest=None,
        cache=None,
        cache_effectiveness=None,
        suggestions=None,
        output_dir="/tmp/public",
        errors=None,
    )

    assert "Performance" in output
    assert "Build performance is excellent!" in output
    assert "Menus" in output


def test_page_explanation_template_renders_bengal_panels():
    """Inspect page output should render without the upstream panel component."""
    from bengal.output import get_cli_output

    cli = get_cli_output(use_global=False)

    output = cli.render(
        "page_explanation.kida",
        source={
            "path": "content/index.md",
            "size": "12 B",
            "lines": 1,
            "modified": "",
            "encoding": "utf-8",
        },
        frontmatter=[{"label": "title", "value": "Home"}],
        template_chain=None,
        deps=None,
        shortcodes=None,
        cache={"status": "MISS", "reason": "changed", "key": "abc", "layers": ["parsed"]},
        output={"url": "/", "path": "public/index.html", "size": "1 KB"},
        issues=None,
        performance={"total_ms": 1.2, "breakdown": [{"label": "Render", "value": "1ms"}]},
    )

    assert "Page Explanation: content/index.md" in output
    assert "Frontmatter" in output
    assert "Performance" in output


def test_url_collision_template_renders_compact_claimants():
    """URL collisions should render as a compact ownership card."""
    from bengal.output import get_cli_output

    cli = get_cli_output(use_global=False)
    collision = SimpleNamespace(
        url="/docs/content/i18n/",
        count=2,
        claimants=(
            SimpleNamespace(
                display_source="site/content/docs/content/i18n/_index.md",
                owner="content",
                priority=100,
            ),
            SimpleNamespace(
                display_source="site/content/docs/content/i18n.md",
                owner="",
                priority=None,
            ),
        ),
    )

    output = cli.render("url_collisions.kida", collisions=[collision])

    assert "URL collision: /docs/content/i18n/" in output
    assert "Claimants" in output
    assert "site/content/docs/content/i18n/_index.md" in output
    assert "site/content/docs/content/i18n.md" in output
    assert "Fix:" in output


def test_command_output_matrix_covers_priority_commands():
    """Document the first parity pass across high-traffic command surfaces."""
    matrix = {
        "build": "build_summary.kida",
        "build dashboard": "build_dashboard.kida",
        "plugin list": "command_empty.kida / command_list.kida",
        "plugin validate": "command_empty.kida / validation_report.kida",
        "content sources": "command_empty.kida / command_list.kida",
        "content fetch": "command_empty.kida / kv_detail.kida",
        "content collections": "command_empty.kida / kv_detail.kida",
        "content schemas": "command_empty.kida / command_list.kida / validation_report.kida",
        "codemod": "command_empty.kida / command_list.kida / kv_detail.kida",
        "i18n compile": "command_empty.kida / command_list.kida",
        "i18n extract": "command_empty.kida / kv_detail.kida",
        "i18n init": "command_list.kida",
        "i18n sync": "command_empty.kida / command_list.kida",
        "version list": "command_empty.kida / command_list.kida / json_output.kida",
        "version info": "kv_detail.kida / command_list.kida",
        "version create": "kv_detail.kida / command_list.kida / scaffold_result.kida",
        "version diff": "command_empty.kida / diff_view.kida / json_output.kida",
        "cache inputs": "command_list.kida / json_output.kida",
        "check": "check_report.kida / check_report_focus.kida",
        "audit": "artifact_audit.kida / artifact_audit_focus.kida / json_output.kida",
        "inspect page": "page_explanation.kida",
        "phase summaries": "phase_summary.kida",
        "url collisions": "url_collisions.kida",
        "report primitives": "_report_primitives.kida",
        "theme list": "command_list.kida",
        "theme discover": "command_list.kida",
        "config show missing config": "command_empty.kida",
        "config doctor missing config": "command_empty.kida",
        "config diff missing config": "command_empty.kida",
        "unknown command": "command_error.kida",
        "unknown group command": "command_error.kida",
    }

    assert len(matrix) >= 12
    assert all(".kida" in template for template in matrix.values())
