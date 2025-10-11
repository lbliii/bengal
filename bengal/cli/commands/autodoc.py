"""Autodoc commands for generating API and CLI documentation."""

from pathlib import Path
import click

from bengal.autodoc.extractors.python import PythonExtractor
from bengal.autodoc.extractors.cli import CLIExtractor
from bengal.autodoc.generator import DocumentationGenerator
from bengal.autodoc.config import load_autodoc_config


@click.command()
@click.option('--source', '-s', multiple=True, type=click.Path(exists=True), help='Source directory to document (can specify multiple)')
@click.option('--output', '-o', type=click.Path(), help='Output directory for generated docs (default: from config or content/api)')
@click.option('--clean', is_flag=True, help='Clean output directory before generating')
@click.option('--parallel/--no-parallel', default=True, help='Use parallel processing (default: enabled)')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed progress')
@click.option('--stats', is_flag=True, help='Show performance statistics')
@click.option('--config', type=click.Path(exists=True), help='Path to config file (default: bengal.toml)')
@click.option('--python-only', is_flag=True, help='Only generate Python API docs (skip CLI docs)')
@click.option('--cli-only', is_flag=True, help='Only generate CLI docs (skip Python API docs)')
def autodoc(source: tuple, output: str, clean: bool, parallel: bool, verbose: bool, stats: bool, config: str, python_only: bool, cli_only: bool) -> None:
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
    
    try:
        # Load configuration
        config_path = Path(config) if config else None
        autodoc_config = load_autodoc_config(config_path)
        python_config = autodoc_config.get('python', {})
        cli_config = autodoc_config.get('cli', {})
        
        # Determine what to generate
        generate_python = not cli_only and (python_only or python_config.get('enabled', True))
        generate_cli = not python_only and (cli_only or (cli_config.get('enabled', False) and cli_config.get('app_module')))
        
        if not generate_python and not generate_cli:
            click.echo(click.style("⚠️  Nothing to generate", fg='yellow'))
            click.echo()
            click.echo("Either:")
            click.echo("  • Enable Python docs in bengal.toml: [autodoc.python] enabled = true")
            click.echo("  • Enable CLI docs in bengal.toml: [autodoc.cli] enabled = true, app_module = '...'")
            click.echo("  • Use --python-only or --cli-only flags")
            return
        
        click.echo()
        click.echo(click.style("📚 Bengal Autodoc", fg='cyan', bold=True))
        click.echo()
        
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
                python_config=python_config
            )
        
        # ========== CLI DOCUMENTATION ==========
        if generate_cli:
            if generate_python:
                click.echo()
                click.echo(click.style("─" * 60, fg='blue'))
                click.echo()
            
            _generate_cli_docs(
                app=cli_config.get('app_module'),
                framework=cli_config.get('framework', 'click'),
                output=cli_config.get('output_dir', 'content/cli'),
                include_hidden=cli_config.get('include_hidden', False),
                clean=clean,
                verbose=verbose,
                cli_config=cli_config
            )
        
        # Summary
        if generate_python and generate_cli:
            total_time = time.time() - total_start
            click.echo()
            click.echo(click.style("─" * 60, fg='blue'))
            click.echo()
            click.echo(click.style(f"✅ All documentation generated in {total_time:.2f}s", fg='green', bold=True))
            click.echo()
        
    except KeyboardInterrupt:
        click.echo()
        click.echo(click.style("⚠️  Cancelled by user", fg='yellow'))
        raise click.Abort()
    except Exception as e:
        click.echo()
        click.echo(click.style(f"❌ Error: {e}", fg='red', bold=True))
        if verbose:
            import traceback
            traceback.print_exc()
        raise click.Abort()


def _generate_python_docs(source: tuple, output: str, clean: bool, parallel: bool, verbose: bool, stats: bool, python_config: dict) -> None:
    """Generate Python API documentation."""
    import time
    
    click.echo(click.style("🐍 Python API Documentation", fg='cyan', bold=True))
    click.echo()
    
    # Use CLI args or fall back to config
    if source:
        sources = list(source)
    else:
        sources = python_config.get('source_dirs', ['.'])
    
    if output:
        output_dir = Path(output)
    else:
        output_dir = Path(python_config.get('output_dir', 'content/api'))
    
    # Get exclusion patterns from config
    exclude_patterns = python_config.get('exclude', [])
    
    # Clean output directory if requested
    if clean and output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
        click.echo(click.style(f"🧹 Cleaned {output_dir}", fg='yellow'))
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract documentation
    click.echo(click.style("🔍 Extracting Python API documentation...", fg='blue'))
    start_time = time.time()
    
    extractor = PythonExtractor(exclude_patterns=exclude_patterns)
    all_elements = []
    
    for source_path in sources:
        source_path = Path(source_path)
        if verbose:
            click.echo(f"   📂 Scanning {source_path}")
        
        elements = extractor.extract(source_path)
        all_elements.extend(elements)
        
        if verbose:
            module_count = len(elements)
            class_count = sum(len([c for c in e.children if c.element_type == 'class']) for e in elements)
            func_count = sum(len([c for c in e.children if c.element_type == 'function']) for e in elements)
            click.echo(f"   ✓ Found {module_count} modules, {class_count} classes, {func_count} functions")
    
    extraction_time = time.time() - start_time
    
    if not all_elements:
        click.echo(click.style("⚠️  No Python modules found", fg='yellow'))
        return
    
    click.echo(click.style(f"   ✓ Extracted {len(all_elements)} modules in {extraction_time:.2f}s", fg='green'))
    
    # Generate documentation
    from bengal.utils.cli_output import CLIOutput
    cli = CLIOutput()
    cli.blank()
    cli.header("Generating documentation...")
    gen_start = time.time()
    
    generator = DocumentationGenerator(extractor, {'python': python_config})
    generated = generator.generate_all(all_elements, output_dir, parallel=parallel)
    
    generation_time = time.time() - gen_start
    total_time = time.time() - start_time
    
    # Success message
    click.echo()
    click.echo(click.style(f"✅ Generated {len(generated)} documentation pages", fg='green', bold=True))
    click.echo(click.style(f"   📁 Output: {output_dir}", fg='cyan'))
    
    if stats:
        click.echo()
        click.echo(click.style("📊 Performance Statistics:", fg='blue'))
        click.echo(f"   Extraction time:  {extraction_time:.2f}s")
        click.echo(f"   Generation time:  {generation_time:.2f}s")
        click.echo(f"   Total time:       {total_time:.2f}s")
        click.echo(f"   Throughput:       {len(generated) / total_time:.1f} pages/sec")
    
    click.echo()
    click.echo(click.style("💡 Next steps:", fg='yellow'))
    click.echo(f"   • View docs: ls {output_dir}")
    click.echo(f"   • Build site: bengal build")
    click.echo()


def _generate_cli_docs(app: str, framework: str, output: str, include_hidden: bool, clean: bool, verbose: bool, cli_config: dict) -> None:
    """Generate CLI documentation."""
    import time
    import importlib
    
    click.echo(click.style("⌨️  CLI Documentation", fg='cyan', bold=True))
    click.echo()
    
    output_dir = Path(output)
    
    # Clean output directory if requested
    if clean and output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
        click.echo(click.style(f"🧹 Cleaned {output_dir}", fg='yellow'))
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Import the CLI app
    click.echo(click.style(f"🔍 Loading CLI app from {app}...", fg='blue'))
    
    try:
        module_path, attr_name = app.split(':')
        module = importlib.import_module(module_path)
        cli_app = getattr(module, attr_name)
    except Exception as e:
        click.echo(click.style(f"❌ Failed to load app: {e}", fg='red', bold=True))
        click.echo()
        click.echo("Make sure the module path is correct:")
        click.echo(f"  • Module: {app.split(':')[0]}")
        click.echo(f"  • Attribute: {app.split(':')[1] if ':' in app else '(missing)'}")
        click.echo()
        raise click.Abort()
    
    # Extract documentation
    click.echo(click.style(f"📝 Extracting CLI documentation...", fg='blue'))
    start_time = time.time()
    
    extractor = CLIExtractor(framework=framework, include_hidden=include_hidden)
    elements = extractor.extract(cli_app)
    
    extraction_time = time.time() - start_time
    
    # Count commands
    command_count = 0
    option_count = 0
    for element in elements:
        if element.element_type == 'command-group':
            command_count = len(element.children)
            for cmd in element.children:
                option_count += cmd.metadata.get('option_count', 0)
    
    click.echo(click.style(f"   ✓ Extracted {command_count} commands, {option_count} options", fg='green'))
    
    if verbose:
        click.echo()
        click.echo("Commands found:")
        for element in elements:
            if element.element_type == 'command-group':
                for cmd in element.children:
                    click.echo(f"  • {cmd.name}")
    
    # Generate documentation
    from bengal.utils.cli_output import CLIOutput
    cli = CLIOutput()
    cli.blank()
    cli.header("Generating documentation...")
    gen_start = time.time()
    
    generator = DocumentationGenerator(extractor, {'cli': cli_config})
    generated_files = generator.generate_all(elements, output_dir)
    
    gen_time = time.time() - gen_start
    total_time = time.time() - start_time
    
    # Display results
    click.echo()
    click.echo(click.style("✅ CLI Documentation Generated!", fg='green', bold=True))
    click.echo()
    click.echo(click.style("   📊 Statistics:", fg='blue'))
    click.echo(f"      • Commands: {command_count}")
    click.echo(f"      • Options:  {option_count}")
    click.echo(f"      • Pages:    {len(generated_files)}")
    click.echo()
    click.echo(click.style("   ⚡ Performance:", fg='blue'))
    click.echo(f"      • Extraction: {extraction_time:.3f}s")
    click.echo(f"      • Generation: {gen_time:.3f}s")
    click.echo(f"      • Total:      {total_time:.3f}s")
    click.echo()
    click.echo(click.style(f"   📂 Output: {output_dir}", fg='cyan'))
    click.echo()
    click.echo(click.style("💡 Next steps:", fg='yellow'))
    click.echo(f"   • View docs: ls {output_dir}")
    click.echo(f"   • Build site: bengal build")
    click.echo()


@click.command(name='autodoc-cli')
@click.option('--app', '-a', help='CLI app module (e.g., bengal.cli:main)')
@click.option('--framework', '-f', type=click.Choice(['click', 'argparse', 'typer']), default='click', help='CLI framework (default: click)')
@click.option('--output', '-o', type=click.Path(), help='Output directory for generated docs (default: content/cli)')
@click.option('--include-hidden', is_flag=True, help='Include hidden commands')
@click.option('--clean', is_flag=True, help='Clean output directory before generating')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed progress')
@click.option('--config', type=click.Path(exists=True), help='Path to config file (default: bengal.toml)')
def autodoc_cli(app: str, framework: str, output: str, include_hidden: bool, clean: bool, verbose: bool, config: str) -> None:
    """
    ⌨️  Generate CLI documentation from Click/argparse/typer apps.
    
    Extracts documentation from command-line interfaces to create
    comprehensive command reference documentation.
    
    Example:
        bengal autodoc-cli --app bengal.cli:main --output content/cli
    """
    import time
    import importlib
    
    try:
        click.echo()
        click.echo(click.style("⌨️  Bengal CLI Autodoc", fg='cyan', bold=True))
        click.echo()
        
        # Load configuration
        config_path = Path(config) if config else None
        autodoc_config = load_autodoc_config(config_path)
        cli_config = autodoc_config.get('cli', {})
        
        # Use CLI args or fall back to config
        if not app:
            app = cli_config.get('app_module')
        
        if not app:
            click.echo(click.style("❌ Error: No CLI app specified", fg='red', bold=True))
            click.echo()
            click.echo("Please specify the app module either:")
            click.echo("  • Via command line: --app bengal.cli:main")
            click.echo("  • Via config file: [autodoc.cli] app_module = 'bengal.cli:main'")
            click.echo()
            raise click.Abort()
        
        if not framework:
            framework = cli_config.get('framework', 'click')
        
        if output:
            output_dir = Path(output)
        else:
            output_dir = Path(cli_config.get('output_dir', 'content/cli'))
        
        if not include_hidden:
            include_hidden = cli_config.get('include_hidden', False)
        
        # Clean output directory if requested
        if clean and output_dir.exists():
            import shutil
            shutil.rmtree(output_dir)
            click.echo(click.style(f"🧹 Cleaned {output_dir}", fg='yellow'))
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Import the CLI app
        click.echo(click.style(f"🔍 Loading CLI app from {app}...", fg='blue'))
        
        try:
            module_path, attr_name = app.split(':')
            module = importlib.import_module(module_path)
            cli_app = getattr(module, attr_name)
        except Exception as e:
            click.echo(click.style(f"❌ Failed to load app: {e}", fg='red', bold=True))
            click.echo()
            click.echo("Make sure the module path is correct:")
            click.echo(f"  • Module: {app.split(':')[0]}")
            click.echo(f"  • Attribute: {app.split(':')[1] if ':' in app else '(missing)'}")
            click.echo()
            raise click.Abort()
        
        # Extract documentation
        click.echo(click.style(f"📝 Extracting CLI documentation...", fg='blue'))
        start_time = time.time()
        
        extractor = CLIExtractor(framework=framework, include_hidden=include_hidden)
        elements = extractor.extract(cli_app)
        
        extraction_time = time.time() - start_time
        
        # Count commands
        command_count = 0
        option_count = 0
        for element in elements:
            if element.element_type == 'command-group':
                command_count = len(element.children)
                for cmd in element.children:
                    option_count += cmd.metadata.get('option_count', 0)
        
        click.echo(click.style(f"   ✓ Extracted {command_count} commands, {option_count} options", fg='green'))
        
        if verbose:
            click.echo()
            click.echo("Commands found:")
            for element in elements:
                if element.element_type == 'command-group':
                    for cmd in element.children:
                        click.echo(f"  • {cmd.name}")
        
        # Generate documentation
        from bengal.utils.cli_output import CLIOutput
        cli = CLIOutput()
        cli.blank()
        cli.header("Generating documentation...")
        gen_start = time.time()
        
        generator = DocumentationGenerator(extractor, cli_config)
        generated_files = generator.generate_all(elements, output_dir)
        
        gen_time = time.time() - gen_start
        total_time = time.time() - start_time
        
        # Display results
        click.echo()
        click.echo(click.style("✅ CLI Documentation Generated!", fg='green', bold=True))
        click.echo()
        click.echo(f"   📊 Statistics:")
        click.echo(f"      • Commands: {command_count}")
        click.echo(f"      • Options:  {option_count}")
        click.echo(f"      • Pages:    {len(generated_files)}")
        click.echo()
        click.echo(f"   ⚡ Performance:")
        click.echo(f"      • Extraction: {extraction_time:.3f}s")
        click.echo(f"      • Generation: {gen_time:.3f}s")
        click.echo(f"      • Total:      {total_time:.3f}s")
        click.echo()
        click.echo(f"   📂 Output: {output_dir}")
        click.echo()
        
        if verbose:
            click.echo("Generated files:")
            for file in generated_files:
                click.echo(f"  • {file}")
            click.echo()
        
        click.echo(click.style("💡 Next steps:", fg='yellow'))
        click.echo(f"   • View docs: ls {output_dir}")
        click.echo(f"   • Build site: bengal build")
        click.echo()
        
    except click.Abort:
        raise
    except Exception as e:
        click.echo()
        click.echo(click.style(f"❌ Error: {e}", fg='red', bold=True))
        if verbose:
            import traceback
            click.echo()
            click.echo(traceback.format_exc())
        raise click.Abort()

