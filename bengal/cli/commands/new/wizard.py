"""
Interactive site initialization wizard.

Provides a questionary-based wizard for selecting site presets.
"""

from __future__ import annotations

import questionary

from bengal.cli.helpers import get_cli_output

from .presets import PRESETS


def should_run_init_wizard(template: str, no_init: bool, init_preset: str | None) -> bool:
    """
    Determine if we should run the initialization wizard.

    Args:
        template: Selected template name
        no_init: Whether user explicitly said no to wizard
        init_preset: Preset name if provided via flag

    Returns:
        True if wizard should run
    """
    # Skip if user explicitly said no
    if no_init:
        return False

    # Skip if user provided a preset (they know what they want)
    if init_preset:
        return True

    # Skip if template is non-default (template already has structure)
    # Otherwise, prompt the user
    return template == "default"


def run_init_wizard(preset: str | None = None) -> str | None:
    """
    Run the site initialization wizard and return the selected template ID.

    Args:
        preset: Optional preset name to use directly without prompting

    Returns:
        Template ID string or None for blank site
    """
    cli = get_cli_output()

    # If preset was provided via flag, use it directly
    if preset:
        if preset not in PRESETS:
            cli.warning(f"Unknown preset '{preset}'. Available: " + ", ".join(PRESETS.keys()))
            return None

        selected_preset = PRESETS[preset]
        cli.info(f"🏗️  Selected {selected_preset['emoji']} {selected_preset['name']} preset.")
        return str(selected_preset.get("template_id", "default"))

    # Build choices list
    choices = []
    preset_items = list(PRESETS.items())

    for key, info in preset_items:
        choices.append(
            {
                "name": f"{info['emoji']} {info['name']:<15} - {info['description']}",
                "value": key,
            }
        )

    choices.append(
        {
            "name": "📦 Blank          - Empty site, no initial structure",
            "value": "__blank__",
        }
    )

    choices.append(
        {
            "name": "⚙️  Custom         - Define your own structure",
            "value": "__custom__",
        }
    )

    # Show interactive menu
    cli.blank()
    cli.header("🎯 What kind of site are you building?")
    selection = questionary.select(
        "Select a preset:",
        choices=choices,
        style=questionary.Style(
            [
                ("qmark", "fg:cyan bold"),
                ("question", "fg:cyan bold"),
                ("pointer", "fg:cyan bold"),
                ("highlighted", "fg:cyan bold"),
                ("selected", "fg:green"),
            ]
        ),
    ).ask()

    # Handle cancellation (Ctrl+C)
    if selection is None:
        cli.blank()
        cli.warning("✨ Cancelled. Will create basic default site.")
        return "default"

    # Handle blank
    if selection == "__blank__":
        cli.blank()
        cli.info("✨ Blank site selected. No initial structure added.")
        return None

    # Handle custom
    if selection == "__custom__":
        cli.blank()
        sections_input = cli.prompt(
            "Enter section names (comma-separated, e.g., blog,about)", default="blog,about"
        )
        pages_per = cli.prompt("Pages per section", default=3, type=int)
        cli.blank()
        cli.info(
            f"✨ Custom structure noted (sections={sections_input}, pages={pages_per}). "
            f"Basic site created; run 'bengal init --sections {sections_input} "
            f"--pages-per-section {pages_per} --with-content' after to add structure."
        )
        return "default"  # Custom needs post-creation init

    # Regular preset selected
    selected_preset = PRESETS[selection]
    cli.blank()
    cli.info(f"✨ {selected_preset['name']} preset selected.")
    return str(selected_preset.get("template_id", "default"))
