"""Site-wide output format generation (index, LLM texts, changelog, manifest)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.postprocess.output_formats.agent_manifest_generator import (
    AgentManifestGenerator,
)
from bengal.postprocess.output_formats.changelog_generator import ChangelogGenerator
from bengal.postprocess.output_formats.index_generator import SiteIndexGenerator
from bengal.postprocess.output_formats.llm_generator import SiteLlmTxtGenerator
from bengal.postprocess.output_formats.llms_txt_generator import SiteLlmsTxtGenerator
from bengal.postprocess.search_backends import (
    create_search_backend,
    resolve_search_backend_config,
)
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.postprocess.output_formats.generator import OutputFormatsGenerator
    from bengal.protocols import PageLike

logger = get_logger(__name__)


def generate_site_wide_formats(
    self: OutputFormatsGenerator,
    *,
    generated: list[str],
    timings: dict[str, float],
    options: dict[str, Any],
    site_wide: list[str],
    accumulated_data: list[Any] | None,
    ai_input_pages: list[PageLike],
    ai_train_pages: list[PageLike],
    search_pages: list[PageLike],
) -> None:
    """Generate enabled site-wide output formats, skipping unchanged artifacts."""
    if "index_json" in site_wide:
        excerpt_length = options.get("excerpt_length", 200)
        json_indent = options.get("json_indent")
        include_full_content = options.get("include_full_content_in_index", False)
        include_heading_index = options.get("include_heading_index", False)
        index_gen = SiteIndexGenerator(
            self.site,
            excerpt_length=excerpt_length,
            json_indent=json_indent,
            include_full_content=include_full_content,
            include_heading_index=include_heading_index,
        )
        index_result = self._generate_site_wide_if_needed(
            timings,
            "site_index_json",
            search_pages,
            accumulated_data,
            {
                "excerpt_length": excerpt_length,
                "json_indent": json_indent,
                "include_full_content": include_full_content,
                "include_heading_index": include_heading_index,
            },
            self._expected_site_wide_outputs("site_index_json"),
            lambda: index_gen.generate(
                search_pages,
                accumulated_data=accumulated_data,
                build_context=self.build_context,
            ),
        )

        if isinstance(index_result, list):
            index_paths = index_result
            generated.extend([f"index.json ({len(index_paths)} versions)"])
            logger.debug("generated_versioned_index_json", count=len(index_paths))
        else:
            index_paths = [index_result]
            generated.append("index.json")
            logger.debug("generated_site_index_json")

        search_backend_config = resolve_search_backend_config(self.site.config.get("search", {}))
        search_backend = create_search_backend(self.site, search_backend_config)
        generated_search = self._generate_search_backend_if_needed(
            timings,
            search_backend,
            search_backend_config,
            index_paths,
            search_pages,
            accumulated_data,
        )
        generated.extend(generated_search)
        if generated_search:
            logger.debug(
                "generated_search_backend_artifacts",
                backend=search_backend.name,
                count=len(generated_search),
            )

    if "llm_full" in site_wide:
        separator_width = options.get("llm_separator_width", 80)
        llm_gen = SiteLlmTxtGenerator(self.site, separator_width=separator_width)
        self._generate_site_wide_if_needed(
            timings,
            "site_llm_full",
            ai_train_pages,
            accumulated_data,
            {"separator_width": separator_width},
            self._expected_site_wide_outputs("site_llm_full"),
            lambda: llm_gen.generate(ai_train_pages),
        )
        generated.append("llm-full.txt")
        logger.debug("generated_site_llm_full")

    if "llms_txt" in site_wide:
        llms_gen = SiteLlmsTxtGenerator(self.site)
        self._generate_site_wide_if_needed(
            timings,
            "site_llms_txt",
            ai_input_pages,
            accumulated_data,
            {
                "max_pages": getattr(llms_gen, "max_pages", None),
                "max_chars": getattr(llms_gen, "max_chars", None),
            },
            self._expected_site_wide_outputs("site_llms_txt"),
            lambda: llms_gen.generate(ai_input_pages),
        )
        generated.append("llms.txt")
        logger.debug("generated_site_llms_txt")

    if "changelog" in site_wide:
        changelog_gen = ChangelogGenerator(self.site)
        self._generate_site_wide_if_needed(
            timings,
            "site_changelog",
            ai_input_pages,
            accumulated_data,
            {},
            self._expected_site_wide_outputs("site_changelog"),
            lambda: changelog_gen.generate(ai_input_pages),
        )
        generated.append("changelog.json")
        logger.debug("generated_changelog_json")

    if "agent_manifest" in site_wide:
        agent_gen = AgentManifestGenerator(self.site)
        self._generate_site_wide_if_needed(
            timings,
            "site_agent_manifest",
            ai_input_pages,
            accumulated_data,
            {},
            self._expected_site_wide_outputs("site_agent_manifest"),
            lambda: agent_gen.generate(ai_input_pages),
        )
        generated.append("agent.json")
        logger.debug("generated_agent_manifest")
