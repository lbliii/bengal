"""
Optional Node-based asset pipeline integration for Bengal SSG.

Provides SCSS → CSS, PostCSS transforms, and JS/TS bundling via esbuild.

Behavior:
- Only runs when enabled via config (`[assets].pipeline = true`).
- Detects required CLIs on PATH and produces clear, actionable errors.
- Compiles into a temporary pipeline output directory for subsequent
  Bengal fingerprinting and copying.

This module does not change the public API of asset processing; it returns
compiled output files to be treated as regular assets by AssetOrchestrator.
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
    Thin wrapper over Node CLIs (sass, postcss, esbuild).
    """

    def __init__(self, config: PipelineConfig) -> None:
        from bengal.cache.paths import BengalPaths

        self.config = config
        paths = BengalPaths(config.root_path)
        self.temp_out_dir = paths.pipeline_out_dir

    def build(self) -> list[Path]:
        """
        Run the pipeline and return a list of compiled output files.
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

    # Internal helpers

    def _compile_scss(self) -> list[Path]:
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

    # Discovery helpers

    def _find_sources(self, exts: list[str], subdirs: list[str | None]) -> list[Path]:
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
        # Heuristic: treat files at assets/js/*.{js,ts} as entries (not nested modules)
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

    # Path utilities

    def _relative_to_assets(self, src: Path) -> Path:
        for base in self._candidate_asset_dirs():
            try:
                return src.relative_to(base)
            except ValueError:
                continue
        # Fallback: just return name
        return Path(src.name)

    def _candidate_asset_dirs(self) -> list[Path]:
        dirs: list[Path] = [self.config.root_path / "assets"]
        theme_dir = self._theme_assets_dir()
        if theme_dir:
            dirs.append(theme_dir)
        return dirs

    def _theme_assets_dir(self) -> Path | None:
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
        d = self._theme_assets_dir()
        return (
            str(d.relative_to(self.config.root_path))
            if d and str(d).startswith(str(self.config.root_path))
            else None
        )

    # Subprocess helpers

    def _which(self, exe: str) -> bool:
        return shutil.which(exe) is not None

    def _run(self, cmd: list[str], cwd: Path) -> None:
        logger.debug("pipeline_exec", cmd=" ".join(cmd))
        proc = subprocess.run(cmd, check=False, cwd=str(cwd), capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())


def from_site(site: Site) -> NodePipeline:
    """Factory to create pipeline from site config."""
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
