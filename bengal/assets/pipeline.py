"""
Optional Node-based asset pipeline integration for Bengal SSG.

Provides SCSS → CSS compilation, PostCSS transforms, and JavaScript/TypeScript
bundling via esbuild. This module enables modern frontend tooling without
requiring users to configure complex build systems.

Supported Transformations:
    - **SCSS → CSS**: Compiles ``.scss`` files using the ``sass`` CLI
    - **PostCSS**: Applies autoprefixer and other PostCSS plugins
    - **JS/TS Bundling**: Bundles and minifies via ``esbuild``

Behavior:
    - Only runs when enabled via config (``[assets].pipeline = true``)
    - Detects required CLIs on PATH and produces clear, actionable errors
    - Compiles into a temporary pipeline output directory
    - Output files are then fingerprinted by AssetOrchestrator

Requirements:
    Node.js tooling must be installed separately::

        npm install -D sass postcss postcss-cli autoprefixer esbuild

Architecture:
    This module acts as a thin wrapper over Node CLIs. It does not change
    the public API of asset processing; compiled files are returned to
    AssetOrchestrator for fingerprinting and manifest generation.

    Pipeline Flow:
        1. Discover source files (SCSS, JS/TS) in assets/ and theme assets
        2. Compile SCSS → CSS via ``sass`` CLI
        3. Apply PostCSS transforms (if enabled)
        4. Bundle JS/TS via ``esbuild``
        5. Return compiled files for AssetOrchestrator processing

Configuration:
    Pipeline settings are read from ``bengal.yaml``::

        assets:
          pipeline: true        # Enable/disable pipeline
          scss: true            # Compile SCSS files
          postcss: true         # Apply PostCSS transforms
          postcss_config: null  # Custom postcss.config.js path
          bundle_js: true       # Bundle JavaScript/TypeScript
          esbuild_target: es2018  # esbuild target environment
          sourcemaps: true      # Generate source maps

Related:
    - bengal/orchestration/asset_orchestrator.py: Consumes pipeline output
    - bengal/assets/manifest.py: Tracks compiled asset URLs
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


@dataclass
class PipelineConfig:
    """
    Configuration for the Node-based asset pipeline.

    Populated from site configuration and passed to NodePipeline. All boolean
    flags default to sensible values when the pipeline is enabled.

    Attributes:
        root_path: Site root directory containing assets/ and themes/.
        theme_name: Active theme name for locating theme assets, or None.
        enabled: Master switch for the entire pipeline.
        scss: Whether to compile SCSS files to CSS.
        postcss: Whether to apply PostCSS transforms to CSS.
        postcss_config: Path to custom postcss.config.js, or None for default.
        bundle_js: Whether to bundle JavaScript/TypeScript files.
        esbuild_target: Target environment for esbuild (e.g. 'es2018', 'esnext').
        sourcemaps: Whether to generate source maps for debugging.
    """

    root_path: Path
    theme_name: str | None
    enabled: bool
    scss: bool
    postcss: bool
    postcss_config: str | None
    bundle_js: bool
    esbuild_target: str
    sourcemaps: bool


class NodePipeline:
    """
    Thin wrapper over Node CLIs for asset compilation.

    Orchestrates SCSS compilation, PostCSS transforms, and JavaScript bundling
    by invoking external CLI tools. Designed to fail gracefully with clear
    error messages when required tools are not installed.

    The pipeline writes compiled files to a temporary directory, which is then
    processed by AssetOrchestrator for fingerprinting and deployment.

    Attributes:
        config: Pipeline configuration settings.
        temp_out_dir: Temporary directory for compiled output files.

    Example:
        >>> config = PipelineConfig(
        ...     root_path=Path("/site"),
        ...     theme_name="default",
        ...     enabled=True,
        ...     scss=True,
        ...     postcss=True,
        ...     postcss_config=None,
        ...     bundle_js=True,
        ...     esbuild_target="es2018",
        ...     sourcemaps=True,
        ... )
        >>> pipeline = NodePipeline(config)
        >>> compiled_files = pipeline.build()
    """

    def __init__(self, config: PipelineConfig) -> None:
        """
        Initialize the pipeline with configuration.

        Args:
            config: Pipeline configuration from site settings.
        """
        from bengal.cache.paths import BengalPaths

        self.config = config
        paths = BengalPaths(config.root_path)
        self.temp_out_dir = paths.pipeline_out_dir

    def build(self) -> list[Path]:
        """
        Run the full pipeline and return compiled output files.

        Executes enabled pipeline stages in order: SCSS → PostCSS → JS bundling.
        Cleans the temporary output directory before starting.

        Returns:
            List of paths to compiled files in the temporary output directory.
            Returns empty list if pipeline is disabled or no sources found.
        """
        if not self.config.enabled:
            return []

        # Clean temp output
        if self.temp_out_dir.exists():
            shutil.rmtree(self.temp_out_dir)
        self.temp_out_dir.mkdir(parents=True, exist_ok=True)

        compiled_files: list[Path] = []

        # SCSS -> CSS
        if self.config.scss:
            compiled_files += self._compile_scss()

        # PostCSS (optional)
        if self.config.postcss and compiled_files:
            self._run_postcss_on_css([p for p in compiled_files if p.suffix == ".css"])

        # JS/TS bundling
        if self.config.bundle_js:
            compiled_files += self._bundle_js()

        # Return unique paths
        unique: list[Path] = []
        seen = set()
        for p in compiled_files:
            if p not in seen:
                unique.append(p)
                seen.add(p)
        return unique

    # -------------------------------------------------------------------------
    # Internal Compilation Methods
    # -------------------------------------------------------------------------

    def _compile_scss(self) -> list[Path]:
        """
        Compile all discovered SCSS files to CSS.

        Searches for ``.scss`` files in site assets and theme assets directories,
        then compiles each using the ``sass`` CLI.

        Returns:
            List of paths to compiled CSS files.
        """
        if not self._which("sass"):
            logger.error("pipeline_missing_cli", tool="sass", hint="npm i -D sass")
            return []

        scss_files = self._find_sources([".scss"], subdirs=["assets", self._theme_assets_subdir()])
        outputs: list[Path] = []
        for src in scss_files:
            try:
                rel = self._relative_to_assets(src)
                # place compiled css under same relative path but with .css extension inside temp_out_dir/assets
                out_rel = rel.with_suffix(".css")
                out_path = self.temp_out_dir / "assets" / out_rel
                out_path.parent.mkdir(parents=True, exist_ok=True)

                cmd = [
                    "sass",
                    str(src),
                    str(out_path),
                ]
                if self.config.sourcemaps:
                    cmd.append("--source-map")

                self._run(cmd, cwd=self.config.root_path)
                outputs.append(out_path)
            except Exception as e:
                logger.error("scss_compile_failed", source=str(src), error=str(e))
        return outputs

    def _run_postcss_on_css(self, css_files: list[Path]) -> None:
        """
        Apply PostCSS transforms to compiled CSS files in-place.

        Runs the ``postcss`` CLI on each CSS file, applying configured plugins
        (typically autoprefixer). Modifies files in-place.

        Args:
            css_files: List of CSS file paths to process.
        """
        if not self._which("postcss"):
            logger.warning("postcss_not_found", hint="npm i -D postcss postcss-cli autoprefixer")
            return
        for css in css_files:
            try:
                cmd = ["postcss", str(css), "-o", str(css)]
                if self.config.postcss_config:
                    cmd += ["--config", self.config.postcss_config]
                self._run(cmd, cwd=self.config.root_path)
            except Exception as e:
                logger.error("postcss_failed", css=str(css), error=str(e))

    def _bundle_js(self) -> list[Path]:
        """
        Bundle JavaScript and TypeScript entry points via esbuild.

        Discovers entry points in ``assets/js/`` directories and bundles each
        using esbuild with minification. Includes source maps if enabled.

        Returns:
            List of paths to bundled JS files and their source maps.
        """
        if not self._which("esbuild"):
            logger.error("pipeline_missing_cli", tool="esbuild", hint="npm i -D esbuild")
            return []

        entries = self._find_js_entries()
        outputs: list[Path] = []
        for src in entries:
            try:
                rel = self._relative_to_assets(src)
                out_rel = rel.with_suffix(".js")
                out_path = self.temp_out_dir / "assets" / out_rel
                out_path.parent.mkdir(parents=True, exist_ok=True)

                cmd = [
                    "esbuild",
                    str(src),
                    "--bundle",
                    "--minify",
                    "--target={}".format(self.config.esbuild_target or "es2018"),
                    f"--outfile={out_path!s}",
                ]
                if self.config.sourcemaps:
                    cmd.append("--sourcemap")

                self._run(cmd, cwd=self.config.root_path)
                outputs.append(out_path)
                # esbuild writes the sourcemap next to out_path if enabled
                map_path = out_path.with_suffix(out_path.suffix + ".map")
                if map_path.exists():
                    outputs.append(map_path)
            except Exception as e:
                logger.error("esbuild_failed", source=str(src), error=str(e))
        return outputs

    # -------------------------------------------------------------------------
    # Discovery Helpers
    # -------------------------------------------------------------------------

    def _find_sources(self, exts: list[str], subdirs: list[str | None]) -> list[Path]:
        """
        Recursively find source files by extension in specified directories.

        Args:
            exts: List of file extensions to match (e.g. ['.scss', '.sass']).
            subdirs: List of subdirectory paths relative to root_path.

        Returns:
            List of matching file paths.
        """
        files: list[Path] = []
        checked_dirs: list[Path] = []
        for sub in subdirs:
            if not sub:
                continue
            base = self.config.root_path / sub
            if not base.exists():
                continue
            checked_dirs.append(base)
            for p in base.rglob("*"):
                if p.is_file() and p.suffix.lower() in exts:
                    files.append(p)
        logger.debug(
            "pipeline_sources_found",
            count=len(files),
            dirs=[str(d) for d in checked_dirs],
            exts=exts,
        )
        return files

    def _find_js_entries(self) -> list[Path]:
        """
        Find JavaScript/TypeScript entry points for bundling.

        Uses a heuristic: files directly in ``assets/js/`` are treated as entry
        points, while nested files are assumed to be modules imported by entries.

        Returns:
            List of JS/TS entry point paths.
        """
        entries: list[Path] = []
        theme_assets = self._theme_assets_dir()
        bases = [self.config.root_path / "assets" / "js"]
        if theme_assets:
            bases.append(theme_assets / "js")
        for base in bases:
            if base.exists():
                for p in base.glob("*.*"):
                    if p.is_file() and p.suffix.lower() in (".js", ".ts"):
                        entries.append(p)
        logger.debug("pipeline_js_entries", count=len(entries))
        return entries

    # -------------------------------------------------------------------------
    # Path Utilities
    # -------------------------------------------------------------------------

    def _relative_to_assets(self, src: Path) -> Path:
        """
        Compute the relative path of a source file within its assets directory.

        Tries each candidate assets directory and returns the relative path
        from the first match. Falls back to just the filename if no match.

        Args:
            src: Absolute path to a source file.

        Returns:
            Relative path suitable for output file naming.
        """
        for base in self._candidate_asset_dirs():
            try:
                return src.relative_to(base)
            except ValueError:
                continue
        # Fallback: just return name
        return Path(src.name)

    def _candidate_asset_dirs(self) -> list[Path]:
        """
        Get all directories that may contain asset source files.

        Returns:
            List containing site assets dir and theme assets dir (if present).
        """
        dirs: list[Path] = [self.config.root_path / "assets"]
        theme_dir = self._theme_assets_dir()
        if theme_dir:
            dirs.append(theme_dir)
        return dirs

    def _theme_assets_dir(self) -> Path | None:
        """
        Resolve the theme's assets directory.

        Checks for theme assets in the site's themes/ directory first,
        then falls back to bundled themes in the Bengal package.

        Returns:
            Path to theme assets directory, or None if not found.
        """
        if not self.config.theme_name:
            return None
        theme_dir = self.config.root_path / "themes" / self.config.theme_name / "assets"
        if theme_dir.exists():
            return theme_dir
        try:
            import bengal as bengal_pkg

            bundled = (
                Path(bengal_pkg.__file__).parent / "themes" / self.config.theme_name / "assets"
            )
            return bundled if bundled.exists() else None
        except Exception as e:
            logger.debug(
                "asset_pipeline_theme_assets_dir_failed",
                theme=self.config.theme_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def _theme_assets_subdir(self) -> str | None:
        """
        Get the theme assets path as a relative subdirectory string.

        Returns:
            Relative path string (e.g. 'themes/default/assets'), or None.
        """
        d = self._theme_assets_dir()
        return (
            str(d.relative_to(self.config.root_path))
            if d and str(d).startswith(str(self.config.root_path))
            else None
        )

    # -------------------------------------------------------------------------
    # Subprocess Helpers
    # -------------------------------------------------------------------------

    def _which(self, exe: str) -> bool:
        """
        Check if an executable is available on PATH.

        Args:
            exe: Executable name (e.g. 'sass', 'esbuild').

        Returns:
            True if executable is found, False otherwise.
        """
        return shutil.which(exe) is not None

    def _run(self, cmd: list[str], cwd: Path) -> None:
        """
        Execute a subprocess command and raise on failure.

        Args:
            cmd: Command and arguments as a list.
            cwd: Working directory for the subprocess.

        Raises:
            BengalError: If the command exits with non-zero status.
        """
        logger.debug("pipeline_exec", cmd=" ".join(cmd))
        proc = subprocess.run(cmd, check=False, cwd=str(cwd), capture_output=True, text=True)
        if proc.returncode != 0:
            from bengal.errors import BengalError

            error_msg = proc.stderr.strip() or proc.stdout.strip()
            raise BengalError(
                f"Asset pipeline command failed: {error_msg}",
                suggestion="Check command output and ensure required tools are installed",
            )


def from_site(site: Site) -> NodePipeline:
    """
    Factory to create a NodePipeline from site configuration.

    Extracts pipeline settings from the site's ``[assets]`` config section
    and creates a configured NodePipeline instance.

    Args:
        site: Site instance with loaded configuration.

    Returns:
        Configured NodePipeline ready to run.

    Example:
        >>> from bengal.assets.pipeline import from_site
        >>> pipeline = from_site(site)
        >>> compiled_files = pipeline.build()
    """
    assets_cfg = (
        site.config.get("assets", {}) if isinstance(site.config.get("assets"), dict) else {}
    )
    pc = PipelineConfig(
        root_path=site.root_path,
        theme_name=site.theme,
        enabled=bool(assets_cfg.get("pipeline", False)),
        scss=bool(assets_cfg.get("scss", True)),
        postcss=bool(assets_cfg.get("postcss", True)),
        postcss_config=assets_cfg.get("postcss_config"),
        bundle_js=bool(assets_cfg.get("bundle_js", True)),
        esbuild_target=str(assets_cfg.get("esbuild_target", "es2018")),
        sourcemaps=bool(assets_cfg.get("sourcemaps", True)),
    )
    return NodePipeline(pc)
