"""Autodoc commands for generating API and CLI documentation."""

from __future__ import annotations

from pathlib import Path

import click

from bengal.autodoc.config import load_autodoc_config
from bengal.autodoc.extractors.cli import CLIExtractor
from bengal.autodoc.extractors.python import PythonExtractor
from bengal.autodoc.generator import DocumentationGenerator
from bengal.cli.base import BengalCommand
from bengal.utils.cli_output import CLIOutput


@click.command(cls=BengalCommand)
@click.option(
    "--source",
    "-s",
    multiple=True,
    type=click.Path(exists=True),
    help="Source directory to document (can specify multiple)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output directory for generated docs (default: from config or content/api)",
)
@click.option("--clean", is_flag=True, help="Clean output directory before generating")
@click.option(
    "--parallel/--no-parallel", default=True, help="Use parallel processing (default: enabled)"
)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed progress")
@click.option("--stats", is_flag=True, help="Show performance statistics")
@click.option(
    "--config", type=click.Path(exists=True), help="Path to config file (default: bengal.toml)"
)
@click.option("--python-only", is_flag=True, help="Only generate Python API docs (skip CLI docs)")
@click.option("--cli-only", is_flag=True, help="Only generate CLI docs (skip Python API docs)")
def autodoc(
    source: tuple,
    output: str,
    clean: bool,
    parallel: bool,
    verbose: bool,
    stats: bool,
    config: str,
    python_only: bool,
    cli_only: bool,
) -> None:
    """
    📚 Generate comprehensive API documentation (Python + CLI).

    Automatically generates both Python API docs and CLI docs based on
    your bengal.toml configuration. Use --python-only or --cli-only to
    generate specific types.

    Examples:
        bengal autodoc                    # Generate all configured docs
        bengal autodoc --python-only      # Python API docs only
        bengal autodoc --cli-only         # CLI docs only
        bengal autodoc --source src       # Override Python source
    """
    import time

    cli = CLIOutput()

    try:
        # Load configuration
        config_path = Path(config) if config else None
        autodoc_config = load_autodoc_config(config_path)
        python_config = autodoc_config.get("python", {})
        cli_config = autodoc_config.get("cli", {})

        # HTML renderer removed - using traditional Markdown generation

        # Determine what to generate
        generate_python = not cli_only and (python_only or python_config.get("enabled", True))
        generate_cli = not python_only and (
            cli_only or (cli_config.get("enabled", False) and cli_config.get("app_module"))
        )

        if not generate_python and not generate_cli:
            cli.warning("⚠️  Nothing to generate")
            cli.blank()
            cli.info("Either:")
            cli.info("  • Enable Python docs in bengal.toml: [autodoc.python] enabled = true")
            cli.info(
                "  • Enable CLI docs in bengal.toml: [autodoc.cli] enabled = true, app_module = '...'"
            )
            cli.info("  • Use --python-only or --cli-only flags")
            return

        cli.blank()
        cli.header("📚 Bengal Autodoc")
        cli.blank()

        total_start = time.time()

        # ========== PYTHON API DOCUMENTATION ==========
        if generate_python:
            _generate_python_docs(
                source=source,
                output=output,
                clean=clean,
                parallel=parallel,
                verbose=verbose,
                stats=stats,
                python_config=python_config,
            )

        # ========== CLI DOCUMENTATION ==========
        if generate_cli:
            if generate_python:
                cli.blank()
                cli.info("─" * 60)
                cli.blank()

            _generate_cli_docs(
                app=cli_config.get("app_module"),
                framework=cli_config.get("framework", "click"),
                output=cli_config.get("output_dir", "content/cli"),
                include_hidden=cli_config.get("include_hidden", False),
                clean=clean,
                verbose=verbose,
                cli_config=cli_config,
                autodoc_config=autodoc_config,
            )

        # Summary
        if generate_python and generate_cli:
            total_time = time.time() - total_start
            cli.blank()
            cli.info("─" * 60)
            cli.blank()
            cli.success(f"✅ All documentation generated in {total_time:.2f}s")
            cli.blank()

    except KeyboardInterrupt:
        cli.blank()
        cli.warning("⚠️  Cancelled by user")
        raise click.Abort() from None
    except Exception as e:
        cli.blank()
        cli.error(f"❌ Error: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        raise click.Abort() from e


def _generate_python_docs(
    source: tuple,
    output: str,
    clean: bool,
    parallel: bool,
    verbose: bool,
    stats: bool,
    python_config: dict,
) -> None:
    """Generate Python API documentation."""
    import time

    cli = CLIOutput()

    cli.header("🐍 Python API Documentation")
    cli.blank()

    # Use CLI args or fall back to config
    sources = list(source) if source else python_config.get("source_dirs", ["."])

    output_dir = Path(output) if output else Path(python_config.get("output_dir", "content/api"))

    # Get exclusion patterns from config
    exclude_patterns = python_config.get("exclude", [])

    # Clean output directory if requested
    if clean and output_dir.exists():
        import shutil

        shutil.rmtree(output_dir)
        cli.warning(f"🧹 Cleaned {output_dir}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract documentation
    cli.info("🔍 Extracting Python API documentation...")
    start_time = time.time()

    extractor = PythonExtractor(exclude_patterns=exclude_patterns, config=python_config)
    all_elements = []

    for source_path in sources:
        source_path = Path(source_path)
        if verbose:
            cli.info(f"   📂 Scanning {source_path}")

        elements = extractor.extract(source_path)
        all_elements.extend(elements)

        if verbose:
            module_count = len(elements)
            class_count = sum(
                len([c for c in e.children if c.element_type == "class"]) for e in elements
            )
            func_count = sum(
                len([c for c in e.children if c.element_type == "function"]) for e in elements
            )
            cli.info(
                f"   ✓ Found {module_count} modules, {class_count} classes, {func_count} functions"
            )

    extraction_time = time.time() - start_time

    if not all_elements:
        cli.warning("⚠️  No Python modules found")
        return

    cli.success(f"   ✓ Extracted {len(all_elements)} modules in {extraction_time:.2f}s")

    # Generate documentation
    gen_start = time.time()

    config = {"autodoc": python_config}
    generator = DocumentationGenerator(extractor, config)

    # Use traditional markdown generation
    cli.info("📝 Generating markdown files...")
    generated = generator.generate_all(all_elements, output_dir, parallel=parallel)
    generated_count = len(generated)

    generation_time = time.time() - gen_start
    total_time = time.time() - start_time

    # Success message
    cli.blank()
    cli.success(f"✅ Generated {generated_count} documentation pages")
    cli.info(f"   📁 Output: {output_dir}")

    if stats:
        cli.subheader("Performance Statistics:", icon="📊")
        cli.info(f"   Extraction time:  {extraction_time:.2f}s")
        cli.info(f"   Generation time:  {generation_time:.2f}s")
        cli.info(f"   Total time:       {total_time:.2f}s")
        cli.info(f"   Throughput:       {generated_count / total_time:.1f} pages/sec")

    cli.subheader("Next steps:", icon="💡")
    cli.tip(f"View docs: ls {output_dir}")
    cli.tip("Build site: bengal build")
    cli.blank()


def _generate_cli_docs(
    app: str,
    framework: str,
    output: str,
    include_hidden: bool,
    clean: bool,
    verbose: bool,
    cli_config: dict,
    autodoc_config: dict,
) -> None:
    """Generate CLI documentation."""
    import importlib
    import time

    cli = CLIOutput()

    cli.header("⌨️  CLI Documentation")
    cli.blank()

    # Use traditional markdown generation

    output_dir = Path(output)

    # Clean output directory if requested
    if clean and output_dir.exists():
        import shutil

        shutil.rmtree(output_dir)
        cli.warning(f"🧹 Cleaned {output_dir}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Import the CLI app
    cli.info(f"🔍 Loading CLI app from {app}...")

    try:
        module_path, attr_name = app.split(":")
        module = importlib.import_module(module_path)
        cli_app = getattr(module, attr_name)
    except Exception as e:
        cli.error(f"❌ Failed to load app: {e}")
        cli.blank()
        cli.info("Make sure the module path is correct:")
        cli.info(f"  • Module: {app.split(':')[0]}")
        cli.info(f"  • Attribute: {app.split(':')[1] if ':' in app else '(missing)'}")
        cli.blank()
        raise click.Abort() from e

    # Extract documentation
    cli.info("📝 Extracting CLI documentation...")
    start_time = time.time()

    extractor = CLIExtractor(framework=framework, include_hidden=include_hidden)
    elements = extractor.extract(cli_app)

    extraction_time = time.time() - start_time

    # Count commands
    command_count = 0
    option_count = 0
    for element in elements:
        if element.element_type == "command-group":
            command_count = len(element.children)
            for cmd in element.children:
                option_count += cmd.metadata.get("option_count", 0)

    cli.success(f"   ✓ Extracted {command_count} commands, {option_count} options")

    if verbose:
        cli.blank()
        cli.info("Commands found:")
        for element in elements:
            if element.element_type == "command-group":
                for cmd in element.children:
                    cli.info(f"  • {cmd.name}")

    # Generate documentation
    gen_start = time.time()

    generator = DocumentationGenerator(extractor, {"autodoc": {"cli": cli_config}})
    generated_files = generator.generate_all(elements, output_dir)

    gen_time = time.time() - gen_start
    total_time = time.time() - start_time

    # Display results
    cli.blank()
    cli.success("✅ CLI Documentation Generated!")

    cli.subheader("Statistics:", icon="📊")
    cli.info(f"   • Commands: {command_count}")
    cli.info(f"   • Options:  {option_count}")
    cli.info(f"   • Pages:    {len(generated_files)}")

    cli.subheader("Performance:", icon="⚡")
    cli.info(f"   • Extraction: {extraction_time:.3f}s")
    cli.info(f"   • Generation: {gen_time:.3f}s")
    cli.info(f"   • Total:      {total_time:.3f}s")

    cli.blank()
    cli.info(f"📂 Output: {output_dir}")

    cli.subheader("Next steps:", icon="💡")
    cli.tip(f"View docs: ls {output_dir}")
    cli.tip("Build site: bengal build")
    cli.blank()


@click.command(name="autodoc-cli", cls=BengalCommand)
@click.option("--app", "-a", help="CLI app module (e.g., bengal.cli:main)")
@click.option(
    "--framework",
    "-f",
    type=click.Choice(["click", "argparse", "typer"]),
    default="click",
    help="CLI framework (default: click)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output directory for generated docs (default: content/cli)",
)
@click.option("--include-hidden", is_flag=True, help="Include hidden commands")
@click.option("--clean", is_flag=True, help="Clean output directory before generating")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed progress")
@click.option(
    "--config", type=click.Path(exists=True), help="Path to config file (default: bengal.toml)"
)
def autodoc_cli(
    app: str,
    framework: str,
    output: str,
    include_hidden: bool,
    clean: bool,
    verbose: bool,
    config: str,
) -> None:
    """
    ⌨️  Generate CLI documentation from Click/argparse/typer apps.

    Extracts documentation from command-line interfaces to create
    comprehensive command reference documentation.

    Example:
        bengal autodoc-cli --app bengal.cli:main --output content/cli
    """
    import importlib
    import time

    cli = CLIOutput()

    try:
        cli.blank()
        cli.header("⌨️  Bengal CLI Autodoc")
        cli.blank()

        # Load configuration
        config_path = Path(config) if config else None
        autodoc_config = load_autodoc_config(config_path)
        cli_config = autodoc_config.get("cli", {})

        # Use CLI args or fall back to config
        if not app:
            app = cli_config.get("app_module")

        if not app:
            cli.error("❌ Error: No CLI app specified")
            cli.blank()
            cli.info("Please specify the app module either:")
            cli.info("  • Via command line: --app bengal.cli:main")
            cli.info("  • Via config file: [autodoc.cli] app_module = 'bengal.cli:main'")
            cli.blank()
            raise click.Abort()

        if not framework:
            framework = cli_config.get("framework", "click")

        output_dir = Path(output) if output else Path(cli_config.get("output_dir", "content/cli"))

        if not include_hidden:
            include_hidden = cli_config.get("include_hidden", False)

        # Clean output directory if requested
        if clean and output_dir.exists():
            import shutil

            shutil.rmtree(output_dir)
            cli.warning(f"🧹 Cleaned {output_dir}")

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Import the CLI app
        cli.info(f"🔍 Loading CLI app from {app}...")

        try:
            module_path, attr_name = app.split(":")
            module = importlib.import_module(module_path)
            cli_app = getattr(module, attr_name)
        except Exception as e:
            cli.error(f"❌ Failed to load app: {e}")
            cli.blank()
            cli.info("Make sure the module path is correct:")
            cli.info(f"  • Module: {app.split(':')[0]}")
            cli.info(f"  • Attribute: {app.split(':')[1] if ':' in app else '(missing)'}")
            cli.blank()
            raise click.Abort() from e

        # Extract documentation
        cli.info("📝 Extracting CLI documentation...")
        start_time = time.time()

        extractor = CLIExtractor(framework=framework, include_hidden=include_hidden)
        elements = extractor.extract(cli_app)

        extraction_time = time.time() - start_time

        # Count commands
        command_count = 0
        option_count = 0
        for element in elements:
            if element.element_type == "command-group":
                command_count = len(element.children)
                for cmd in element.children:
                    option_count += cmd.metadata.get("option_count", 0)

        cli.success(f"   ✓ Extracted {command_count} commands, {option_count} options")

        if verbose:
            cli.blank()
            cli.info("Commands found:")
            for element in elements:
                if element.element_type == "command-group":
                    for cmd in element.children:
                        cli.info(f"  • {cmd.name}")

        # Generate documentation
        gen_start = time.time()

        generator = DocumentationGenerator(extractor, cli_config)
        generated_files = generator.generate_all(elements, output_dir)

        gen_time = time.time() - gen_start
        total_time = time.time() - start_time

        # Display results
        cli.blank()
        cli.success("✅ CLI Documentation Generated!")

        cli.subheader("Statistics:", icon="📊")
        cli.info(f"   • Commands: {command_count}")
        cli.info(f"   • Options:  {option_count}")
        cli.info(f"   • Pages:    {len(generated_files)}")

        cli.subheader("Performance:", icon="⚡")
        cli.info(f"   • Extraction: {extraction_time:.3f}s")
        cli.info(f"   • Generation: {gen_time:.3f}s")
        cli.info(f"   • Total:      {total_time:.3f}s")
        cli.blank()
        cli.info(f"   📂 Output: {output_dir}")
        cli.blank()

        if verbose:
            cli.info("Generated files:")
            for file in generated_files:
                cli.info(f"  • {file}")
            cli.blank()

        cli.warning("💡 Next steps:")
        cli.tip(f"View docs: ls {output_dir}")
        cli.tip("Build site: bengal build")
        cli.blank()

    except click.Abort:
        raise
    except Exception as e:
        cli.blank()
        cli.error(f"❌ Error: {e}")
        if verbose:
            import traceback

            cli.blank()
            cli.info(traceback.format_exc())
        raise click.Abort() from e
